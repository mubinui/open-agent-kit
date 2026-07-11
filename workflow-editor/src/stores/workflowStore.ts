
import { create } from 'zustand';
import {
    addEdge,
    applyNodeChanges,
    applyEdgeChanges,
} from '@xyflow/react';
import type {
    Connection,
    NodeChange,
    EdgeChange,
    OnNodesChange,
    OnEdgesChange,
    OnConnect,
} from '@xyflow/react';
import type { VisualNode, VisualEdge } from '../types/workflow';

export interface ExecutionTimelineItem {
    id: string;
    type: string;
    label: string;
    nodeId?: string;
    agentId?: string;
    payload: Record<string, any>;
    status: 'running' | 'success' | 'error' | 'info';
    timestamp: string;
}

interface WorkflowState {
    nodes: VisualNode[];
    edges: VisualEdge[];
    // Current workflow tracking (for n8n-style testing)
    currentWorkflowId: string | null;
    workflowName: string;
    // Trigger execution state
    executingTriggerId: string | null;
    triggerResult: 'success' | 'error' | null;
    liveRunActive: boolean;
    liveResponse: string;
    executionTimeline: ExecutionTimelineItem[];

    onNodesChange: OnNodesChange<VisualNode>;
    onEdgesChange: OnEdgesChange;
    onConnect: OnConnect;
    addNode: (node: VisualNode) => void;
    addNodes: (nodes: VisualNode[]) => void;
    addEdges: (edges: VisualEdge[]) => void;
    updateNodeData: (id: string, data: Record<string, any>) => void;
    setNodes: (nodes: VisualNode[]) => void;
    setEdges: (edges: VisualEdge[]) => void;
    // Workflow tracking actions
    setCurrentWorkflow: (id: string | null, name?: string) => void;
    setWorkflowName: (name: string) => void;
    loadWorkflow: (id: string, name: string, nodes: VisualNode[], edges: VisualEdge[]) => void;
    // Trigger execution actions
    setExecutingTrigger: (id: string | null, result?: 'success' | 'error' | null) => void;
    resetExecution: () => void;
    applyExecutionEvent: (event: Record<string, any>) => void;
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
    nodes: [],
    edges: [],
    currentWorkflowId: null,
    workflowName: 'Untitled Workflow',
    executingTriggerId: null,
    triggerResult: null,
    liveRunActive: false,
    liveResponse: '',
    executionTimeline: [],

    onNodesChange: (changes: NodeChange<VisualNode>[]) => {
        set({
            nodes: applyNodeChanges(changes, get().nodes),
        });
    },

    onEdgesChange: (changes: EdgeChange[]) => {
        set({
            edges: applyEdgeChanges(changes, get().edges),
        });
    },

    onConnect: (connection: Connection) => {
        set({
            edges: addEdge(connection, get().edges),
        });
    },

    addNode: (node: VisualNode) => {
        set({
            nodes: [...get().nodes, node],
        });
    },

    addNodes: (nodes: VisualNode[]) => {
        set({
            nodes: [...get().nodes, ...nodes],
        });
    },

    addEdges: (edges: VisualEdge[]) => {
        set({
            edges: [...get().edges, ...edges],
        });
    },

    updateNodeData: (id: string, data: Record<string, any>) => {
        set({
            nodes: get().nodes.map((node) => {
                if (node.id === id) {
                    return {
                        ...node,
                        data: { ...node.data, ...data },
                    };
                }
                return node;
            }),
        });
    },

    setNodes: (nodes: VisualNode[]) => {
        set({ nodes });
    },

    setEdges: (edges: VisualEdge[]) => {
        set({ edges });
    },

    setCurrentWorkflow: (id: string | null, name?: string) => {
        set({
            currentWorkflowId: id,
            workflowName: name || get().workflowName,
        });
    },

    setWorkflowName: (name: string) => {
        set({ workflowName: name });
    },

    loadWorkflow: (id: string, name: string, nodes: VisualNode[], edges: VisualEdge[]) => {
        set({
            currentWorkflowId: id,
            workflowName: name,
            nodes,
            edges,
        });
    },

    setExecutingTrigger: (id: string | null, result?: 'success' | 'error' | null) => {
        set({
            executingTriggerId: id,
            triggerResult: result ?? null,
        });
    },

    resetExecution: () => {
        set({
            liveRunActive: false,
            liveResponse: '',
            executionTimeline: [],
            nodes: get().nodes.map((node) => ({
                ...node,
                data: { ...node.data, status: node.data?.config ? 'configured' : 'idle' },
            })),
            edges: get().edges.map((edge) => ({
                ...edge,
                animated: false,
                style: { ...(edge.style ?? {}), stroke: '#b1b1b7' },
            })),
        });
    },

    applyExecutionEvent: (event: Record<string, any>) => {
        const eventType = String(event.type ?? 'info');
        const payload = (event.payload ?? {}) as Record<string, any>;
        const agentId = event.agent_id || payload.agent_id || payload.agent || payload.target_agent;
        const toolName = payload.name || payload.tool_name;
        const targetName = toolName || agentId;
        const nodes = get().nodes;
        const node = nodes.find((candidate) => {
            const config = candidate.data?.config ?? {};
            return (
                candidate.id === targetName ||
                candidate.data?.label === targetName ||
                config.id === targetName ||
                config.name === targetName ||
                config.agent_id === targetName ||
                candidate.data?.label === agentId ||
                config.id === agentId ||
                config.agent_id === agentId
            );
        });

        const status =
            eventType === 'error' ? 'error' :
                eventType === 'done' || eventType === 'tool_call_result' ? 'success' :
                    eventType === 'token' || eventType === 'reasoning_delta' ? 'info' :
                        'running';

        const labelMap: Record<string, string> = {
            start: 'Workflow started',
            token: 'Response token',
            reasoning_delta: 'Reasoning',
            tool_call_start: `Tool call: ${toolName ?? 'tool'}`,
            tool_call_result: `Tool result: ${toolName ?? 'tool'}`,
            agent_transfer: `Transfer to ${payload.target_agent ?? 'agent'}`,
            error: payload.error_message ?? 'Execution error',
            done: 'Workflow completed',
        };

        const timelineItem: ExecutionTimelineItem = {
            id: `${event.sequence ?? Date.now()}-${eventType}`,
            type: eventType,
            label: labelMap[eventType] ?? eventType,
            nodeId: node?.id,
            agentId,
            payload,
            status,
            timestamp: event.timestamp ?? new Date().toISOString(),
        };

        const responseAppend = eventType === 'token' ? String(payload.content ?? '') : '';
        const doneResult = eventType === 'done' ? payload.result?.response ?? '' : '';

        set({
            liveRunActive: eventType !== 'done' && eventType !== 'error',
            liveResponse: doneResult || (get().liveResponse + responseAppend),
            executionTimeline: [...get().executionTimeline, timelineItem],
            nodes: nodes.map((candidate) => {
                if (!node || candidate.id !== node.id) return candidate;
                return {
                    ...candidate,
                    data: {
                        ...candidate.data,
                        status: status === 'success' ? 'configured' : status === 'error' ? 'error' : 'running',
                    },
                };
            }),
            edges: get().edges.map((edge) => {
                if (!node || (edge.source !== node.id && edge.target !== node.id)) return edge;
                return {
                    ...edge,
                    animated: status === 'running',
                    style: {
                        ...(edge.style ?? {}),
                        stroke: status === 'error' ? '#ef4444' : status === 'success' ? '#22c55e' : '#2563eb',
                    },
                };
            }),
        });
    },
}));

