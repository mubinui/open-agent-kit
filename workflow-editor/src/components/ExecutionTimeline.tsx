import { useState } from 'react';
import { Activity, AlertTriangle, CheckCircle2, Circle, RotateCcw, X } from 'lucide-react';
import { useShallow } from 'zustand/react/shallow';
import { API_BASE_URL } from '../api/client';
import { useWorkflowStore } from '../stores/workflowStore';

const readSse = async (
    response: Response,
    onEvent: (event: Record<string, any>) => void,
) => {
    if (!response.body) throw new Error('No stream body returned');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split('\n\n');
        buffer = frames.pop() ?? '';
        for (const frame of frames) {
            const dataLine = frame.split('\n').find((line) => line.startsWith('data: '));
            if (!dataLine) continue;
            const raw = dataLine.slice(6);
            if (raw === '[DONE]') continue;
            onEvent(JSON.parse(raw));
        }
    }
};

export const ExecutionTimeline = () => {
    const [isOpen, setIsOpen] = useState(false);
    const {
        currentWorkflowId,
        executionTimeline,
        liveRunActive,
        liveResponse,
        resetExecution,
        applyExecutionEvent,
    } = useWorkflowStore(
        useShallow((state) => ({
            currentWorkflowId: state.currentWorkflowId,
            executionTimeline: state.executionTimeline,
            liveRunActive: state.liveRunActive,
            liveResponse: state.liveResponse,
            resetExecution: state.resetExecution,
            applyExecutionEvent: state.applyExecutionEvent,
        })),
    );

    const runLive = async () => {
        if (!currentWorkflowId) {
            alert('Save or load a workflow before running live.');
            return;
        }
        const message = prompt('Live run input:', 'Hello');
        if (!message) return;
        resetExecution();
        try {
            const response = await fetch(`${API_BASE_URL}/api/v1/workflows/${currentWorkflowId}/execute/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, metadata: { source: 'canvas_live_run' }, timeout_seconds: 120 }),
            });
            if (!response.ok) throw new Error(await response.text());
            await readSse(response, applyExecutionEvent);
        } catch (error) {
            applyExecutionEvent({
                type: 'error',
                payload: { error_message: (error as Error).message },
                timestamp: new Date().toISOString(),
            });
        }
    };

    const iconFor = (status: string) => {
        if (status === 'running') return <Activity size={14} className="text-blue-500 animate-pulse" />;
        if (status === 'success') return <CheckCircle2 size={14} className="text-emerald-500" />;
        if (status === 'error') return <AlertTriangle size={14} className="text-red-500" />;
        return <Circle size={14} className="ag-faint" />;
    };

    if (!isOpen) {
        return (
            <button
                onClick={() => setIsOpen(true)}
                className="group absolute left-16 bottom-5 z-40 flex items-center gap-2 h-11 px-4 ag-surface-raised border rounded-full shadow-lg hover:shadow-xl transition-all"
                title="Execution timeline"
            >
                <Activity size={16} className={liveRunActive ? 'text-blue-500 animate-pulse' : 'ag-muted'} />
                <span className="text-xs font-semibold ag-text-secondary">Timeline</span>
                {executionTimeline.length > 0 && (
                    <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-primary)] px-1 text-[9px] font-bold text-white">
                        {executionTimeline.length}
                    </span>
                )}
            </button>
        );
    }

    return (
        <div className="absolute left-16 bottom-5 z-40 w-[360px] max-h-[46vh] ag-surface-raised border rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in slide-in-from-bottom-2 duration-150">
            <div className="px-4 py-3 ag-surface-subtle border-b border-[var(--color-ui-border)] flex items-center justify-between shrink-0">
                <div className="min-w-0">
                    <div className="text-sm font-bold ag-text">Live Execution</div>
                    <div className="text-xs ag-muted truncate">{liveRunActive ? 'Running workflow…' : 'Agent and tool sequence'}</div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                    <button onClick={resetExecution} className="p-2 ag-muted hover:bg-black/5 dark:hover:bg-white/10 rounded-lg transition-colors" title="Reset">
                        <RotateCcw size={14} />
                    </button>
                    <button
                        onClick={runLive}
                        disabled={liveRunActive}
                        className="px-3 py-1.5 bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)] text-white rounded-lg text-xs font-semibold disabled:opacity-50 transition-colors"
                    >
                        Run Live
                    </button>
                    <button onClick={() => setIsOpen(false)} className="p-2 ag-muted hover:bg-black/5 dark:hover:bg-white/10 rounded-lg transition-colors" title="Close">
                        <X size={14} />
                    </button>
                </div>
            </div>
            <div className="overflow-y-auto p-3 space-y-2 min-h-0">
                {executionTimeline.length === 0 ? (
                    <div className="text-xs ag-muted p-3 ag-surface-subtle rounded-lg">Run a workflow to see every agent transfer and tool call in order.</div>
                ) : (
                    executionTimeline.map((item) => (
                        <div key={item.id} className="flex gap-2 p-2 rounded-lg border ag-surface">
                            <div className="pt-0.5">{iconFor(item.status)}</div>
                            <div className="min-w-0 flex-1">
                                <div className="text-xs font-semibold ag-text truncate">{item.label}</div>
                                <div className="text-[10px] ag-muted">{new Date(item.timestamp).toLocaleTimeString()}</div>
                                {(item.type.includes('tool') || item.type === 'error' || item.type === 'node_input' || item.type === 'node_output') && (
                                    <pre className="mt-2 text-[10px] bg-slate-950 text-slate-100 p-2 rounded overflow-auto max-h-28">{JSON.stringify(item.payload, null, 2)}</pre>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>
            {liveResponse && (
                <div className="border-t border-[var(--color-ui-border)] p-3 ag-surface-subtle shrink-0">
                    <div className="text-[10px] font-bold uppercase ag-faint mb-1">Response</div>
                    <div className="text-xs ag-text-secondary max-h-24 overflow-y-auto whitespace-pre-wrap">{liveResponse}</div>
                </div>
            )}
        </div>
    );
};
