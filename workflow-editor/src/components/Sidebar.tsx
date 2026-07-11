
import React, { useEffect, useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import { Bot, Wrench, Play, GitBranch, Square, ChevronLeft, ChevronRight, MessageSquare, Link, Settings, Plus, Brain, FileSearch, ShieldCheck } from 'lucide-react';
import type { NodeType } from '../types/workflow';
import { useLibraryStore } from '../stores/libraryStore';
import { useLibraryModal } from '../App';
import { ResourceCard } from './studio/ResourceCard';
import { getAgentSummary, getToolSummary, getWorkflowSummary } from '../utils/studioDerivedState';


// --- Nested Sidebar Item Component ---
interface SidebarItemProps {
    type: NodeType;
    label: string;
    icon: LucideIcon;
    tone: 'agent' | 'tool' | 'workflow' | 'trigger' | 'logic' | 'output';
    config?: any;
    description?: string;
    children?: React.ReactNode;
    isCollapsed: boolean;
    level?: number; // Indentation level
}

const SidebarItem: React.FC<SidebarItemProps> = ({
    type,
    label,
    icon,
    tone,
    config,
    description,
    children,
    isCollapsed,
    level = 0
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const hasChildren = React.Children.count(children) > 0;

    // If main sidebar is collapsed, we don't show children/expansion
    const showChildren = !isCollapsed && isOpen && hasChildren;
    const agentSummary = type === 'agent' ? getAgentSummary(config) : null;
    const toolSummary = type === 'tool' ? getToolSummary(config) : null;
    const workflowSummary = type === 'workflow' ? getWorkflowSummary(config) : null;
    const badges = [
        agentSummary ? { label: agentSummary.model, tone: agentSummary.health } : null,
        agentSummary ? { label: `${agentSummary.toolCount} tools`, tone: agentSummary.toolCount > 0 ? 'ready' as const : 'muted' as const } : null,
        toolSummary ? { label: toolSummary.type === 'api' ? toolSummary.method : 'function', tone: toolSummary.health } : null,
        toolSummary ? { label: toolSummary.auth === 'none' ? 'no auth' : toolSummary.auth, tone: toolSummary.auth === 'none' ? 'muted' as const : 'warning' as const } : null,
        workflowSummary ? { label: workflowSummary.pattern, tone: workflowSummary.health } : null,
        workflowSummary ? { label: `${workflowSummary.nodeCount} nodes`, tone: 'muted' as const } : null,
    ].filter(Boolean) as Array<{ label: string; tone: 'ready' | 'warning' | 'error' | 'running' | 'muted' }>;

    return (
        <div className="select-none">
            <ResourceCard
                type={type}
                label={label}
                icon={icon}
                tone={tone}
                config={config}
                description={description}
                collapsed={isCollapsed}
                level={level}
                expandable={hasChildren}
                expanded={isOpen}
                onToggle={() => setIsOpen(!isOpen)}
                badges={badges}
                compact
            />

            {/* Recursive Children Rendering */}
            {showChildren && (
                <div className="border-l border-gray-100 ml-[22px] pl-1 relative">
                    {children}
                </div>
            )}
        </div>
    );
};


export const Sidebar = () => {
    const { savedAgents, savedTools, savedWorkflows, fetchLibraryItems } = useLibraryStore();
    const { openLibraryModal } = useLibraryModal();
    const [isCollapsed, setIsCollapsed] = useState(false);

    // Initial fetch
    useEffect(() => {
        fetchLibraryItems();
    }, []);

    const toggleCollapse = () => setIsCollapsed(!isCollapsed);

    // --- Helper to find entities by ID for nesting ---
    const findAgentById = (id: string) => savedAgents.find(a => a.id === id || a.name === id || a.config?.id === id);
    const findToolById = (id: string) => savedTools.find(t => t.id === id || t.name === id || t.config?.id === id);

    // --- Recursive Renders ---

    // Render Tools assigned to an Agent
    const renderAgentTools = (agentConfig: any) => {
        if (!agentConfig?.tools || !Array.isArray(agentConfig.tools)) return null;

        return agentConfig.tools.map((toolRef: string) => {
            const tool = findToolById(toolRef);
            // If tool found in library, use it; else verify if it is a string name
            const toolName = tool ? tool.name : toolRef;
            const toolConfig = tool ? tool.config : {}; // Default config if not found

            return (
                <SidebarItem
                    key={toolRef}
                    type="tool" // Nested tools are still 'tool' nodes if dragged
                    label={toolName}
                    icon={Wrench}
                    tone="tool"
                    isCollapsed={isCollapsed}
                    level={2}
                    config={toolConfig}
                />
            );
        });
    };

    // Render Agents inside a Workflow
    const renderWorkflowAgents = (workflow: any) => {
        // Look for agents in topology.nodes or topology.domain_agents
        const nodes = workflow.config?.topology?.nodes || [];
        // Map nodes to actual agents in library if possible
        return nodes.map((node: any) => {
            const agentId = node.agent_id || node.id;
            const agent = findAgentById(agentId);
            const label = agent ? agent.name : (node.name || agentId);
            const config = agent ? agent.config : {};
            const desc = node.description || (agent ? agent.description : '');

            return (
                <SidebarItem
                    key={node.id}
                    type="agent"
                    label={label}
                    icon={Bot}
                    tone="agent"
                    description={desc}
                    isCollapsed={isCollapsed}
                    level={1}
                    config={config}
                >
                    {/* Recursively show tools for this agent! */}
                    {renderAgentTools(config)}
                </SidebarItem>
            );
        });
    };


    return (
        <aside className={`${isCollapsed ? 'w-16' : 'w-[292px]'} bg-white dark:bg-[#0b111b] border-r border-[var(--color-ui-border)] flex flex-col h-full shadow-xl z-20 font-[var(--font-body)] transition-all duration-300 relative`}>
            {/* Collapse Toggle Button */}
            <button
                onClick={toggleCollapse}
                className="absolute -right-3 top-6 w-6 h-6 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-full shadow-md flex items-center justify-center text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-sky-400 z-50 transform hover:scale-110 transition-all"
            >
                {isCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>

            {/* Library Content */}
            <div className="flex-1 overflow-y-auto p-3 space-y-5 custom-scrollbar bg-gray-50/30 dark:bg-transparent">

                {/* --- Standard Components Section (Now at Top) --- */}
                <div className="space-y-1">
                    {!isCollapsed && (
                        <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 pl-2 flex items-center gap-1.5 sticky top-0 bg-gray-50/95 dark:bg-[#0b111b]/95 backdrop-blur-sm py-1 z-10">
                            <Square size={10} /> Base Components
                        </div>
                    )}

                    <div className="grid grid-cols-1 gap-1.5">
                        {/* Manual Trigger */}
                        <SidebarItem
                            type="trigger"
                            label="Manual Trigger"
                            icon={Play}
                            tone="trigger"
                            config={{ trigger_type: 'manual', label: 'Start' }}
                            isCollapsed={isCollapsed}
                        />

                        {/* Chat Trigger */}
                        <SidebarItem
                            type="trigger"
                            label="Chat Trigger"
                            icon={MessageSquare}
                            tone="trigger"
                            config={{ trigger_type: 'chat', label: 'On Chat' }}
                            isCollapsed={isCollapsed}
                        />

                        {/* Webhook Trigger */}
                        <SidebarItem
                            type="trigger"
                            label="Webhook"
                            icon={Link}
                            tone="trigger"
                            config={{ trigger_type: 'webhook', label: 'Webhook' }}
                            isCollapsed={isCollapsed}
                        />

                        {/* Generic Agent */}
                        <SidebarItem
                            type="agent"
                            label="CrewAI Agent"
                            icon={Bot}
                            tone="agent"
                            config={{ type: 'LlmAgent', role: '', goal: '', backstory: '', tools: [] }}
                            isCollapsed={isCollapsed}
                        />

                        <SidebarItem
                            type="agent"
                            label="CrewAI Task"
                            icon={Bot}
                            tone="agent"
                            config={{ type: 'LlmAgent', task: 'Describe the task objective', expected_output: 'Structured task result' }}
                            isCollapsed={isCollapsed}
                        />

                        {/* Add Tool - Opens Library Modal */}
                        <div
                            onClick={() => openLibraryModal('tools')}
                            className={`group flex items-center ${isCollapsed ? 'justify-center p-2' : 'gap-2 p-1.5'} bg-white dark:bg-slate-900/40 hover:bg-orange-50 dark:hover:bg-orange-950/20 rounded-lg cursor-pointer transition-all duration-200 border border-dashed border-orange-300 dark:border-orange-500/40 hover:border-orange-400 dark:hover:border-orange-500 mb-1`}
                            title="Create a new tool"
                        >
                            {/* Invisible chevron placeholder for alignment */}
                            {!isCollapsed && <div className="p-0.5 invisible"><ChevronRight size={12} /></div>}
                            <div className="p-1.5 bg-orange-50 dark:bg-orange-950/40 text-orange-600 dark:text-orange-400 rounded-lg shrink-0 shadow-sm border border-black/5 dark:border-white/5">
                                <Plus size={14} strokeWidth={2.5} />
                            </div>
                            {!isCollapsed && (
                                <span className="text-sm font-medium text-orange-600 dark:text-orange-400 group-hover:text-orange-700 dark:group-hover:text-orange-300">Add Tool</span>
                            )}
                        </div>

                        {/* Logic Nodes */}
                        <SidebarItem
                            type="router"
                            label="Flow Router"
                            icon={GitBranch}
                            tone="logic"
                            config={{ type: 'router', routing_mode: 'conditional' }}
                            isCollapsed={isCollapsed}
                        />

                        <SidebarItem
                            type="tool"
                            label="Memory Store"
                            icon={Brain}
                            tone="tool"
                            config={{ type: 'memory', memory_enabled: true, retention: 'session' }}
                            isCollapsed={isCollapsed}
                        />

                        <SidebarItem
                            type="tool"
                            label="Knowledge Source"
                            icon={FileSearch}
                            tone="tool"
                            config={{ type: 'knowledge', knowledge_enabled: true, top_k: 5 }}
                            isCollapsed={isCollapsed}
                        />

                        <SidebarItem
                            type="router"
                            label="Guardrail"
                            icon={ShieldCheck}
                            tone="logic"
                            config={{ type: 'guardrail', guardrails_enabled: true, output_schema: 'text' }}
                            isCollapsed={isCollapsed}
                        />

                        <SidebarItem
                            type="output"
                            label="Output"
                            icon={Square}
                            tone="output"
                            config={{ type: 'output' }}
                            isCollapsed={isCollapsed}
                        />
                    </div>
                </div>

                {/* --- Workflows Section --- */}
                {(savedWorkflows.length > 0) && (
                    <div className="space-y-1.5 pt-4 border-t border-gray-200/60 dark:border-slate-800/80">
                        {!isCollapsed && (
                            <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 pl-2 flex items-center gap-1.5 sticky top-0 bg-gray-50/95 dark:bg-[#0b111b]/95 backdrop-blur-sm py-1 z-10 border-b border-transparent">
                                <GitBranch size={10} /> Workflows
                            </div>
                        )}
                        {savedWorkflows.map(w => (
                            <SidebarItem
                                key={w.id}
                                type="workflow" // Explicit 'workflow' type for drop handler
                                label={w.name}
                                icon={GitBranch}
                                tone="workflow"
                                config={w.config}
                                description={w.description}
                                isCollapsed={isCollapsed}
                            >
                                {renderWorkflowAgents(w)}
                            </SidebarItem>
                        ))}
                    </div>
                )}

                {/* --- Agents Section --- */}
                {(savedAgents.length > 0 || !isCollapsed) && (
                    <div className="space-y-1.5 pt-4 border-t border-gray-200/60 dark:border-slate-800/80">
                        {!isCollapsed && (
                            <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 pl-2 flex items-center justify-between sticky top-0 bg-gray-50/95 dark:bg-[#0b111b]/95 backdrop-blur-sm py-1 z-10 pr-2">
                                <span className="flex items-center gap-1.5"><Bot size={10} /> Agents Library</span>
                                <button
                                    onClick={() => openLibraryModal('agents')}
                                    className="p-1 hover:bg-gray-200 dark:hover:bg-slate-800 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                                    title="Manage Agents"
                                >
                                    <Settings size={12} />
                                </button>
                            </div>
                        )}
                        {savedAgents.map(a => (
                            <SidebarItem
                                key={a.id}
                                type="agent"
                                label={a.name}
                                icon={Bot}
                                tone="agent"
                                config={a.config}
                                description={a.description}
                                isCollapsed={isCollapsed}
                            >
                                {renderAgentTools(a.config)}
                            </SidebarItem>
                        ))}
                    </div>
                )}

                {/* --- Tools Section --- */}
                {(savedTools.length > 0 || !isCollapsed) && (
                    <div className="space-y-1.5 pt-4 border-t border-gray-200/60 dark:border-slate-800/80">
                        {!isCollapsed && (
                            <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 pl-2 flex items-center justify-between sticky top-0 bg-gray-50/95 dark:bg-[#0b111b]/95 backdrop-blur-sm py-1 z-10 pr-2">
                                <span className="flex items-center gap-1.5"><Wrench size={10} /> Tools Library</span>
                                <button
                                    onClick={() => openLibraryModal('tools')}
                                    className="p-1 hover:bg-gray-200 dark:hover:bg-slate-800 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
                                    title="Manage Tools"
                                >
                                    <Settings size={12} />
                                </button>
                            </div>
                        )}
                        {savedTools.map(t => (
                            <SidebarItem
                                key={t.id}
                                type="tool"
                                label={t.name}
                                icon={Wrench}
                                tone="tool"
                                config={t.config}
                                description={t.description}
                                isCollapsed={isCollapsed}
                            />
                        ))}
                    </div>
                )}

            </div>

            {/* Footer */}
            {!isCollapsed && (
                <div className="p-3 border-t border-[var(--color-ui-border)] text-[10px] text-gray-400 text-center bg-gray-50/50 dark:bg-slate-900/30">
                    CrewAI Studio v1.2.0
                </div>
            )}
        </aside>
    );
};
