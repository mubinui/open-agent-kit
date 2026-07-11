import type { LibraryItem } from '../api/backendTypes';
import type { VisualNode } from '../types/workflow';

type ConfigLike = Record<string, any> | undefined;

const asArray = (value: unknown): string[] => (Array.isArray(value) ? value.map(String) : []);

const modelConfig = (config: ConfigLike) => config?.model_config ?? config?.llm_config ?? {};

export const compactModelName = (model?: string) => {
    if (!model) return 'No model';
    return model.split('/').pop() || model;
};

export const getAgentSummary = (config: ConfigLike) => {
    const model = modelConfig(config);
    const tools = asArray(config?.tools);
    const missingModel = !model?.model;
    const missingInstructions = !config?.instruction && !config?.system_message;

    return {
        strategy: String(config?.type ?? 'LlmAgent'),
        provider: String(model?.provider_id ?? 'provider'),
        model: compactModelName(String(model?.model ?? '')),
        toolCount: tools.length,
        tools,
        isSelector: Boolean(config?.is_selector),
        humanInput: String(config?.human_input_mode ?? 'NEVER'),
        health: missingModel || missingInstructions ? 'warning' as const : 'ready' as const,
        issues: [
            missingModel ? 'Missing model' : '',
            missingInstructions ? 'Missing instructions' : '',
        ].filter(Boolean),
    };
};

export const getToolSummary = (config: ConfigLike) => {
    const type = String(config?.type ?? 'function');
    const method = String(config?.http_method ?? 'GET');
    const auth = String(config?.auth_type ?? 'none');
    const missingEndpoint = type === 'api' && !config?.api_url;
    const missingEntrypoint = type !== 'api' && !config?.entrypoint;

    return {
        type,
        method,
        auth,
        endpoint: String(config?.api_url ?? config?.entrypoint ?? ''),
        enabled: config?.enabled !== false,
        health: missingEndpoint || missingEntrypoint ? 'warning' as const : 'ready' as const,
        issues: [
            missingEndpoint ? 'Missing API URL' : '',
            missingEntrypoint ? 'Missing entrypoint' : '',
        ].filter(Boolean),
    };
};

export const getWorkflowSummary = (config: ConfigLike) => {
    const topology = config?.topology ?? {};
    const nodes = asArray(topology.nodes ?? config?.nodes);
    const edges = asArray(topology.edges ?? config?.edges);

    return {
        pattern: String(config?.pattern ?? topology.type ?? 'workflow'),
        nodeCount: nodes.length || Number(config?.nodes?.length ?? 0),
        edgeCount: edges.length || Number(config?.edges?.length ?? 0),
        entryNode: String(topology.entry_node ?? config?.entry_agent_id ?? 'not set'),
        health: topology.entry_node || config?.entry_agent_id ? 'ready' as const : 'warning' as const,
        issues: topology.entry_node || config?.entry_agent_id ? [] : ['Missing entry node'],
    };
};

export const getNodeSummary = (node: VisualNode) => {
    if (node.type === 'agent') return getAgentSummary(node.data?.config);
    if (node.type === 'tool') return getToolSummary(node.data?.config);
    if (node.type === 'workflow') return getWorkflowSummary(node.data?.config);
    return null;
};

export const countAgentUsage = (agents: LibraryItem[], workflows: LibraryItem[]) => {
    const usage = new Map<string, number>();
    agents.forEach((agent) => usage.set(agent.id, 0));
    workflows.forEach((workflow) => {
        const nodes = workflow.config?.topology?.nodes ?? workflow.config?.nodes ?? [];
        nodes.forEach((node: any) => {
            const agentId = String(node.agent_id ?? node.id ?? '');
            if (usage.has(agentId)) usage.set(agentId, (usage.get(agentId) ?? 0) + 1);
        });
    });
    return usage;
};
