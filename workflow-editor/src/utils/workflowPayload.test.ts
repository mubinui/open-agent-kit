import { describe, expect, it } from 'vitest';
import type { VisualEdge, VisualNode } from '../types/workflow';
import { buildWorkflowPayload, getAgentBindings } from './workflowPayload';

const agent = (id: string, label: string): VisualNode => ({
    id,
    type: 'agent',
    position: { x: 0, y: 0 },
    data: { label, config: { name: label, type: 'LlmAgent' } },
});

const tool = (id: string, label: string, toolType: string): VisualNode => ({
    id,
    type: 'tool',
    position: { x: 0, y: 100 },
    data: { label, config: { id, type: toolType } },
});

const flowEdge = (source: string, target: string): VisualEdge => ({
    id: `${source}-${target}`,
    source,
    target,
});

const auxEdge = (source: string, target: string, handle: string): VisualEdge => ({
    id: `${source}-${target}-${handle}`,
    source,
    target,
    sourceHandle: 'attach',
    targetHandle: handle,
});

describe('getAgentBindings', () => {
    it('resolves the backend agent id per agent node and ignores non-agents', () => {
        const nodes: VisualNode[] = [
            agent('n1', 'Search Assistant'),
            tool('t1', 'MCP Tool', 'mcp'),
            {
                id: 'blank',
                type: 'agent',
                position: { x: 0, y: 0 },
                // Blank palette agent: no id/name → resolves from the label.
                data: { label: 'CrewAI Agent', config: { type: 'LlmAgent' } },
            },
        ];
        const bindings = getAgentBindings(nodes);
        expect(bindings).toEqual([
            { nodeId: 'n1', label: 'Search Assistant', agentId: 'search_assistant' },
            { nodeId: 'blank', label: 'CrewAI Agent', agentId: 'crewai_agent' },
        ]);
    });

    it('prefers config.id over name/label', () => {
        const node: VisualNode = {
            id: 'x',
            type: 'agent',
            position: { x: 0, y: 0 },
            data: { label: 'Some Label', config: { id: 'general_assistant', name: 'Other' } },
        };
        expect(getAgentBindings([node])[0].agentId).toBe('general_assistant');
    });
});

describe('buildWorkflowPayload aux attachments', () => {
    const nodes = [
        agent('agent_a', 'Agent A'),
        agent('agent_b', 'Agent B'),
        tool('mcp_tool', 'MCP Tool', 'mcp'),
        tool('memory_store', 'Memory Store', 'memory'),
        tool('knowledge_src', 'Knowledge Source', 'knowledge'),
    ];
    const edges = [
        flowEdge('agent_a', 'agent_b'),
        auxEdge('mcp_tool', 'agent_a', 'tools'),
        auxEdge('memory_store', 'agent_a', 'memory'),
        auxEdge('knowledge_src', 'agent_b', 'knowledge'),
    ];
    const { create } = buildWorkflowPayload({ id: 'wf', name: 'WF', nodes, edges });

    it('attaches tool ids to the agent topology node', () => {
        const nodeA = create.topology.nodes.find((n) => n.id === 'agent_a')!;
        expect(nodeA.tools).toEqual(['mcp_tool']);
        expect(nodeA.memory).toBe(true);
        expect(nodeA.knowledge).toBeUndefined();
    });

    it('attaches knowledge to the right agent only', () => {
        const nodeB = create.topology.nodes.find((n) => n.id === 'agent_b')!;
        expect(nodeB.knowledge).toBe(true);
        expect(nodeB.memory).toBeUndefined();
        expect(nodeB.tools).toEqual([]);
    });

    it('keeps aux edges out of flow connections and topology edges', () => {
        expect(create.connections).toEqual([
            { from_node: 'agent_a', to_node: 'agent_b', type: 'sequential' },
        ]);
        expect(create.topology.edges).toHaveLength(1);
    });

    it('enables workflow-level memory/knowledge from attachments', () => {
        expect(create.memory.enabled).toBe(true);
        expect(create.knowledge.enabled).toBe(true);
    });

    it('preserves the full visual graph including aux edges', () => {
        expect(create.metadata.visual_canvas.edges).toHaveLength(4);
    });
});

describe('buildWorkflowPayload without attachments', () => {
    it('disables memory when no memory node exists (fixed always-on bug)', () => {
        const { create } = buildWorkflowPayload({
            id: 'wf2',
            name: 'WF2',
            nodes: [agent('agent_a', 'Agent A')],
            edges: [],
        });
        expect(create.memory.enabled).toBe(false);
        expect(create.knowledge.enabled).toBe(false);
        const nodeA = create.topology.nodes[0];
        expect(nodeA.tools).toEqual([]);
        expect(nodeA.memory).toBeUndefined();
    });

    it('legacy presence scan still enables memory for in-flow memory nodes', () => {
        const { create } = buildWorkflowPayload({
            id: 'wf3',
            name: 'WF3',
            nodes: [agent('agent_a', 'Agent A'), tool('memory_store', 'Memory Store', 'memory')],
            edges: [flowEdge('agent_a', 'memory_store')],
        });
        expect(create.memory.enabled).toBe(true);
        // but no per-node attachment without an aux handle edge
        expect(create.topology.nodes[0].memory).toBeUndefined();
    });
});
