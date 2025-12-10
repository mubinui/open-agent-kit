# Agent Behavior Configuration Guide

## Overview

Agent behavior configuration allows you to define how agents should behave, what output formats they should produce, what constraints they must follow, and how their outputs should be validated. This guide explains how to configure agent behaviors for reliable, production-ready workflows.

## Why Configure Agent Behavior?

### Without Behavior Configuration

```
Agent → LLM → Unpredictable Output
- Format varies
- No validation
- Inconsistent results
- Hard to debug
```

### With Behavior Configuration

```
Agent → LLM → Validation → Structured Output
- Consistent format
- Validated output
- Reliable results
- Easy to debug
```

## Behavior Configuration Structure

### Complete Example

```json
{
  "id": "structured_agent",
  "type": "conversable",
  "system_message": "You are a data analyzer...",
  "behavior": {
    "output_format": {
      "type": "json",
      "schema": {...}
    },
    "constraints": {
      "max_output_length": 5000,
      "forbidden_patterns": ["eval(", "exec("],
      "required_patterns": ["^```"]
    },
    "validation": {
      "syntax_check": true,
      "security_scan": true,
      "custom_validators": ["check_quality"]
    }
  }
}
```

## Output Format Configuration

### JSON Output

**Use Case:** Structured data, API responses, machine-readable output

**Configuration:**

```json
{
  "output_format": {
    "type": "json",
    "schema": {
      "type": "object",
      "required": ["result", "confidence"],
      "properties": {
        "result": {
          "type": "string",
          "minLength": 1
        },
        "confidence": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        },
        "metadata": {
          "type": "object",
          "properties": {
            "sources": {
              "type": "array",
              "items": {"type": "string"}
            }
          }
        }
      }
    },
    "strict": true
  }
}
```

**System Message Template:**

```
You are an analyzer. Always respond in JSON format:
{
  "result": "your analysis here",
  "confidence": 0.85,
  "metadata": {
    "sources": ["source1", "source2"]
  }
}
```

**Validation:**
- Checks JSON syntax
- Validates against schema
- Rejects invalid responses

### Code Output

**Use Case:** Code generation, technical documentation

**Configuration:**

```json
{
  "output_format": {
    "type": "code",
    "language": "python",
    "include_explanation": true,
    "format_template": "```{language}\n{code}\n```\n\n{explanation}"
  }
}
```

**System Message Template:**

```
You are a code generator. Generate Python code in this format:

```python
# Your code here
def example():
    pass
```

Explanation: Brief explanation of the code.
```

**Validation:**
- Checks code block syntax
- Validates language specification
- Optionally runs syntax checker

### Text Output

**Use Case:** Natural language responses, essays, summaries

**Configuration:**

```json
{
  "output_format": {
    "type": "text",
    "min_length": 100,
    "max_length": 2000,
    "format": "markdown"
  }
}
```

**System Message Template:**

```
You are a writer. Provide clear, well-structured responses in markdown format.
Keep responses between 100-2000 characters.
```

**Validation:**
- Checks length constraints
- Validates markdown syntax (if specified)
- Checks readability

### Custom Format

**Use Case:** Domain-specific formats

**Configuration:**

```json
{
  "output_format": {
    "type": "custom",
    "format_name": "research_report",
    "template": {
      "sections": ["summary", "findings", "conclusions"],
      "required_fields": ["title", "author", "date"]
    },
    "validator": "validate_research_report"
  }
}
```

## Constraints Configuration

### Length Constraints

```json
{
  "constraints": {
    "max_output_length": 5000,
    "min_output_length": 100,
    "max_tokens": 2000
  }
}
```

**Use Cases:**
- Prevent excessive token usage
- Ensure minimum detail level
- Control response size

### Pattern Constraints

#### Forbidden Patterns

```json
{
  "constraints": {
    "forbidden_patterns": [
      "eval\\(",
      "exec\\(",
      "import os",
      "subprocess",
      "__import__"
    ]
  }
}
```

**Use Cases:**
- Security: Block dangerous code
- Quality: Prevent bad practices
- Compliance: Enforce standards

#### Required Patterns

```json
{
  "constraints": {
    "required_patterns": [
      "^```python",
      "def \\w+\\(",
      "# .*"
    ]
  }
}
```

**Use Cases:**
- Ensure code blocks
- Require function definitions
- Enforce documentation

### Content Constraints

```json
{
  "constraints": {
    "allowed_languages": ["python", "javascript"],
    "forbidden_topics": ["politics", "religion"],
    "required_citations": true,
    "max_code_complexity": 10
  }
}
```

### Timeout Constraints

```json
{
  "constraints": {
    "timeout": 120,
    "max_retries": 3,
    "retry_on_validation_failure": true
  }
}
```

## Validation Configuration

### Syntax Validation

```json
{
  "validation": {
    "syntax_check": true,
    "syntax_checker": "python",
    "fail_on_syntax_error": true
  }
}
```

**Supported Checkers:**
- `python`: Python syntax validation
- `javascript`: JavaScript syntax validation
- `json`: JSON syntax validation
- `markdown`: Markdown syntax validation

### Security Validation

```json
{
  "validation": {
    "security_scan": true,
    "security_rules": [
      "no_eval",
      "no_exec",
      "no_file_operations",
      "no_network_calls"
    ],
    "fail_on_security_issue": true
  }
}
```

**Security Rules:**
- `no_eval`: Block eval() calls
- `no_exec`: Block exec() calls
- `no_file_operations`: Block file I/O
- `no_network_calls`: Block network operations
- `no_dangerous_imports`: Block dangerous modules

### Custom Validation

```json
{
  "validation": {
    "custom_validators": [
      "check_code_quality",
      "verify_imports",
      "validate_docstrings"
    ]
  }
}
```

**Custom Validator Example:**

```python
def check_code_quality(output: str) -> ValidationResult:
    """Check code quality metrics."""
    # Run pylint, flake8, etc.
    score = calculate_quality_score(output)
    
    return ValidationResult(
        valid=score > 0.7,
        errors=[] if score > 0.7 else ["Quality score too low"],
        warnings=get_warnings(output)
    )
```

## Complete Agent Examples

### Example 1: JSON API Agent

```json
{
  "id": "api_agent",
  "type": "conversable",
  "name": "APIAgent",
  "system_message": "You are an API agent. Always respond in JSON format with 'status', 'data', and 'message' fields.",
  "llm_config": {
    "provider_id": "openrouter",
    "model": "openai/gpt-4",
    "temperature": 0.3
  },
  "behavior": {
    "output_format": {
      "type": "json",
      "schema": {
        "type": "object",
        "required": ["status", "data", "message"],
        "properties": {
          "status": {
            "type": "string",
            "enum": ["success", "error", "warning"]
          },
          "data": {
            "type": "object"
          },
          "message": {
            "type": "string"
          }
        }
      },
      "strict": true
    },
    "constraints": {
      "max_output_length": 10000,
      "timeout": 60
    },
    "validation": {
      "syntax_check": true,
      "fail_on_syntax_error": true
    }
  }
}
```

### Example 2: Code Generator Agent

```json
{
  "id": "code_generator",
  "type": "conversable",
  "name": "CodeGenerator",
  "system_message": "You are a Python code generator. Generate clean, well-documented code with type hints.",
  "llm_config": {
    "provider_id": "openrouter",
    "model": "anthropic/claude-3.5-sonnet",
    "temperature": 0.2
  },
  "behavior": {
    "output_format": {
      "type": "code",
      "language": "python",
      "include_explanation": true,
      "format_template": "```python\n{code}\n```\n\n**Explanation:** {explanation}"
    },
    "constraints": {
      "max_output_length": 5000,
      "forbidden_patterns": [
        "eval\\(",
        "exec\\(",
        "import os",
        "__import__"
      ],
      "required_patterns": [
        "^```python",
        "def \\w+\\(",
        "\"\"\".*\"\"\""
      ],
      "timeout": 120
    },
    "validation": {
      "syntax_check": true,
      "syntax_checker": "python",
      "security_scan": true,
      "security_rules": [
        "no_eval",
        "no_exec",
        "no_dangerous_imports"
      ],
      "custom_validators": [
        "check_type_hints",
        "check_docstrings"
      ],
      "fail_on_syntax_error": true,
      "fail_on_security_issue": true
    }
  }
}
```

### Example 3: Research Agent

```json
{
  "id": "research_agent",
  "type": "conversable",
  "name": "ResearchAgent",
  "system_message": "You are a research agent. Provide well-researched, cited responses.",
  "llm_config": {
    "provider_id": "openrouter",
    "model": "openai/gpt-4",
    "temperature": 0.5
  },
  "behavior": {
    "output_format": {
      "type": "json",
      "schema": {
        "type": "object",
        "required": ["summary", "findings", "sources"],
        "properties": {
          "summary": {"type": "string", "minLength": 100},
          "findings": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["finding", "confidence", "source"],
              "properties": {
                "finding": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "source": {"type": "string"}
              }
            }
          },
          "sources": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1
          }
        }
      }
    },
    "constraints": {
      "max_output_length": 10000,
      "required_citations": true,
      "min_sources": 3,
      "timeout": 180
    },
    "validation": {
      "custom_validators": [
        "validate_citations",
        "check_source_quality"
      ]
    }
  }
}
```

### Example 4: Creative Writer Agent

```json
{
  "id": "creative_writer",
  "type": "conversable",
  "name": "CreativeWriter",
  "system_message": "You are a creative writer. Write engaging, original content.",
  "llm_config": {
    "provider_id": "openrouter",
    "model": "anthropic/claude-3-opus",
    "temperature": 0.9
  },
  "behavior": {
    "output_format": {
      "type": "text",
      "format": "markdown",
      "min_length": 500,
      "max_length": 5000
    },
    "constraints": {
      "forbidden_topics": ["violence", "explicit_content"],
      "required_elements": ["introduction", "body", "conclusion"],
      "timeout": 180
    },
    "validation": {
      "custom_validators": [
        "check_readability",
        "check_originality"
      ]
    }
  },
  "cache_override": {
    "llm_response": {
      "enabled": false  // Always generate fresh content
    }
  }
}
```

## Node-Level Behavior Overrides

Override agent behavior for specific nodes in a workflow:

```json
{
  "topology": {
    "nodes": [
      {
        "id": "analyzer_node",
        "agent_id": "reasoning_agent",
        "config_override": {
          "behavior": {
            "output_format": {
              "type": "json",
              "schema": {
                "type": "object",
                "required": ["analysis", "next_steps"],
                "properties": {
                  "analysis": {"type": "string"},
                  "next_steps": {
                    "type": "array",
                    "items": {"type": "string"}
                  }
                }
              }
            },
            "constraints": {
              "max_output_length": 2000
            }
          }
        }
      }
    ]
  }
}
```

## Validation Error Handling

### Retry on Validation Failure

```json
{
  "behavior": {
    "validation": {
      "retry_on_failure": true,
      "max_retries": 3,
      "retry_prompt_template": "Your previous response failed validation: {error}. Please try again following the required format."
    }
  }
}
```

### Fallback Behavior

```json
{
  "behavior": {
    "validation": {
      "fallback_on_failure": true,
      "fallback_response": {
        "status": "error",
        "message": "Failed to generate valid response",
        "error": "{validation_error}"
      }
    }
  }
}
```

### Logging Validation Failures

```json
{
  "behavior": {
    "validation": {
      "log_failures": true,
      "log_level": "WARNING",
      "include_output_in_log": false
    }
  }
}
```

## Best Practices

### 1. Start with Loose Constraints

Begin permissive, then tighten:

```json
// Phase 1: Development
{
  "constraints": {
    "max_output_length": 10000
  },
  "validation": {
    "fail_on_syntax_error": false
  }
}

// Phase 2: Production
{
  "constraints": {
    "max_output_length": 5000,
    "forbidden_patterns": ["eval(", "exec("]
  },
  "validation": {
    "fail_on_syntax_error": true,
    "security_scan": true
  }
}
```

### 2. Use JSON for Structured Data

Always use JSON schema for structured output:

```json
{
  "output_format": {
    "type": "json",
    "schema": {...},
    "strict": true
  }
}
```

### 3. Validate Security-Critical Agents

Always enable security validation for code generators:

```json
{
  "validation": {
    "security_scan": true,
    "security_rules": ["no_eval", "no_exec", "no_dangerous_imports"],
    "fail_on_security_issue": true
  }
}
```

### 4. Document Behavior Configuration

```json
{
  "_behavior_notes": {
    "output_format": "JSON schema ensures consistent API responses",
    "constraints": "Forbidden patterns prevent code injection",
    "validation": "Security scan blocks dangerous operations"
  }
}
```

### 5. Test Validation Rules

```bash
# Test agent with validation
curl -X POST http://localhost:8000/api/v1/agents/test \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "code_generator",
    "message": "Generate a function that uses eval()"
  }'

# Should fail validation
```

### 6. Monitor Validation Failures

```bash
# Check validation metrics
curl http://localhost:8000/api/v1/metrics | grep validation

# Example output:
validation_failures_total{agent="code_generator"} 15
validation_success_rate{agent="code_generator"} 0.95
```

## Troubleshooting

### Issue: Validation Always Fails

**Symptoms:** Agent responses consistently fail validation

**Diagnosis:**
```bash
# Check validation logs
curl http://localhost:8000/api/v1/logs?agent=my_agent&level=WARNING
```

**Solutions:**
1. Review system message - ensure it explains format
2. Check schema - may be too strict
3. Increase max_retries
4. Add retry_prompt_template
5. Test schema with sample data

### Issue: Inconsistent Output Format

**Symptoms:** Agent produces different formats

**Solutions:**
1. Add strict JSON schema
2. Lower temperature (more deterministic)
3. Improve system message
4. Enable validation with fail_on_error
5. Add format examples to system message

### Issue: Security Validation Too Strict

**Symptoms:** Valid code rejected

**Solutions:**
1. Review security rules
2. Adjust forbidden_patterns
3. Use custom validators for nuanced checks
4. Whitelist safe patterns

### Issue: Performance Impact

**Symptoms:** Validation slows down responses

**Solutions:**
1. Disable expensive validators in development
2. Use async validation
3. Cache validation results
4. Optimize custom validators

## Next Steps

1. Review [Topology Configuration](TOPOLOGY_CONFIGURATION.md)
2. Configure [Execution Strategies](EXECUTION_STRATEGIES.md)
3. Set up [Cache Settings](CACHE_CONFIGURATION.md)
4. Read [Troubleshooting Guide](TROUBLESHOOTING.md)
5. Explore [Complete Examples](../configs/templates/complete_examples/)

