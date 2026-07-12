import { memo, useState } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { Node, NodeProps } from '@xyflow/react';
import type { LucideIcon } from 'lucide-react';
import { Play, MessageSquare, Link, Loader2, Check, X } from 'lucide-react';
import { useShallow } from 'zustand/react/shallow';
import type { WorkflowNodeData } from '../../types/workflow';
import { useWorkflowStore } from '../../stores/workflowStore';
import { api } from '../../api/client';
import { NODE_TONE, triggerToneForType } from '../../utils/nodeTheme';

const ICON_FOR_TRIGGER_TYPE: Record<string, LucideIcon> = {
    chat: MessageSquare,
    webhook: Link,
    manual: Play,
};

export const TriggerNode = memo(({ id, data, selected }: NodeProps<Node<WorkflowNodeData>>) => {
    const config = data.config as any;
    const triggerType = config?.trigger_type || 'manual';
    const tone = NODE_TONE[triggerToneForType(triggerType)];
    const Icon = ICON_FOR_TRIGGER_TYPE[triggerType] ?? Play;

    // Selector-scoped: this node only re-renders when these specific fields change,
    // not on every node/edge update elsewhere on the canvas.
    const { currentWorkflowId, setExecutingTrigger, executingTriggerId, triggerResult } = useWorkflowStore(
        useShallow((state) => ({
            currentWorkflowId: state.currentWorkflowId,
            setExecutingTrigger: state.setExecutingTrigger,
            executingTriggerId: state.executingTriggerId,
            triggerResult: state.triggerResult,
        })),
    );
    const [localStatus, setLocalStatus] = useState<'idle' | 'running' | 'success' | 'error'>('idle');

    const isExecuting = executingTriggerId === id || localStatus === 'running';
    const showSuccess = (executingTriggerId === id && triggerResult === 'success') || localStatus === 'success';
    const showError = (executingTriggerId === id && triggerResult === 'error') || localStatus === 'error';

    const handleRun = async (e: React.MouseEvent) => {
        e.stopPropagation();

        // Use configured workflow_id or fall back to current canvas workflow
        const targetWorkflowId = config?.workflow_id || currentWorkflowId;

        if (!targetWorkflowId) {
            alert('No workflow loaded. Please load a workflow from the sidebar first.');
            return;
        }

        setLocalStatus('running');
        setExecutingTrigger(id, null);

        try {
            // Create a session and send a test message
            const sessionData = await api<{ session_id: string }>('/api/v1/sessions', {
                method: 'POST',
                body: JSON.stringify({
                    workflow_id: targetWorkflowId,
                    user_id: 'trigger-test-user',
                    metadata: { source: 'trigger_node', trigger_type: config?.trigger_type || 'manual' }
                }),
            });
            const sessionId = sessionData.session_id;

            // Send a test message to trigger the workflow
            const result = await api(`/api/v1/sessions/${sessionId}/messages`, {
                method: 'POST',
                body: JSON.stringify({
                    message: config?.trigger_type === 'chat'
                        ? 'Hello, trigger test!'
                        : '{"trigger": "manual", "source": "workflow_editor"}',
                    max_turns: 10,
                    metadata: { triggered_from: 'canvas' }
                }),
            });
            console.log('Trigger execution result:', result);

            setLocalStatus('success');
            setExecutingTrigger(id, 'success');

            // Reset after 3 seconds
            setTimeout(() => {
                setLocalStatus('idle');
                setExecutingTrigger(null, null);
            }, 3000);

        } catch (err) {
            console.error('Trigger execution error:', err);
            setLocalStatus('error');
            setExecutingTrigger(id, 'error');

            // Reset after 3 seconds
            setTimeout(() => {
                setLocalStatus('idle');
                setExecutingTrigger(null, null);
            }, 3000);
        }
    };

    return (
        // `group` lives on the outer wrapper (not the inner circle) so the run button —
        // a sibling of the circle, not a descendant — actually receives group-hover.
        <div className="group relative flex flex-col items-center justify-center">
            <div
                className={`flex items-center justify-center w-14 h-14 ag-surface-raised rounded-full border-2 shadow-sm transition-all duration-200
                ${selected
                        ? `${tone.handleBorder} ${tone.ring}`
                        : `${tone.border} ${tone.borderHover} hover:shadow-md`
                    }
                ${showSuccess ? 'ring-4 ring-emerald-400/50 dark:ring-emerald-400/40' : ''}
                ${showError ? 'ring-4 ring-red-400/50 dark:ring-red-400/40' : ''}
                `}
            >
                <div className={`flex items-center justify-center w-10 h-10 rounded-full ${tone.iconBg} ${tone.iconText} transition-transform group-hover:scale-110`}>
                    {isExecuting ? (
                        <Loader2 size={20} className="animate-spin" />
                    ) : showSuccess ? (
                        <Check size={20} className="text-emerald-600 dark:text-emerald-400" />
                    ) : showError ? (
                        <X size={20} className="text-red-600 dark:text-red-400" />
                    ) : (
                        <Icon size={20} fill="currentColor" className="ml-0.5" />
                    )}
                </div>

                {/* Output Handle (Right) */}
                <Handle
                    type="source"
                    position={Position.Right}
                    className={`!w-3 !h-3 !-right-[7px] !bg-[var(--color-surface-raised)] !border-[3px] ${tone.handleBorder} ${tone.handleHover} transition-colors z-10`}
                />
            </div>

            {/* Run Button - Shows on hover */}
            <button
                onClick={handleRun}
                disabled={isExecuting}
                className={`absolute -bottom-1 -right-1 w-6 h-6 rounded-full ${tone.actionBg} text-white shadow-lg
                    flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-200
                    hover:scale-110 disabled:opacity-50 disabled:cursor-not-allowed z-20
                    ${isExecuting || showSuccess || showError ? 'opacity-100' : ''}`}
                title="Run Trigger"
            >
                {isExecuting ? (
                    <Loader2 size={12} className="animate-spin" />
                ) : showSuccess ? (
                    <Check size={12} />
                ) : showError ? (
                    <X size={12} />
                ) : (
                    <Play size={12} fill="currentColor" />
                )}
            </button>

            {/* External Label */}
            <div className="absolute -bottom-6 flex flex-col items-center w-32">
                <span className="text-xs font-bold ag-label px-2 py-0.5 rounded-full shadow-sm backdrop-blur-sm">
                    {data.label || 'Start'}
                </span>
            </div>
        </div>
    );
});
