import type { VisualEdge, VisualNode } from '../types/workflow';

const slugify = (value: string, fallback: string) => {
    const slug = value
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9_-]+/g, '_')
        .replace(/^_+|_+$/g, '');
    return slug || fallback;
};

const agentIdForNode = (node: VisualNode) => {
    const config = node.data?.config ?? {};
    return slugify(String(config.id ?? config.agent_id ?? config.name ?? node.data?.label ?? node.id), 'agent');
};

const inferPattern = (nodes: VisualNode[], edges: VisualEdge[]) => {
    const hasRouter = nodes.some((node) => node.type === 'router' || node.data?.config?.is_selector);
    const hasLoop = nodes.some((node) => node.data?.config?.type === 'LoopAgent');
    const agentCount = nodes.filter((node) => node.type === 'agent').length;
    const branchSources = new Set<string>();

    edges.forEach((edge) => {
        if (edges.filter((candidate) => candidate.source === edge.source).length > 1) {
            branchSources.add(edge.source);
        }
    });

    if (hasLoop) return 'loop';
    if (hasRouter) return 'selector';
    if (branchSources.size > 0) return 'parallel';
    if (agentCount <= 1) return 'single';
    return 'sequential';
};

const findEntryNode = (nodes: VisualNode[], edges: VisualEdge[]) => {
    const agentNodes = nodes.filter((node) => node.type === 'agent');
    const triggerEdge = edges.find((edge) => nodes.find((node) => node.id === edge.source)?.type === 'trigger');
    const targetAgent = triggerEdge ? agentNodes.find((node) => node.id === triggerEdge.target) : null;
    return targetAgent ?? agentNodes.find((node) => !edges.some((edge) => edge.target === node.id)) ?? agentNodes[0];
};

const processForPattern = (pattern: string) => (
    pattern === 'selector' || pattern === 'parallel' ? 'hierarchical' : 'sequential'
);

const taskForNode = (node: VisualNode, index: number) => {
    const config = node.data?.config ?? {};
    return {
        id: `${node.id}_task`,
        node_id: node.id,
        agent_id: agentIdForNode(node),
        description: String(
            config.task
            ?? config.goal
            ?? config.description
            ?? node.data?.description
            ?? `Run ${node.data?.label ?? node.id} as CrewAI task ${index + 1}.`,
        ),
        expected_output: String(
            config.expected_output
            ?? config.output_schema
            ?? 'A structured, useful result for the next node or final response.',
        ),
    };
};

export function buildWorkflowPayload(options: {
    id?: string | null;
    name: string;
    nodes: VisualNode[];
    edges: VisualEdge[];
}) {
    const id = slugify(options.id || options.name, 'workflow');
    const agentNodes = options.nodes.filter((node) => node.type === 'agent');
    const entryNode = findEntryNode(options.nodes, options.edges);
    const pattern = inferPattern(options.nodes, options.edges);

    const backendNodes = agentNodes.map((node) => ({
        id: node.id,
        agent_id: agentIdForNode(node),
        position: {
            x: node.position.x,
            y: node.position.y,
        },
        config: node.data?.config ?? {},
    }));

    const agentNodeIds = new Set(agentNodes.map((node) => node.id));
    const connections = options.edges
        .filter((edge) => agentNodeIds.has(edge.source) && agentNodeIds.has(edge.target))
        .map((edge) => ({
            from_node: edge.source,
            to_node: edge.target,
            type: 'sequential',
        }));

    const topologyEdges = connections.map((edge) => ({
        from_node: edge.from_node,
        to_node: edge.to_node,
        source: edge.from_node,
        target: edge.to_node,
        context_strategy: 'full',
    }));

    const topology = {
        type: pattern === 'single' ? 'single' : pattern === 'sequential' ? 'sequential' : 'graph',
        nodes: backendNodes.map((node) => ({
            id: node.id,
            agent_id: node.agent_id,
            description: node.config?.description ?? '',
            position: node.position,
            config: node.config,
        })),
        edges: topologyEdges,
        entry_node: entryNode?.id ?? backendNodes[0]?.id ?? '',
    };

    const process = processForPattern(pattern);
    const tasks = agentNodes.map(taskForNode);
    const memoryEnabled = options.nodes.some((node) => node.data?.config?.type === 'memory' || node.data?.config?.memory_enabled);
    const knowledgeEnabled = options.nodes.some((node) => node.data?.config?.type === 'knowledge' || node.data?.config?.knowledge_enabled);
    const guardrailsEnabled = options.nodes.some((node) => node.data?.config?.type === 'guardrail' || node.data?.config?.guardrails_enabled);

    const create = {
        id,
        name: options.name,
        description: `Workflow with ${options.nodes.length} nodes and ${options.edges.length} edges`,
        pattern,
        entry_agent_id: entryNode ? agentIdForNode(entryNode) : backendNodes[0]?.agent_id ?? '',
        max_turns: 10,
        enabled: true,
        workflow_type: pattern === 'single' ? 'chatbot' : pattern,
        persistence: pattern === 'single' ? 'mongo_only' : 'postgres',
        topology,
        execution_strategy: pattern === 'parallel' ? 'parallel' : 'sequential',
        runtime: 'crewai',
        process,
        tasks,
        memory: {
            enabled: memoryEnabled || true,
            retention: 'session',
        },
        knowledge: {
            enabled: knowledgeEnabled,
            collections: [],
            top_k: 5,
        },
        guardrails: {
            enabled: guardrailsEnabled || true,
            human_review: false,
            output_schema: 'text',
        },
        tracing: {
            enabled: true,
            amp_enabled: false,
            event_listeners: ['crew', 'agent', 'task', 'tool', 'llm', 'memory', 'knowledge'],
        },
        event_listeners: [],
        mcp_servers: [],
        output_schema: 'text',
        deployment_auth_mode: 'private',
        nodes: backendNodes,
        connections,
        metadata: {
            visual_canvas: {
                nodes: options.nodes,
                edges: options.edges,
                viewport: { x: 0, y: 0, zoom: 1 },
            },
        },
    };

    const update = {
        name: create.name,
        description: create.description,
        pattern,
        entry_agent_id: create.entry_agent_id,
        nodes: backendNodes,
        connections,
        topology,
        execution_strategy: create.execution_strategy,
        process,
        tasks,
        memory: create.memory,
        knowledge: create.knowledge,
        guardrails: create.guardrails,
        tracing: create.tracing,
        event_listeners: create.event_listeners,
        mcp_servers: create.mcp_servers,
        output_schema: create.output_schema,
        deployment_auth_mode: create.deployment_auth_mode,
        metadata: create.metadata,
    };

    return { id, create, update };
}
