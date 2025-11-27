# Quick Model Switch Guide

## Current Configuration
✅ **Model**: `openai/gpt-oss-20b` from OpenRouter  
✅ **Configured via**: Environment variables in `.env`

## How to Switch Models

### 1. Edit `.env` file:
```bash
# Change this line:
OPENROUTER_MODEL=openai/gpt-oss-20b

# To any of these popular options:
# OPENROUTER_MODEL=openai/gpt-4              # Most capable
# OPENROUTER_MODEL=openai/gpt-3.5-turbo     # Fast & economical
# OPENROUTER_MODEL=anthropic/claude-3.5-sonnet  # Latest Claude
# OPENROUTER_MODEL=meta-llama/llama-3.1-70b-instruct  # Open source
```

### 2. Restart the backend:
```bash
# Stop current process (Ctrl+C if running)
# Then restart:
python src/main.py
```

### 3. Test in Admin UI:
- Go to Testing Interface
- Start a session
- Send a test message
- Verify response quality

## Popular Model Options

| Model | Use Case | Speed | Cost |
|-------|----------|-------|------|
| `openai/gpt-oss-20b` | Development, testing | ⚡️ Fast | 💰 Low |
| `openai/gpt-3.5-turbo` | Production chatbots | ⚡️ Fast | 💰 Low |
| `openai/gpt-4` | Complex reasoning | 🐢 Slower | 💰💰💰 High |
| `anthropic/claude-3.5-sonnet` | Code, analysis | ⚡️ Fast | 💰💰 Medium |
| `anthropic/claude-3-haiku` | Simple tasks | ⚡️⚡️ Very Fast | 💰 Low |
| `meta-llama/llama-3.1-70b-instruct` | Open source | ⚡️ Fast | 💰 Low |

## Configuration Files

The model is set in 3 places (all updated):

1. **`.env`** - Environment variables (PRIMARY)
   ```bash
   OPENROUTER_MODEL=openai/gpt-oss-20b
   DEFAULT_LLM_MODEL=openai/gpt-oss-20b
   ```

2. **`configs/agents.json`** - Agent-specific models (OVERRIDE)
   ```json
   {
     "llm_config": {
       "model": "openai/gpt-oss-20b"
     }
   }
   ```

3. **`configs/api_providers.json`** - Provider defaults (FALLBACK)
   ```json
   {
     "models": [{
       "name": "openai/gpt-oss-20b",
       "default": true
     }]
   }
   ```

## Priority Order

The system uses models in this order:
1. Agent-specific model in `configs/agents.json` (if set)
2. `OPENROUTER_MODEL` environment variable
3. `DEFAULT_LLM_MODEL` environment variable
4. Default model in `configs/api_providers.json`

## Troubleshooting

**Problem**: Model not found error  
**Solution**: Verify model name at https://openrouter.ai/models

**Problem**: Slow responses  
**Solution**: Switch to `gpt-oss-20b` or `gpt-3.5-turbo`

**Problem**: Poor quality responses  
**Solution**: Try `gpt-4` or `claude-3.5-sonnet`

**Problem**: High costs  
**Solution**: Use `gpt-oss-20b` for dev, `gpt-3.5-turbo` for prod

## Full Documentation

See `docs/MODEL_CONFIGURATION.md` for complete guide.
