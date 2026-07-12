import { describe, expect, it } from 'vitest';
import type { Connection } from '@xyflow/react';
import type { VisualNode } from '../types/workflow';
import { auxKindForToolType, isAuxHandle, isValidConnection } from './connectionRules';

const node = (id: string, type: VisualNode['type'], toolType?: string): VisualNode => ({
    id,
    type,
    position: { x: 0, y: 0 },
    data: { label: id, config: toolType ? { type: toolType } : {} },
});

const nodes: VisualNode[] = [
    node('agent-1', 'agent'),
    node('memory-1', 'tool', 'memory'),
    node('knowledge-1', 'tool', 'knowledge'),
    node('mcp-1', 'tool', 'mcp'),
    node('gmail-1', 'tool', 'gmail'),
    node('trigger-1', 'trigger'),
];

const connect = (source: string, targetHandle: string | null): Connection => ({
    source,
    target: 'agent-1',
    sourceHandle: 'attach',
    targetHandle,
});

describe('isAuxHandle', () => {
    it('recognizes only the three aux handle ids', () => {
        expect(isAuxHandle('tools')).toBe(true);
        expect(isAuxHandle('memory')).toBe(true);
        expect(isAuxHandle('knowledge')).toBe(true);
        expect(isAuxHandle(null)).toBe(false);
        expect(isAuxHandle('right')).toBe(false);
    });
});

describe('auxKindForToolType', () => {
    it('maps memory and knowledge to their handles, everything else to tools', () => {
        expect(auxKindForToolType('memory')).toBe('memory');
        expect(auxKindForToolType('knowledge')).toBe('knowledge');
        expect(auxKindForToolType('mcp')).toBe('tools');
        expect(auxKindForToolType('gmail')).toBe('tools');
        expect(auxKindForToolType(undefined)).toBe('tools');
    });
});

describe('isValidConnection', () => {
    it('allows matching tool kinds on their aux handle', () => {
        expect(isValidConnection(connect('memory-1', 'memory'), nodes)).toBe(true);
        expect(isValidConnection(connect('knowledge-1', 'knowledge'), nodes)).toBe(true);
        expect(isValidConnection(connect('mcp-1', 'tools'), nodes)).toBe(true);
        expect(isValidConnection(connect('gmail-1', 'tools'), nodes)).toBe(true);
    });

    it('rejects mismatched tool kinds on aux handles', () => {
        expect(isValidConnection(connect('memory-1', 'tools'), nodes)).toBe(false);
        expect(isValidConnection(connect('memory-1', 'knowledge'), nodes)).toBe(false);
        expect(isValidConnection(connect('mcp-1', 'memory'), nodes)).toBe(false);
        expect(isValidConnection(connect('knowledge-1', 'tools'), nodes)).toBe(false);
    });

    it('rejects non-tool sources on aux handles', () => {
        expect(isValidConnection(connect('trigger-1', 'tools'), nodes)).toBe(false);
    });

    it('rejects aux connections into non-agent targets', () => {
        const conn: Connection = { source: 'memory-1', target: 'mcp-1', sourceHandle: 'attach', targetHandle: 'memory' };
        expect(isValidConnection(conn, nodes)).toBe(false);
    });

    it('never lets an attach-handle drag become a flow edge', () => {
        const conn: Connection = { source: 'memory-1', target: 'agent-1', sourceHandle: 'attach', targetHandle: null };
        expect(isValidConnection(conn, nodes)).toBe(false);
    });

    it('leaves flow connections unrestricted', () => {
        const flow: Connection = { source: 'trigger-1', target: 'agent-1', sourceHandle: null, targetHandle: null };
        expect(isValidConnection(flow, nodes)).toBe(true);
        const routerFlow: Connection = { source: 'agent-1', target: 'mcp-1', sourceHandle: 'right', targetHandle: null };
        expect(isValidConnection(routerFlow, nodes)).toBe(true);
    });
});
