import React, { useState, useCallback, useRef } from 'react';
import { Plus, Layout, Save, Download, Upload, Copy, Check, ShieldCheck, Play, Moon, Sun, Home, Zap, Rocket } from 'lucide-react';
import { useReactFlow } from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import dagre from 'dagre';
import { useWorkflowStore } from '../stores/workflowStore';
import { useLibraryStore } from '../stores/libraryStore';
import { buildWorkflowPayload } from '../utils/workflowPayload';
import { OakLogo } from './OakLogo';
import { useTheme } from '../hooks/useTheme';

// --- DAGRE LAYOUT LOGIC ---
const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
    dagreGraph.setGraph({ rankdir: 'LR' });

    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, { width: 250, height: 100 });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    const layoutedNodes = nodes.map((node) => {
        const nodeWithPosition = dagreGraph.node(node.id);
        return {
            ...node,
            position: {
                x: nodeWithPosition.x - 125,
                y: nodeWithPosition.y - 50,
            },
        };
    });

    return { nodes: layoutedNodes, edges };
};

const isSelectorTopology = (topology: any) => (
    Boolean(topology?.entry_node)
    && Array.isArray(topology?.domain_agents)
    && topology.domain_agents.length > 0
);

const buildSelectorEdges = (topology: any) => {
    if (!topology?.entry_node) {
        return [];
    }

    const targetIds = Array.isArray(topology.domain_agents) && topology.domain_agents.length > 0
        ? topology.domain_agents.map((agent: any) => agent.id)
        : (topology.nodes ?? [])
            .map((node: any) => node.id)
            .filter((nodeId: string) => nodeId !== topology.entry_node);

    return targetIds
        .filter((targetId: string) => targetId && targetId !== topology.entry_node)
        .map((targetId: string, index: number) => ({
            id: `selector-edge-${index}`,
            source: topology.entry_node,
            target: targetId,
            type: 'smoothstep',
        }));
};

interface HeaderProps {
    onOpenLanding?: () => void;
    onOpenTester?: () => void;
    onOpenDeploy?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenLanding, onOpenTester, onOpenDeploy }) => {
    const { nodes, edges, setNodes, setEdges, onNodesChange, currentWorkflowId, workflowName, setWorkflowName, setCurrentWorkflow, loadWorkflow } = useWorkflowStore();
    const { savedWorkflows, saveWorkflow, validateWorkflow, executeWorkflow, isLoading, fetchLibraryItems } = useLibraryStore();
    const { fitView } = useReactFlow();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [copied, setCopied] = useState(false);
    const { isDark, toggleTheme } = useTheme();

    const handleNew = () => {
        if (confirm("Are you sure you want to create a new workflow? Unsaved changes will be lost.")) {
            setNodes([]);
            setEdges([]);
            setWorkflowName('Untitled Workflow');
            setCurrentWorkflow(null);
        }
    };

    const handleLayout = useCallback(() => {
        const { nodes: layoutedNodes } = getLayoutedElements(nodes, edges);
        const changes = layoutedNodes.map((node) => ({
            id: node.id,
            type: 'position',
            position: node.position
        }));
        // @ts-ignore
        onNodesChange(changes);
        setTimeout(() => fitView({ padding: 0.2, duration: 800 }), 100);
    }, [nodes, edges, onNodesChange, fitView]);

    const handleSave = async () => {
        if (!nodes.length) {
            alert("Cannot save an empty workflow.");
            return;
        }

        const payload = buildWorkflowPayload({
            id: currentWorkflowId,
            name: workflowName,
            nodes,
            edges,
        });

        try {
            const saved = await saveWorkflow({ ...payload, currentId: currentWorkflowId });
            setCurrentWorkflow(saved.id, saved.name);
            alert("Workflow saved to backend successfully.");
        } catch (e) {
            alert("Failed to save workflow: " + (e as Error).message);
        }
    };

    const handleLoadWorkflow = async (workflowId: string) => {
        if (!workflowId) return;
        const workflow = savedWorkflows.find((item) => item.id === workflowId);
        if (!workflow) return;

        const topology = workflow.config?.topology ?? {};
        const selectorTopology = isSelectorTopology(topology);
        const visualCanvas = workflow.config?.metadata?.visual_canvas ?? workflow.config;
        const hasVisualCanvas = Array.isArray(visualCanvas.nodes) && visualCanvas.nodes.some((node: any) => node.data);
        const baseWorkflowNodes = hasVisualCanvas
            ? visualCanvas.nodes
            : (topology.nodes ?? []).map((node: any, index: number) => ({
                id: node.id,
                type: 'agent',
                position: node.position ?? { x: 120 + index * 260, y: 180 },
                data: {
                    label: node.agent_id ?? node.id,
                    description: node.description ?? '',
                    config: {
                        id: node.agent_id ?? node.id,
                        agent_id: node.agent_id ?? node.id,
                        is_selector: selectorTopology && node.id === topology.entry_node,
                        ...(node.config ?? {}),
                    },
                },
            }));
        const workflowNodes = selectorTopology
            ? baseWorkflowNodes.map((node: any) => {
                if (node.id !== topology.entry_node) {
                    return node;
                }
                return {
                    ...node,
                    data: {
                        ...node.data,
                        config: {
                            ...(node.data?.config ?? {}),
                            is_selector: true,
                        },
                    },
                };
            })
            : baseWorkflowNodes;
        const topologyEdges = (topology.edges ?? []).map((edge: any, index: number) => ({
                id: edge.id ?? `edge-${index}`,
                source: edge.source ?? edge.from_node,
                target: edge.target ?? edge.to_node,
                type: 'smoothstep',
            }));
        const workflowEdges = Array.isArray(visualCanvas.edges) && visualCanvas.edges.length > 0
            ? visualCanvas.edges
            : topologyEdges.length > 0
                ? topologyEdges
                : selectorTopology
                    ? buildSelectorEdges(topology)
                    : [];

        loadWorkflow(workflow.id, workflow.name, workflowNodes, workflowEdges);
        setTimeout(() => fitView({ padding: 0.2, duration: 500 }), 100);
    };

    const handleValidate = async () => {
        if (!currentWorkflowId) {
            alert('Save or load a workflow before validating.');
            return;
        }
        try {
            const result = await validateWorkflow(currentWorkflowId);
            alert(result.valid ? 'Workflow validation passed.' : `Workflow validation failed:\n${JSON.stringify(result.errors, null, 2)}`);
        } catch (e) {
            alert('Validation failed: ' + (e as Error).message);
        }
    };

    const handleExecute = async () => {
        if (!currentWorkflowId) {
            alert('Save or load a workflow before executing.');
            return;
        }
        const message = prompt('Input message for this workflow:', 'Hello');
        if (!message) return;
        try {
            const result = await executeWorkflow(currentWorkflowId, message);
            alert(JSON.stringify(result, null, 2));
        } catch (e) {
            alert('Execution failed: ' + (e as Error).message);
        }
    };

    // --- EXPORT: Download workflow as JSON ---
    const handleExport = () => {
        if (!nodes.length) {
            alert("Nothing to export - canvas is empty.");
            return;
        }

        const workflow = {
            name: workflowName,
            version: '1.0',
            exportedAt: new Date().toISOString(),
            nodes,
            edges,
        };

        const blob = new Blob([JSON.stringify(workflow, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${workflowName.replace(/\s+/g, '_')}.workflow.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    // --- IMPORT: Upload workflow from JSON ---
    const handleImport = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const content = e.target?.result as string;
                const workflow = JSON.parse(content);

                if (!workflow.nodes || !Array.isArray(workflow.nodes)) {
                    throw new Error('Invalid workflow file: missing nodes array');
                }

                const name = workflow.name || 'Imported Workflow';
                loadWorkflow(
                    workflow.id || `imported_${Date.now()}`,
                    name,
                    workflow.nodes,
                    workflow.edges || []
                );

                setTimeout(() => fitView({ padding: 0.2, duration: 500 }), 100);
                alert(`Workflow "${name}" imported successfully!`);
            } catch (err) {
                alert('Failed to import workflow: ' + (err as Error).message);
            }
        };
        reader.readAsText(file);

        // Reset input so same file can be imported again
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    // --- COPY: Copy workflow JSON to clipboard ---
    const handleCopy = async () => {
        if (!nodes.length) {
            alert("Nothing to copy - canvas is empty.");
            return;
        }

        const workflow = {
            name: workflowName,
            version: '1.0',
            nodes,
            edges,
        };

        try {
            await navigator.clipboard.writeText(JSON.stringify(workflow, null, 2));
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            alert('Failed to copy to clipboard');
        }
    };

    return (
        <header className="h-14 bg-white dark:bg-[#0b111b] border-b border-[var(--color-ui-border)] flex items-center justify-between px-4 z-20 shadow-sm transition-colors">
            <div className="flex items-center gap-3">
                <OakLogo className="w-8 h-8 rounded-lg shadow-sm" />
                <div className="flex flex-col">
                    <div className="flex items-baseline gap-1.5">
                        <span className="brand-lockup-title">Open Agent Kit</span>
                        <span className="brand-lockup-tagline">Agent Studio</span>
                    </div>
                    <input
                        className="text-sm font-semibold text-gray-900 dark:text-white bg-transparent border-none p-0 focus:ring-0 w-48 hover:bg-gray-50 dark:hover:bg-slate-800/50 rounded px-1 -ml-1 transition-colors"
                        value={workflowName}
                        onChange={(e) => setWorkflowName(e.target.value)}
                    />
                </div>
            </div>

            <div className="flex items-center gap-2">
                {/* Navigation Views Switchers */}
                {onOpenLanding && (
                    <button
                        onClick={onOpenLanding}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-bold text-blue-600 dark:text-sky-400 hover:bg-blue-50 dark:hover:bg-slate-800 rounded-md transition-colors"
                        title="Return to Welcome Hub"
                    >
                        <Home size={14} />
                        <span className="hidden md:inline">Hub</span>
                    </button>
                )}
                {onOpenTester && (
                    <button
                        onClick={onOpenTester}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-bold text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-slate-800 rounded-md transition-colors"
                        title="Launch Live LLM Tester Sandbox"
                    >
                        <Zap size={14} />
                        <span className="hidden md:inline">Live API</span>
                    </button>
                )}
                {onOpenDeploy && (
                    <button
                        onClick={onOpenDeploy}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-bold text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-slate-800 rounded-md transition-colors"
                        title="Open Production Deploy Hub"
                    >
                        <Rocket size={14} />
                        <span className="hidden md:inline">Deploy</span>
                    </button>
                )}

                <div className="w-px h-5 bg-gray-200 dark:bg-slate-800 mx-1"></div>

                {/* Export/Import/Copy */}
                <button
                    onClick={handleExport}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors"
                    title="Download workflow as JSON"
                >
                    <Download size={14} />
                </button>

                <button
                    onClick={() => fileInputRef.current?.click()}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors"
                    title="Import workflow from JSON"
                >
                    <Upload size={14} />
                </button>
                <input
                    ref={fileInputRef}
                    type="file"
                    accept=".json,.workflow.json"
                    onChange={handleImport}
                    className="hidden"
                />

                <button
                    onClick={handleCopy}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors"
                    title="Copy workflow to clipboard"
                >
                    {copied ? <Check size={14} className="text-green-600 dark:text-emerald-400" /> : <Copy size={14} />}
                </button>

                <div className="w-px h-5 bg-gray-200 dark:bg-slate-800 mx-1"></div>

                <button
                    onClick={handleLayout}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors"
                    title="Auto Format"
                >
                    <Layout size={14} />
                    Format
                </button>

                <div className="w-px h-5 bg-gray-200 dark:bg-slate-800 mx-1"></div>

                <select
                    onFocus={() => fetchLibraryItems()}
                    onChange={(event) => handleLoadWorkflow(event.target.value)}
                    value=""
                    className="max-w-44 px-2 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-md transition-colors"
                    title="Load workflow from backend"
                >
                    <option value="">Load workflow...</option>
                    {savedWorkflows.map((workflow) => (
                        <option key={workflow.id} value={workflow.id}>{workflow.name}</option>
                    ))}
                </select>

                <button
                    onClick={handleValidate}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors"
                    title="Validate saved workflow"
                >
                    <ShieldCheck size={14} />
                    Validate
                </button>

                <button
                    onClick={handleExecute}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors"
                    title="Execute saved workflow"
                >
                    <Play size={14} />
                    Execute
                </button>

                <div className="w-px h-5 bg-gray-200 dark:bg-slate-800 mx-1"></div>

                <button
                    onClick={toggleTheme}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors"
                    title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
                >
                    {isDark ? <Sun size={14} /> : <Moon size={14} />}
                    {isDark ? 'Light' : 'Dark'}
                </button>

                <div className="w-px h-5 bg-gray-200 dark:bg-slate-800 mx-1"></div>

                <button
                    onClick={handleNew}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 rounded-md transition-colors"
                >
                    <Plus size={14} />
                    New
                </button>

                <button
                    onClick={handleSave}
                    disabled={isLoading}
                    className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md shadow-sm transition-all disabled:opacity-70 disabled:cursor-not-allowed"
                >
                    <Save size={14} />
                    {isLoading ? 'Saving...' : 'Save'}
                </button>
            </div>
        </header>
    );
};
