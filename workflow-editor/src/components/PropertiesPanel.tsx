import React, { useEffect, useState } from 'react';
import { X, Trash2, Save, ChevronDown, ChevronRight, Check, Activity, FlaskConical, Gauge, Settings2, Sparkles, Wrench, Layers } from 'lucide-react';
import { useStoreWithEqualityFn } from 'zustand/traditional';
import { useShallow } from 'zustand/react/shallow';
import { useWorkflowStore } from '../stores/workflowStore';
import { useLibraryStore } from '../stores/libraryStore';
import { InspectorTabs } from './studio/InspectorTabs';
import { StatusBadge } from './studio/StatusBadge';
import { getAgentSummary, getToolSummary } from '../utils/studioDerivedState';

// CrewAI & Model Definitions
const AGENT_TYPES = [
    { id: 'LlmAgent', name: 'LLM Agent (Chat/Reasoning)' },
    { id: 'RecursiveAgent', name: 'Recursive Selector Agent' },
    { id: 'SequentialAgent', name: 'Sequential Agent' },
    { id: 'ParallelAgent', name: 'Parallel Agent' },
    { id: 'LoopAgent', name: 'Loop Agent' },
    { id: 'conversable', name: 'Conversable Agent (Legacy)' }
];

const PROVIDERS = [
    { id: 'openrouter', name: 'OpenRouter' },
    { id: 'vllm', name: 'vLLM (Self-Hosted)' },
    { id: 'ollama', name: 'Ollama (Local)' },
    { id: 'openai', name: 'OpenAI' },
    { id: 'anthropic', name: 'Anthropic' },
    { id: 'google', name: 'Google Gemini' },
];

const HUMAN_INPUT_MODES = [
    { id: 'NEVER', name: 'Never' },
    { id: 'ALWAYS', name: 'Always' },
    { id: 'TERMINATE', name: 'Terminate' },
];

export const PropertiesPanel = () => {
    // Custom equality (not just useShallow) because a node being *dragged* gets a new
    // object reference every frame via applyNodeChanges (position updates), even while
    // its `data`/`type`/`id` stay referentially the same. Comparing on those three only
    // means this panel — and its many form fields — no longer re-renders on every
    // mousemove while the currently-selected node is being moved around the canvas.
    const selectedNode = useStoreWithEqualityFn(
        useWorkflowStore,
        (state) => state.nodes.find((n) => n.selected),
        (a, b) => a?.id === b?.id && a?.type === b?.type && a?.data === b?.data,
    );
    const { updateNodeData, onNodesChange } = useWorkflowStore(
        useShallow((state) => ({
            updateNodeData: state.updateNodeData,
            onNodesChange: state.onNodesChange,
        })),
    );
    const isNodeDragging = useWorkflowStore((state) => state.isNodeDragging);
    const { savedTools, executeTool } = useLibraryStore();

    // Core State
    const [label, setLabel] = useState('');
    const [description, setDescription] = useState('');

    // Dynamic Configuration State
    const [config, setConfig] = useState<Record<string, any>>({});

    // UI State
    const [activeSection, setActiveSection] = useState<string>('basic');
    const [activeInspectorTab, setActiveInspectorTab] = useState('overview');
    const [testArgs, setTestArgs] = useState('{\n  "input": "hello"\n}');
    const [testResult, setTestResult] = useState('');
    const [isTesting, setIsTesting] = useState(false);

    // Sync state when selection changes
    useEffect(() => {
        if (selectedNode) {
            setLabel((selectedNode.data?.label as string) || '');
            setDescription((selectedNode.data?.description as string) || '');
            const initialConfig = (selectedNode.data?.config as Record<string, any>) || {};
            if (!initialConfig.tools) initialConfig.tools = [];
            setConfig(initialConfig);
            setActiveInspectorTab('overview');
            setTestResult('');
        }
    }, [selectedNode?.id]);

    // Stay out of the way while a node is mid-drag: the inspector only appears once the
    // drag is released, so moving a component never opens or resizes UI around it.
    if (!selectedNode || isNodeDragging) return null;

    const handleSave = () => {
        if (selectedNode) {
            updateNodeData(selectedNode.id, {
                label,
                description,
                config
            });
        }
    };

    const updateConfig = (key: string, value: any) => {
        setConfig(prev => ({ ...prev, [key]: value }));
    };

    const updateNestedConfig = (parent: string, key: string, value: any) => {
        setConfig(prev => ({
            ...prev,
            [parent]: {
                ...prev[parent],
                [key]: value
            }
        }));
    };

    const toggleTool = (toolName: string) => {
        const currentTools = config.tools || [];
        if (currentTools.includes(toolName)) {
            updateConfig('tools', currentTools.filter((t: string) => t !== toolName));
        } else {
            updateConfig('tools', [...currentTools, toolName]);
        }
    };

    const handleDelete = () => {
        if (selectedNode) {
            // @ts-ignore
            onNodesChange([{ id: selectedNode.id, type: 'remove' }]);
        }
    };

    const runToolTest = async () => {
        const toolId = String(config.id || config.name || selectedNode.data?.label || '');
        if (!toolId) return;
        setIsTesting(true);
        setTestResult('');
        try {
            const parsedArgs = JSON.parse(testArgs || '{}');
            const result = await executeTool(toolId, parsedArgs);
            setTestResult(JSON.stringify(result, null, 2));
        } catch (error) {
            setTestResult((error as Error).message);
        } finally {
            setIsTesting(false);
        }
    };

    const renderStudioSummary = () => {
        if (selectedNode.type === 'agent') {
            const summary = getAgentSummary(config);
            return (
                <div className="rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-gradient-to-b from-white to-slate-50/50 dark:from-slate-900/60 dark:to-slate-950/40 p-4 shadow-xs">
                    <div className="mb-3.5 flex items-start justify-between gap-3">
                        <div>
                            <div className="text-xs font-black text-slate-800 dark:text-slate-200 tracking-wide uppercase">Agent Diagnostics</div>
                            <div className="text-[11px] text-slate-500 dark:text-slate-400 font-medium mt-0.5">Strategy layer verification logic</div>
                        </div>
                        <StatusBadge tone={summary.health} label={summary.health === 'ready' ? 'Ready' : 'Needs setup'} />
                    </div>
                    <div className="grid grid-cols-2 gap-2.5 text-xs">
                        <div className="rounded-lg bg-white dark:bg-slate-900/80 border border-slate-100 dark:border-slate-800 p-2.5 shadow-2xs">
                            <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Strategy</div>
                            <div className="font-extrabold text-slate-700 dark:text-slate-300 mt-0.5 truncate">{summary.strategy}</div>
                        </div>
                        <div className="rounded-lg bg-white dark:bg-slate-900/80 border border-slate-100 dark:border-slate-800 p-2.5 shadow-2xs">
                            <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Engine</div>
                            <div className="font-extrabold text-slate-700 dark:text-slate-300 mt-0.5 truncate">{summary.model}</div>
                        </div>
                        <div className="rounded-lg bg-white dark:bg-slate-900/80 border border-slate-100 dark:border-slate-800 p-2.5 shadow-2xs">
                            <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Tool Cap</div>
                            <div className="font-extrabold text-blue-600 dark:text-blue-400 mt-0.5">{summary.toolCount} Hooked</div>
                        </div>
                        <div className="rounded-lg bg-white dark:bg-slate-900/80 border border-slate-100 dark:border-slate-800 p-2.5 shadow-2xs">
                            <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Human Loop</div>
                            <div className="font-extrabold text-slate-700 dark:text-slate-300 mt-0.5 truncate">{summary.humanInput}</div>
                        </div>
                    </div>
                    {summary.issues.length > 0 && (
                        <div className="mt-3 text-[11px] font-medium bg-amber-50/80 dark:bg-amber-950/30 border border-amber-200/60 dark:border-amber-900/50 text-amber-800 dark:text-amber-400 rounded-lg p-2.5">
                            {summary.issues.join(' · ')}
                        </div>
                    )}
                </div>
            );
        }

        if (selectedNode.type === 'tool') {
            const summary = getToolSummary(config);
            return (
                <div className="rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-gradient-to-b from-white to-slate-50/50 dark:from-slate-900/60 dark:to-slate-950/40 p-4 shadow-xs">
                    <div className="mb-3.5 flex items-start justify-between gap-3">
                        <div>
                            <div className="text-xs font-black text-slate-800 dark:text-slate-200 tracking-wide uppercase">Tool Interface</div>
                            <div className="text-[11px] text-slate-500 dark:text-slate-400 font-medium mt-0.5">Connectivity protocol summary</div>
                        </div>
                        <StatusBadge tone={summary.health} label={summary.enabled ? 'Live Link' : 'Disabled'} />
                    </div>
                    <div className="space-y-2 text-xs">
                        <div className="flex items-center justify-between rounded-lg bg-white dark:bg-slate-900/80 border border-slate-100 dark:border-slate-800 p-2.5 shadow-2xs">
                            <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Type protocol</span>
                            <span className="font-extrabold text-slate-800 dark:text-slate-200 font-mono text-[11px]">{summary.type}</span>
                        </div>
                        <div className="flex items-center justify-between rounded-lg bg-white dark:bg-slate-900/80 border border-slate-100 dark:border-slate-800 p-2.5 shadow-2xs">
                            <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Authentication</span>
                            <span className="font-extrabold text-slate-800 dark:text-slate-200 font-mono text-[11px]">{summary.auth}</span>
                        </div>
                        <div className="rounded-lg bg-white dark:bg-slate-900/80 border border-slate-100 dark:border-slate-800 p-2.5 shadow-2xs">
                            <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">Resolution Target</div>
                            <div className="truncate font-mono text-[11px] text-blue-600 dark:text-blue-400 font-bold mt-0.5">{summary.endpoint || 'Not configured'}</div>
                        </div>
                    </div>
                    {summary.issues.length > 0 && (
                        <div className="mt-3 text-[11px] font-medium bg-amber-50/80 dark:bg-amber-950/30 border border-amber-200/60 dark:border-amber-900/50 text-amber-800 dark:text-amber-400 rounded-lg p-2.5">
                            {summary.issues.join(' · ')}
                        </div>
                    )}
                </div>
            );
        }

        return (
            <div className="rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-slate-50/60 dark:bg-slate-900/40 p-4 text-xs text-slate-500 dark:text-slate-400 font-medium text-center">
                Configure pipeline bindings via the runtime sub-inspector.
            </div>
        );
    };

    const renderToolTest = () => (
        <div className="space-y-3">
            <div className="rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/60 p-4 shadow-xs">
                <div className="mb-2.5 text-xs font-black text-slate-800 dark:text-slate-200 uppercase tracking-wide">Payload Harness Injection</div>
                <textarea
                    value={testArgs}
                    onChange={(event) => setTestArgs(event.target.value)}
                    className="min-h-28 w-full rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/50 p-3 font-mono text-xs text-slate-900 dark:text-slate-100 focus:bg-white dark:focus:bg-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 transition-all"
                />
                <button
                    onClick={runToolTest}
                    disabled={isTesting}
                    type="button"
                    className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-slate-900 dark:bg-slate-800 hover:bg-slate-800 dark:hover:bg-slate-700 py-2.5 text-xs font-bold text-white transition-all shadow-sm disabled:opacity-60"
                >
                    <FlaskConical size={14} className="text-blue-400" />
                    {isTesting ? 'Evaluating Sandboxed Hook...' : 'Trigger Sandbox Execution'}
                </button>
            </div>
            {testResult && (
                <div className="rounded-xl bg-slate-950 p-4 shadow-inner border border-slate-900">
                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 flex items-center justify-between">
                        <span>Output Stream</span>
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    </div>
                    <pre className="max-h-72 overflow-auto font-mono text-[11px] text-emerald-400 leading-normal">{testResult}</pre>
                </div>
            )}
        </div>
    );

    // --- Premium Glassmorphic Embedded Section Wrappers ---
    const renderSection = (title: string, id: string, children: React.ReactNode) => (
        <div className="border border-slate-200/80 dark:border-slate-800/80 rounded-xl overflow-hidden bg-white dark:bg-slate-900/40 shadow-2xs mb-3.5 transition-all">
            <button
                onClick={() => setActiveSection(activeSection === id ? '' : id)}
                type="button"
                className="w-full flex items-center justify-between px-3.5 py-3 bg-gradient-to-r from-slate-50/80 to-white dark:from-slate-900/80 dark:to-slate-900/30 hover:from-slate-100/50 dark:hover:from-slate-800/50 transition-all text-left border-b border-slate-100/60 dark:border-slate-800/60"
            >
                <span className="font-bold text-slate-800 dark:text-slate-200 text-xs tracking-wide uppercase">{title}</span>
                {activeSection === id ? <ChevronDown size={14} className="text-slate-400" /> : <ChevronRight size={14} className="text-slate-400" />}
            </button>
            {activeSection === id && (
                <div className="p-4 space-y-4 bg-white dark:bg-slate-900/20">
                    {children}
                </div>
            )}
        </div>
    );

    const renderModelConfig = () => {
        let providerId = config.model_config?.provider_id || config.llm_config?.provider_id || '';
        const modelName = config.model_config?.model || config.llm_config?.model || '';

        if (!providerId && modelName.includes('/')) {
            providerId = modelName.split('/')[0];
        }

        const showBaseUrl = providerId === 'vllm' || providerId === 'ollama';

        return renderSection('Inference Driver', 'model_config', (
            <div className="space-y-4">
                <div className="space-y-1.5">
                    <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Gateway Provider</label>
                    <select
                        value={providerId}
                        onChange={(e) => updateNestedConfig('model_config', 'provider_id', e.target.value)}
                        className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                    >
                        <option value="">Select Gateway Base...</option>
                        {PROVIDERS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                    </select>
                </div>

                <div className="space-y-1.5">
                    <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Model Weight String</label>
                    <input
                        type="text"
                        value={modelName}
                        onChange={(e) => updateNestedConfig('model_config', 'model', e.target.value)}
                        className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                        placeholder="openai/gpt-4o, google/gemini-2.5-pro"
                    />
                </div>

                {showBaseUrl && (
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Base Uniform Resource Locator</label>
                        <input
                            type="text"
                            value={config.model_config?.base_url || ''}
                            onChange={(e) => updateNestedConfig('model_config', 'base_url', e.target.value)}
                            className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                            placeholder={providerId === 'ollama' ? 'http://localhost:11434' : 'https://api.vllm.ai/v1'}
                        />
                    </div>
                )}

                <div className="space-y-1.5 pt-1">
                    <div className="flex justify-between items-center">
                        <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Sampling Entropy (Temperature)</label>
                        <span className="text-[11px] font-mono font-bold bg-blue-50 dark:bg-blue-950/50 text-blue-600 dark:text-sky-400 px-1.5 py-0.2 rounded border border-blue-100 dark:border-blue-900/40">
                            {config.model_config?.temperature ?? config.llm_config?.temperature ?? 0.7}
                        </span>
                    </div>
                    <input
                        type="range"
                        min="0"
                        max="2"
                        step="0.05"
                        value={config.model_config?.temperature ?? config.llm_config?.temperature ?? 0.7}
                        onChange={(e) => updateNestedConfig('model_config', 'temperature', parseFloat(e.target.value))}
                        className="w-full h-1.5 bg-slate-200 dark:bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-600"
                    />
                </div>

                <div className="space-y-1.5">
                    <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Context Limit Capacity</label>
                    <input
                        type="number"
                        value={config.model_config?.max_tokens || config.llm_config?.max_tokens || 2048}
                        onChange={(e) => updateNestedConfig('model_config', 'max_tokens', parseInt(e.target.value) || 2048)}
                        className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                    />
                </div>
            </div>
        ));
    };

    const renderToolsSelector = () => {
        const assignedTools = config.tools || [];
        return renderSection('Tool Chain Attachments', 'tools_selector', (
            <div className="space-y-3">
                <div className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">Toggle capability slots visible to parent node logic:</div>
                <div className="max-h-48 overflow-y-auto space-y-1.5 border border-slate-200/60 dark:border-slate-800/60 rounded-xl p-2.5 bg-slate-50/40 dark:bg-slate-950/40">
                    {savedTools.map(tool => {
                        const isSelected = assignedTools.includes(tool.name);
                        return (
                            <div
                                key={tool.id}
                                onClick={() => toggleTool(tool.name)}
                                className={`flex items-center gap-2.5 p-2 rounded-lg cursor-pointer transition-all text-xs select-none
                                    ${isSelected ? 'bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 border border-blue-600/40 font-bold shadow-2xs' : 'hover:bg-white dark:hover:bg-slate-900 text-slate-600 dark:text-slate-400 font-medium border border-transparent'}`}
                            >
                                <div className={`w-4 h-4 rounded flex items-center justify-center border shrink-0 transition-colors ${isSelected ? 'bg-blue-600 border-blue-600 text-white' : 'bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700'}`}>
                                    {isSelected && <Check size={10} strokeWidth={3} />}
                                </div>
                                <span className="truncate">{tool.name}</span>
                            </div>
                        );
                    })}
                    {savedTools.length === 0 && (
                        <div className="text-xs text-slate-400 font-medium text-center py-4">Registry completely void. Define sub-blocks first.</div>
                    )}
                </div>
            </div>
        ));
    };

    const renderAgentConfig = () => {
        const agentType = config.type || 'LlmAgent';
        const isLlmAgent = agentType === 'LlmAgent' || agentType === 'ReasoningAgent' || agentType === 'conversable';

        return (
            <>
                {renderSection('Strategy Role Specs', 'agent_settings', (
                    <>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Executor Base Strategy</label>
                            <select
                                value={config.type || 'LlmAgent'}
                                onChange={(e) => updateConfig('type', e.target.value)}
                                className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                            >
                                {AGENT_TYPES.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                            </select>
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Output State Variable Key</label>
                            <input
                                type="text"
                                value={config.output_key || ''}
                                onChange={(e) => updateConfig('output_key', e.target.value)}
                                className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                                placeholder="e.g. summarized_analysis"
                            />
                            <p className="text-[9px] text-slate-400 font-medium">Binds computed stream output into standard state cache dictionary.</p>
                        </div>

                        <div className="flex items-center justify-between p-2.5 bg-slate-50 dark:bg-slate-950/40 rounded-lg border border-slate-200/80 dark:border-slate-800/80">
                            <span className="text-xs font-bold text-slate-700 dark:text-slate-300">Router Switch Subagent</span>
                            <input
                                type="checkbox"
                                checked={config.is_selector || false}
                                onChange={(e) => updateConfig('is_selector', e.target.checked)}
                                className="accent-blue-600 w-4 h-4 rounded text-blue-600 focus:ring-blue-500"
                            />
                        </div>

                        {agentType === 'LoopAgent' && (
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Cyclic Upper Bounds</label>
                                <input
                                    type="number"
                                    value={config.loop_config?.max_loops || 5}
                                    onChange={(e) => updateNestedConfig('loop_config', 'max_loops', parseInt(e.target.value) || 1)}
                                    className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                                />
                            </div>
                        )}

                        {(isLlmAgent || config.is_selector) && (
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">System Directives / Behavioral Boundaries</label>
                                <textarea
                                    value={config.instruction || config.system_message || ''}
                                    onChange={(e) => {
                                        updateConfig('instruction', e.target.value);
                                        updateConfig('system_message', e.target.value);
                                    }}
                                    className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all min-h-[140px] leading-relaxed"
                                    placeholder="Define objective criteria, operational personas, constraints, and explicit formatted formats..."
                                />
                            </div>
                        )}

                        <div className="space-y-1.5">
                            <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Human Overrule Interruption Mode</label>
                            <select
                                value={config.human_input_mode || 'NEVER'}
                                onChange={(e) => updateConfig('human_input_mode', e.target.value)}
                                className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                            >
                                {HUMAN_INPUT_MODES.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                            </select>
                        </div>
                    </>
                ))}
            </>
        );
    };

    const renderTriggerConfig = () => {
        const triggerType = config.trigger_type || 'manual';

        return (
            <>
                {renderSection('Trigger Handlers', 'trigger_settings', (
                    <>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Entry Interface</label>
                            <select
                                value={triggerType}
                                onChange={(e) => updateConfig('trigger_type', e.target.value)}
                                className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                            >
                                <option value="manual">Manual Push Trigger</option>
                                <option value="chat">Conversational State Catch</option>
                                <option value="webhook">RESTful Webhook Receiver</option>
                            </select>
                        </div>

                        {triggerType === 'webhook' && (
                            <>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Public Webhook URL String</label>
                                    <input
                                        type="text"
                                        value={config.public_slug || ''}
                                        onChange={(e) => updateConfig('public_slug', e.target.value)}
                                        className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                                        placeholder="customer-support-ingest"
                                    />
                                    <p className="text-[9px] text-slate-400 font-mono">Hook: /api/v1/webhooks/{config.public_slug || '{slug}'}</p>
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">JSON Pointer Extraction Map</label>
                                    <textarea
                                        value={config.input_mapping_text || JSON.stringify(config.input_mapping || { message: '$.message' }, null, 2)}
                                        onChange={(e) => updateConfig('input_mapping_text', e.target.value)}
                                        className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all min-h-[90px]"
                                    />
                                </div>
                            </>
                        )}

                        {(triggerType === 'chat' || triggerType === 'webhook') && (
                            <>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Session Token Filter</label>
                                    <select
                                        value={config.auth_mode || 'public'}
                                        onChange={(e) => updateConfig('auth_mode', e.target.value)}
                                        className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                                    >
                                        <option value="public">Fully Permissive</option>
                                        <option value="api_key">Shared Application Key Check</option>
                                        <option value="jwt">JSON Web Token Signing Proof</option>
                                    </select>
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1.5">
                                        <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Provider</label>
                                        <input
                                            type="text"
                                            value={config.provider_id || 'openrouter'}
                                            onChange={(e) => updateConfig('provider_id', e.target.value)}
                                            className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Fallback Model</label>
                                        <input
                                            type="text"
                                            value={config.model_id || 'openai/gpt-4o'}
                                            onChange={(e) => updateConfig('model_id', e.target.value)}
                                            className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                                        />
                                    </div>
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Initial Greeting Header</label>
                                    <textarea
                                        value={config.greeting || 'Hi, how can I help?'}
                                        onChange={(e) => updateConfig('greeting', e.target.value)}
                                        className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all min-h-[70px]"
                                    />
                                </div>
                            </>
                        )}

                        <div className="space-y-1.5">
                            <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Downstream Cascade Execution Slug</label>
                            <input
                                type="text"
                                value={config.workflow_id || ''}
                                onChange={(e) => updateConfig('workflow_id', e.target.value)}
                                className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                                placeholder="e.g. main_orchestration"
                            />
                        </div>
                    </>
                ))}
            </>
        );
    };

    const renderToolConfig = () => (
        <>
            {renderSection('Protocol Payload Parameters', 'tool_details', (
                <>
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Interface Mechanism</label>
                        <select
                            value={config.type || 'function'}
                            onChange={(e) => updateConfig('type', e.target.value)}
                            className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                        >
                            <option value="function">Local Python Thread Execution</option>
                            <option value="api">External Network Resource Fetch</option>
                        </select>
                    </div>

                    {config.type === 'function' && (
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Target Resolution Import Path</label>
                            <input
                                type="text"
                                value={config.entrypoint || ''}
                                onChange={(e) => updateConfig('entrypoint', e.target.value)}
                                className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                                placeholder="package.module:function_name"
                            />
                        </div>
                    )}

                    {config.type === 'api' && (
                        <div className="space-y-4">
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Endpoint URL String</label>
                                <input
                                    type="text"
                                    value={config.api_url || ''}
                                    onChange={(e) => updateConfig('api_url', e.target.value)}
                                    className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-mono text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                                    placeholder="https://api.example.com/v1/data"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Verb</label>
                                    <select
                                        value={config.http_method || 'GET'}
                                        onChange={(e) => updateConfig('http_method', e.target.value)}
                                        className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                                    >
                                        <option>GET</option>
                                        <option>POST</option>
                                        <option>PUT</option>
                                        <option>DELETE</option>
                                    </select>
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Negotiation Token</label>
                                    <select
                                        value={config.auth_type || 'none'}
                                        onChange={(e) => updateConfig('auth_type', e.target.value)}
                                        className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                                    >
                                        <option value="none">Public</option>
                                        <option value="bearer">Bearer Auth</option>
                                        <option value="api_key">API Custom Header</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            ))}
        </>
    );

    return (
        <div className="w-[400px] shrink-0 h-full bg-white dark:bg-[#0b111b] border-l border-[var(--color-ui-border)] shadow-xl flex flex-col antialiased animate-in slide-in-from-right duration-200">
            {/* Docked Inspector Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 dark:border-slate-800 bg-gradient-to-r from-slate-50/60 to-white dark:from-[#0f1723]/80 dark:to-[#0b111b] shrink-0">
                <div className="flex items-center gap-2.5">
                    <div className="p-1.5 bg-blue-600 text-white rounded-lg shadow-2xs">
                        <Settings2 size={15} />
                    </div>
                    <div>
                        <h3 className="font-extrabold text-slate-800 dark:text-slate-200 text-xs tracking-wide uppercase">Node Parameters</h3>
                        <div className="flex items-center gap-2 mt-0.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse"></span>
                            <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 font-mono uppercase tracking-wider">
                                Type: {selectedNode.type}
                            </span>
                        </div>
                    </div>
                </div>
                <button
                    onClick={() => {
                        // @ts-ignore
                        onNodesChange([{ id: selectedNode.id, type: 'select', selected: false }]);
                    }}
                    type="button"
                    className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60 p-1.5 rounded-xl transition-all"
                >
                    <X size={15} />
                </button>
            </div>

            {/* Seamless Tab Strips & Field Scrollable View */}
            <div className="p-5 overflow-y-auto flex-1 custom-scrollbar min-h-0 space-y-4">
                <InspectorTabs
                    activeTab={activeInspectorTab}
                    onChange={setActiveInspectorTab}
                    tabs={[
                        { id: 'overview', label: 'Overview', icon: Activity },
                        { id: 'model', label: 'Driver', icon: Sparkles, disabled: selectedNode.type !== 'agent' },
                        { id: 'tools', label: selectedNode.type === 'tool' ? 'Config' : 'Tools', icon: Wrench, disabled: selectedNode.type === 'trigger' },
                        { id: 'runtime', label: 'Runtime', icon: Layers },
                        { id: 'test', label: 'Test', icon: Gauge, disabled: selectedNode.type === 'output' },
                    ]}
                />

                {/* Core Overview Diagnostics */}
                {activeInspectorTab === 'overview' && (
                    <div className="space-y-4 animate-in fade-in duration-200">
                        {renderStudioSummary()}

                        <div className="space-y-4 rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-white dark:bg-slate-900/40 p-4 shadow-2xs">
                            <div className="text-xs font-black text-slate-800 dark:text-slate-200 tracking-wide uppercase mb-1">Canvas Identifiers</div>
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Label Title</label>
                                <input
                                    type="text"
                                    value={label}
                                    onChange={(e) => setLabel(e.target.value)}
                                    onBlur={handleSave}
                                    className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-bold text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all h-9"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-extrabold text-slate-500 uppercase tracking-wider">Semantic Description Note</label>
                                <textarea
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    onBlur={handleSave}
                                    className="w-full px-3 py-2 bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-300 resize-y min-h-[60px] focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-600 focus:bg-white dark:focus:bg-slate-900 transition-all leading-relaxed"
                                />
                            </div>
                        </div>
                    </div>
                )}

                {/* Switchable Inspectors */}
                <div className="space-y-4 animate-in fade-in duration-200">
                    {selectedNode.type === 'agent' && activeInspectorTab === 'model' && renderModelConfig()}
                    {selectedNode.type === 'agent' && activeInspectorTab === 'tools' && renderToolsSelector()}
                    {selectedNode.type === 'agent' && activeInspectorTab === 'runtime' && renderAgentConfig()}
                    {selectedNode.type === 'tool' && activeInspectorTab === 'tools' && renderToolConfig()}
                    {selectedNode.type === 'tool' && activeInspectorTab === 'test' && renderToolTest()}
                    {selectedNode.type === 'trigger' && activeInspectorTab === 'runtime' && renderTriggerConfig()}
                    
                    {activeInspectorTab === 'test' && selectedNode.type === 'agent' && (
                        <div className="rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-slate-50/60 dark:bg-slate-900/40 p-4 text-xs text-slate-500 dark:text-slate-400 font-medium text-center">
                            Trigger full canvas traversal from control playback hub to track agent-level sequential reasoning outputs.
                        </div>
                    )}
                    {activeInspectorTab === 'test' && selectedNode.type === 'trigger' && (
                        <div className="rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-slate-50/60 dark:bg-slate-900/40 p-4 text-xs text-slate-500 dark:text-slate-400 font-medium text-center">
                            Trigger hooks can be activated directly via interactive testing push endpoints.
                        </div>
                    )}
                    {activeInspectorTab !== 'overview' && selectedNode.type === 'output' && (
                        <div className="rounded-xl border border-slate-200/80 dark:border-slate-800/80 bg-slate-50/60 dark:bg-slate-900/40 p-4 text-xs text-slate-500 dark:text-slate-400 font-medium text-center">
                            Terminal node. Imposes hard pipeline exit blocks upon data pipeline traversal success.
                        </div>
                    )}
                </div>
            </div>

            {/* Bottom Actions Controls */}
            <div className="p-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-950/30 flex gap-3 shrink-0">
                <button
                    onClick={handleDelete}
                    type="button"
                    className="flex-1 flex items-center justify-center gap-1.5 py-2.5 bg-white dark:bg-slate-900 border border-red-200 dark:border-red-900/40 text-red-600 dark:text-red-400 rounded-xl text-xs font-bold hover:bg-red-50/60 dark:hover:bg-red-950/30 transition-all shadow-2xs"
                >
                    <Trash2 size={13} />
                    Unlink
                </button>
                <button
                    onClick={handleSave}
                    type="button"
                    className="flex-[2] flex items-center justify-center gap-1.5 py-2.5 bg-blue-600 text-white rounded-xl text-xs font-bold hover:bg-blue-500 shadow-sm transition-all"
                >
                    <Save size={13} />
                    Persist Payload Specs
                </button>
            </div>
        </div>
    );
};
