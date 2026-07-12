import { describe, expect, it } from 'vitest';
import { itemToAgentCreate } from './libraryStore';

describe('itemToAgentCreate', () => {
    it('maps a blank canvas agent to a valid backend payload', () => {
        // Mirrors the palette "CrewAI Agent" node dragged onto the canvas.
        const payload = itemToAgentCreate({
            name: 'CrewAI Agent',
            config: { id: 'crewai_agent', type: 'LlmAgent', role: '', goal: '', tools: [] },
        });
        expect(payload.id).toBe('crewai_agent');
        // 'LlmAgent' is not a backend enum → coerced to conversable
        expect(payload.type).toBe('conversable');
        // empty model config → null, not {} (which fails backend validation)
        expect(payload.llm_config).toBeNull();
        expect(payload.name).toBe('CrewAI_Agent');
    });

    it('keeps a valid backend type and a real model config', () => {
        const payload = itemToAgentCreate({
            name: 'Assistant',
            config: {
                type: 'assistant',
                model_config: { provider_id: 'openrouter', model: 'openai/gpt-4o-mini', temperature: 0.5 },
            },
        });
        expect(payload.type).toBe('assistant');
        expect(payload.llm_config).toEqual({ provider_id: 'openrouter', model: 'openai/gpt-4o-mini', temperature: 0.5 });
    });

    it('sends null when a model config lacks provider or model', () => {
        const payload = itemToAgentCreate({
            name: 'Half',
            config: { type: 'conversable', model_config: { provider_id: 'openrouter' } },
        });
        expect(payload.llm_config).toBeNull();
    });
});
