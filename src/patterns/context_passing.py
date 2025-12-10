"""
AUTOGEN 0.2 RESEARCH:
- Feature needed: Context passing strategies and message transformation between agents
- Autogen provides: Conversation history via chat_result.chat_history, summary via summary_method
- Using: Custom context passing strategies extending Autogen's conversation patterns
- Documentation: https://microsoft.github.io/autogen/0.2/docs/reference/agentchat/conversable_agent
- Decision: Custom implementation - Autogen provides basic context via chat history and summaries,
  but we need advanced strategies (selective, transformation, size management) for complex workflows
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import jq


class ContextStrategy(str, Enum):
    """Strategy for passing context between agents."""
    
    FULL = "full"
    SUMMARY = "summary"
    SELECTIVE = "selective"


@dataclass
class ContextPassingConfig:
    """Configuration for context passing between agents."""
    
    strategy: ContextStrategy = ContextStrategy.FULL
    fields: Optional[List[str]] = None
    max_size: int = 100000  # Maximum context size in characters
    summarization_prompt: Optional[str] = None
    transformation_rules: Optional[List[Dict[str, Any]]] = None


class ContextTransformer(ABC):
    """Abstract base class for context transformers."""
    
    @abstractmethod
    def transform(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform context according to specific rules.
        
        Args:
            context: Input context dictionary
            
        Returns:
            Transformed context dictionary
        """
        pass


class JQTransformer(ContextTransformer):
    """Transformer using jq-style expressions."""
    
    def __init__(self, expression: str):
        """
        Initialize JQ transformer.
        
        Args:
            expression: jq expression (e.g., '.topics[0]', '.plan')
        """
        self.expression = expression
        try:
            self.compiled = jq.compile(expression)
        except Exception as e:
            raise ValueError(f"Invalid jq expression '{expression}': {e}")
    
    def transform(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply jq transformation to context.
        
        Args:
            context: Input context
            
        Returns:
            Transformed context
        """
        try:
            result = self.compiled.input(context).first()
            # Wrap result in dict if it's not already
            if isinstance(result, dict):
                return result
            else:
                return {"value": result}
        except Exception as e:
            raise ValueError(f"Failed to apply jq expression '{self.expression}': {e}")


class FieldSelectorTransformer(ContextTransformer):
    """Transformer that selects specific fields from context."""
    
    def __init__(self, fields: List[str]):
        """
        Initialize field selector.
        
        Args:
            fields: List of field names to select
        """
        self.fields = fields
    
    def transform(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Select specified fields from context.
        
        Args:
            context: Input context
            
        Returns:
            Context with only selected fields
        """
        result = {}
        for field in self.fields:
            # Support nested field access with dot notation
            if '.' in field:
                value = self._get_nested_field(context, field)
                if value is not None:
                    self._set_nested_field(result, field, value)
            else:
                if field in context:
                    result[field] = context[field]
        return result
    
    def _get_nested_field(self, data: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value using dot notation."""
        parts = field_path.split('.')
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
    
    def _set_nested_field(self, data: Dict[str, Any], field_path: str, value: Any) -> None:
        """Set nested field value using dot notation."""
        parts = field_path.split('.')
        current = data
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value


class MessageTransformationRule:
    """Rule for transforming messages."""
    
    def __init__(
        self,
        pattern: Optional[str] = None,
        replacement: Optional[str] = None,
        filter_func: Optional[str] = None,
        transform_func: Optional[str] = None,
    ):
        """
        Initialize transformation rule.
        
        Args:
            pattern: Regex pattern to match
            replacement: Replacement string (for regex substitution)
            filter_func: Python expression to filter messages (returns bool)
            transform_func: Python expression to transform message content
        """
        self.pattern = re.compile(pattern) if pattern else None
        self.replacement = replacement
        self.filter_func = filter_func
        self.transform_func = transform_func
    
    def apply(self, message: str) -> Optional[str]:
        """
        Apply transformation rule to message.
        
        Args:
            message: Input message
            
        Returns:
            Transformed message or None if filtered out
        """
        # Apply filter if specified
        if self.filter_func:
            try:
                # Create safe evaluation context
                context = {"message": message, "len": len, "str": str}
                if not eval(self.filter_func, {"__builtins__": {}}, context):
                    return None
            except Exception:
                # If filter fails, keep the message
                pass
        
        # Apply transformation
        result = message
        
        if self.pattern and self.replacement is not None:
            result = self.pattern.sub(self.replacement, result)
        
        if self.transform_func:
            try:
                context = {"message": result, "len": len, "str": str, "upper": str.upper, "lower": str.lower}
                result = eval(self.transform_func, {"__builtins__": {}}, context)
            except Exception:
                # If transformation fails, return original
                pass
        
        return result


class ContextSizeManager:
    """Manages context size and applies summarization when needed."""
    
    def __init__(
        self,
        max_size: int = 100000,
        summarization_strategy: str = "truncate",
        summarization_prompt: Optional[str] = None,
    ):
        """
        Initialize context size manager.
        
        Args:
            max_size: Maximum context size in characters
            summarization_strategy: Strategy for reducing size ('truncate', 'summarize', 'compress')
            summarization_prompt: Optional prompt for LLM-based summarization
        """
        self.max_size = max_size
        self.summarization_strategy = summarization_strategy
        self.summarization_prompt = summarization_prompt
    
    def manage_size(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manage context size, applying summarization if needed.
        
        Args:
            context: Input context
            
        Returns:
            Context with managed size
        """
        # Calculate current size
        context_str = json.dumps(context)
        current_size = len(context_str)
        
        if current_size <= self.max_size:
            return context
        
        # Apply size reduction strategy
        if self.summarization_strategy == "truncate":
            return self._truncate_context(context, current_size)
        elif self.summarization_strategy == "compress":
            return self._compress_context(context)
        elif self.summarization_strategy == "summarize":
            # For now, fall back to truncate
            # In production, this would call an LLM to summarize
            return self._truncate_context(context, current_size)
        else:
            return context
    
    def _truncate_context(self, context: Dict[str, Any], current_size: int) -> Dict[str, Any]:
        """Truncate context to fit within size limit."""
        # For nested dicts, we need to be more aggressive
        # Calculate reduction ratio with more aggressive margin
        ratio = min(0.7, self.max_size / current_size)  # Cap at 70% to account for overhead
        
        result = {}
        for key, value in context.items():
            if isinstance(value, str):
                # Truncate strings proportionally with larger margin
                new_length = int(len(value) * ratio)
                result[key] = value[:new_length] + "..." if len(value) > new_length and new_length > 0 else value[:new_length] if new_length > 0 else ""
            elif isinstance(value, list):
                # Keep fewer items from lists
                new_length = max(0, int(len(value) * ratio))
                result[key] = value[:new_length] if new_length > 0 else []
            elif isinstance(value, dict):
                # For nested dicts, apply even more aggressive truncation
                nested_size = len(json.dumps(value))
                # Allocate proportional space to nested dict
                nested_max = max(20, int(self.max_size * ratio * 0.5))  # Give nested dict less space
                nested_manager = ContextSizeManager(max_size=nested_max, summarization_strategy="truncate")
                result[key] = nested_manager.manage_size(value)
            else:
                result[key] = value
        
        # Double-check size and further reduce if needed
        result_str = json.dumps(result)
        if len(result_str) > self.max_size:
            # More aggressive truncation needed
            # Remove keys until we fit, but keep at least one key
            keys_to_keep = list(result.keys())
            while len(json.dumps({k: result[k] for k in keys_to_keep})) > self.max_size and len(keys_to_keep) > 1:
                keys_to_keep.pop()
            
            # If even one key is too large, truncate its value
            if len(keys_to_keep) == 1:
                key = keys_to_keep[0]
                value = result[key]
                if isinstance(value, str):
                    # Truncate string to fit within max_size
                    # Account for JSON overhead and Unicode encoding
                    # Start with a conservative estimate
                    max_value_len = max(1, int(self.max_size * 0.3))  # Very conservative
                    truncated_value = value[:max_value_len]
                    test_dict = {key: truncated_value}
                    
                    # Iteratively reduce until it fits
                    while len(json.dumps(test_dict)) > self.max_size and max_value_len > 1:
                        max_value_len = int(max_value_len * 0.7)
                        truncated_value = value[:max_value_len]
                        test_dict = {key: truncated_value}
                    
                    result = test_dict
                elif isinstance(value, dict):
                    # Nested dict - recursively truncate with smaller limit
                    nested_manager = ContextSizeManager(max_size=int(self.max_size * 0.8), summarization_strategy="truncate")
                    result = {key: nested_manager.manage_size(value)}
                else:
                    result = {key: value}
            else:
                result = {k: result[k] for k in keys_to_keep}
        
        return result
    
    def _compress_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Compress context by removing less important fields."""
        # Priority order for keeping fields
        priority_fields = ['response', 'result', 'output', 'summary', 'message']
        
        result = {}
        current_size = 0
        
        # First, add priority fields
        for field in priority_fields:
            if field in context:
                field_str = json.dumps({field: context[field]})
                if current_size + len(field_str) <= self.max_size:
                    result[field] = context[field]
                    current_size += len(field_str)
        
        # Then add other fields if space allows
        for key, value in context.items():
            if key not in priority_fields:
                field_str = json.dumps({key: value})
                if current_size + len(field_str) <= self.max_size:
                    result[key] = value
                    current_size += len(field_str)
                else:
                    break
        
        return result


class ContextPassingEngine:
    """Engine for managing context passing between agents."""
    
    def __init__(self, config: Optional[ContextPassingConfig] = None):
        """
        Initialize context passing engine.
        
        Args:
            config: Context passing configuration
        """
        self.config = config or ContextPassingConfig()
        self.size_manager = ContextSizeManager(
            max_size=self.config.max_size,
            summarization_prompt=self.config.summarization_prompt,
        )
    
    def prepare_context(
        self,
        source_context: Dict[str, Any],
        strategy: Optional[ContextStrategy] = None,
        fields: Optional[List[str]] = None,
        transformation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Prepare context for passing to next agent.
        
        Args:
            source_context: Source context from previous agent
            strategy: Context passing strategy (overrides config)
            fields: Fields to select (for selective strategy)
            transformation: jq expression for transformation
            
        Returns:
            Prepared context
        """
        # Use provided strategy or fall back to config
        strategy = strategy or self.config.strategy
        
        # Apply transformation if specified
        if transformation:
            transformer = JQTransformer(transformation)
            context = transformer.transform(source_context)
        else:
            context = source_context.copy()
        
        # Apply strategy
        if strategy == ContextStrategy.FULL:
            result = context
        elif strategy == ContextStrategy.SUMMARY:
            result = self._create_summary(context)
        elif strategy == ContextStrategy.SELECTIVE:
            fields = fields or self.config.fields
            if not fields:
                raise ValueError("Selective strategy requires fields to be specified")
            transformer = FieldSelectorTransformer(fields)
            result = transformer.transform(context)
        else:
            result = context
        
        # Manage size
        result = self.size_manager.manage_size(result)
        
        return result
    
    def _create_summary(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create summary of context.
        
        Args:
            context: Full context
            
        Returns:
            Summarized context
        """
        # Extract key information for summary
        summary = {}
        
        # Include response/output if present
        for key in ['response', 'output', 'result', 'summary']:
            if key in context:
                summary[key] = context[key]
                break
        
        # Include metadata
        if 'metadata' in context:
            summary['metadata'] = context['metadata']
        
        # Include conversation summary if present
        if 'conversation_history' in context:
            history = context['conversation_history']
            if isinstance(history, list) and history:
                # Keep only last few messages
                summary['recent_messages'] = history[-3:]
        
        return summary
    
    def apply_transformation_rules(
        self,
        messages: List[str],
        rules: List[MessageTransformationRule],
    ) -> List[str]:
        """
        Apply transformation rules to messages.
        
        Args:
            messages: List of messages
            rules: List of transformation rules
            
        Returns:
            Transformed messages (filtered messages are removed)
        """
        result = []
        for message in messages:
            transformed = message
            for rule in rules:
                transformed = rule.apply(transformed)
                if transformed is None:
                    break
            if transformed is not None:
                result.append(transformed)
        return result
    
    def transform_output(
        self,
        output: Any,
        transformation: Optional[str] = None,
    ) -> Any:
        """
        Transform agent output using jq expression.
        
        Args:
            output: Agent output
            transformation: jq expression
            
        Returns:
            Transformed output
        """
        if not transformation:
            return output
        
        # Convert output to dict if it's not already
        if isinstance(output, str):
            try:
                output_dict = json.loads(output)
            except json.JSONDecodeError:
                output_dict = {"text": output}
        elif isinstance(output, dict):
            output_dict = output
        else:
            output_dict = {"value": output}
        
        # Apply transformation
        transformer = JQTransformer(transformation)
        return transformer.transform(output_dict)
