# Model Configuration Guide

This guide explains how to configure and switch between different LLM models in the orchestration service.

## Quick Start: Using GPT-OSS-20B from OpenRouter

The system is now configured to use `openai/gpt-oss-20b` from OpenRouter by default. This model is:
- Fast and efficient
- Cost-effective
- Good for general-purpose tasks

### Environment Variables

The model can be configured using environment variables in your `.env` file:

```bash
# OpenRouter Configuration
OPENROUTER_API_KEY=your_api_key_here
OPENROUTER_MODEL=openai/gpt-oss-20b
DEFAULT_LLM_MODEL=openai/gpt-oss-20b
DEFAULT_LLM_PROVIDER=openrouter
```

## Switching Models

### Method 1: Environment Variables (Recommended)

1. Edit your `.env` file:
```bash
# For GPT-OSS-20B (default, fast, economical)
OPENROUTER_MODEL=openai/gpt-oss-20b

# For GPT-4 (more capable, more expensive)
OPENROUTER_MODEL=openai/gpt-4

# For GPT-4 Turbo
OPENROUTER_MODEL=openai/gpt-4-turbo

# For Claude 3.5 Sonnet
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet

# For Claude 3 Opus
OPENROUTER_MODEL=anthropic/claude-3-opus

# For Llama 3.1 70B
OPENROUTER_MODEL=meta-llama/llama-3.1-70b-instruct
```

2. Restart the backend service:
```bash
# In terminal with virtual environment activated
python src/main.py
```

### Method 2: Update Agent Configurations

Edit `configs/agents.json` to change the model for specific agents:

```json
{
  "id": "reasoning_agent",
  "llm_config": {
    "provider_id": "openrouter",
    "model": "openai/gpt-oss-20b",  // Change this
    "temperature": 0.7,
    "max_tokens": 500
  }
}
```

### Method 3: Update Provider Configuration

Edit `configs/api_providers.json` to change the default model:

```json
{
  "id": "openrouter",
  "models": [
    {
      "name": "openai/gpt-oss-20b",
      "default": true,  // Set this to true for your preferred model
      "capabilities": ["chat", "reasoning"]
    }
  ]
}
```

## Available Models on OpenRouter

### OpenAI Models
- `openai/gpt-oss-20b` - Fast, efficient, economical (current default)
- `openai/gpt-4` - Most capable OpenAI model
- `openai/gpt-4-turbo` - Faster GPT-4 with larger context
- `openai/gpt-3.5-turbo` - Fast and economical

### Anthropic Models
- `anthropic/claude-3.5-sonnet` - Latest Claude model
- `anthropic/claude-3-opus` - Most capable Claude model
- `anthropic/claude-3-sonnet` - Balanced performance
- `anthropic/claude-3-haiku` - Fast and economical

### Meta Llama Models
- `meta-llama/llama-3.1-405b-instruct` - Largest Llama model
- `meta-llama/llama-3.1-70b-instruct` - Balanced
- `meta-llama/llama-3.1-8b-instruct` - Fast and economical

### Google Models
- `google/gemini-pro-1.5` - Latest Gemini model
- `google/gemini-flash-1.5` - Fast variant

### Mistral Models
- `mistralai/mixtral-8x22b-instruct` - MoE model
- `mistralai/mistral-large` - Most capable

## Configuration Priority

The system uses this priority order for model selection:

1. **Agent-specific model** in `configs/agents.json`
2. **Environment variable** `OPENROUTER_MODEL` or `DEFAULT_LLM_MODEL`
3. **Default model** marked in `configs/api_providers.json`
4. **Fallback** to `openai/gpt-oss-20b`

## Testing Your Configuration

After changing the model, test it using the Admin UI:

1. Navigate to **Testing Interface** in Admin UI
2. Select a workflow (e.g., "Simple Assistant")
3. Start a session and send a test message
4. Verify the response comes from the expected model

## Cost Optimization Tips

1. **Use GPT-OSS-20B for development**: Fast and very economical
2. **Use GPT-3.5-Turbo for production**: Good balance of cost/performance
3. **Reserve GPT-4/Claude for complex tasks**: Use in specialized agents only
4. **Set appropriate max_tokens**: Limit response length to control costs
5. **Enable caching**: Set `cache_seed` in llm_config

## Model-Specific Configuration

Different models may require different parameters:

```json
{
  "llm_config": {
    "provider_id": "openrouter",
    "model": "openai/gpt-oss-20b",
    "temperature": 0.7,      // Creativity: 0.0-2.0
    "max_tokens": 500,       // Response length limit
    "cache_seed": 42,        // Enable response caching
    "timeout": 120           // Request timeout in seconds
  }
}
```

### Recommended Settings by Use Case

**Fast Responses (Chatbots):**
```json
{
  "model": "openai/gpt-oss-20b",
  "temperature": 0.7,
  "max_tokens": 500
}
```

**Code Generation:**
```json
{
  "model": "anthropic/claude-3.5-sonnet",
  "temperature": 0.3,
  "max_tokens": 2000
}
```

**Creative Writing:**
```json
{
  "model": "openai/gpt-4",
  "temperature": 1.0,
  "max_tokens": 2000
}
```

**Reasoning/Analysis:**
```json
{
  "model": "anthropic/claude-3-opus",
  "temperature": 0.5,
  "max_tokens": 1000
}
```

## Troubleshooting

### Model Not Found Error
- Verify the model name is correct (check OpenRouter docs)
- Ensure OpenRouter API key is set in `.env`
- Check model availability in your OpenRouter account

### Slow Responses
- Try a faster model like `gpt-oss-20b` or `gpt-3.5-turbo`
- Reduce `max_tokens` to limit response length
- Check network connectivity to OpenRouter

### High Costs
- Switch to more economical models for non-critical agents
- Set lower `max_tokens` limits
- Enable caching with `cache_seed`
- Monitor usage in OpenRouter dashboard

## Environment Variable Reference

```bash
# Primary model configuration
OPENROUTER_MODEL=openai/gpt-oss-20b         # Model to use
DEFAULT_LLM_MODEL=openai/gpt-oss-20b        # Fallback if agent config doesn't specify
DEFAULT_LLM_PROVIDER=openrouter              # Provider to use

# Provider settings
OPENROUTER_API_KEY=your_key_here            # Required
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1  # Optional, has default

# Performance tuning
DEFAULT_TEMPERATURE=0.7                      # Default creativity level
DEFAULT_MAX_TOKENS=500                       # Default response length
LLM_REQUEST_TIMEOUT=120                      # Request timeout in seconds
```

## Next Steps

1. **Set up your API key**: Add `OPENROUTER_API_KEY` to `.env`
2. **Choose your model**: Set `OPENROUTER_MODEL` to your preferred model
3. **Test the configuration**: Use the Testing Interface in Admin UI
4. **Optimize per agent**: Customize models for specific agents if needed
5. **Monitor costs**: Track usage in OpenRouter dashboard

For more information, visit:
- [OpenRouter Models](https://openrouter.ai/models)
- [API Documentation](https://openrouter.ai/docs)
