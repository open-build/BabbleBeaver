"""
Context Builder - Constructs context-aware system prompts

This module enhances BabbleBeaver with automatic context awareness,
allowing it to provide more relevant responses based on user context,
product data, and session information.

ALWAYS ENABLED - If context is provided, it will be used automatically.
Set CONTEXT_AWARE_MODE=disabled to completely disable this feature.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds context-aware system prompts from various context sources."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the context builder.
        
        Args:
            config_path: Path to context configuration file (optional)
        """
        self.config = self._load_config(config_path)
        # Check if feature is explicitly disabled
        self.disabled = os.getenv("CONTEXT_AWARE_MODE", "auto") == "disabled"
        
    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """Load context configuration from file or use defaults."""
        default_config = {
            "context_mode": "disabled",
            "prompt_template": "minimal",
            "max_context_items": 10  # Limit number of context items to avoid bloat
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load context config: {e}, using defaults")
        
        return default_config
    
    def build_context_prompt(
        self,
        base_prompt: str,
        context: Optional[Dict[str, Any]] = None,
        product_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build enhanced system prompt with context awareness.
        
        Args:
            base_prompt: Original system prompt
            context: User-provided context (from frontend)
            product_context: Enriched product context (from Buildly Agent)
            
        Returns:
            Enhanced system prompt with context information
        """
        # If feature is explicitly disabled, return base prompt
        if self.disabled:
            return base_prompt
            
        # If no context provided, return base prompt unchanged
        if not context and not product_context:
            return base_prompt
        
        # Build generic context from any provided data
        context_lines = []
        
        # Generic context from user-provided data (accept ANY JSON)
        if context and isinstance(context, dict):
            context_lines.extend(self._format_generic_context(context))
        
        # Product context from Buildly Agent (if enriched)
        if product_context and product_context.get("enabled"):
            context_lines.extend(self._format_product_enrichment(product_context))
        
        if not context_lines:
            return base_prompt
        
        # Format based on template
        template = self.config.get("prompt_template", "minimal")
        
        if template == "verbose":
            return self._verbose_template(base_prompt, context_lines)
        else:  # minimal (default)
            return self._minimal_template(base_prompt, context_lines)
    
    def _format_generic_context(self, context: Dict[str, Any]) -> List[str]:
        """
        Format any JSON context generically without assumptions.
        Accepts ANY key-value pairs and formats them nicely.
        """
        lines = []
        max_items = self.config.get("max_context_items", 10)
        count = 0
        
        for key, value in context.items():
            if count >= max_items:
                lines.append(f"... and {len(context) - count} more context items")
                break
            
            # Format key nicely (snake_case -> Title Case)
            formatted_key = key.replace("_", " ").title()
            
            # Handle different value types
            if isinstance(value, (str, int, float, bool)):
                lines.append(f"- {formatted_key}: {value}")
                count += 1
            elif isinstance(value, dict):
                # Nested object - format as JSON string (truncated)
                json_str = json.dumps(value)
                if len(json_str) > 100:
                    json_str = json_str[:100] + "..."
                lines.append(f"- {formatted_key}: {json_str}")
                count += 1
            elif isinstance(value, list):
                # List - show first few items
                if len(value) > 0 and all(isinstance(v, str) for v in value[:3]):
                    preview = ", ".join(str(v) for v in value[:3])
                    if len(value) > 3:
                        preview += f" (+{len(value) - 3} more)"
                    lines.append(f"- {formatted_key}: {preview}")
                    count += 1
        
        return lines
    
    def _format_product_enrichment(self, product_context: Dict[str, Any]) -> List[str]:
        """Format product enrichment from Buildly Agent (if available)."""
        lines = []
        
        product_info = product_context.get("product_info", {})
        if product_info and isinstance(product_info, dict):
            if "name" in product_info:
                lines.append(f"- Product: {product_info['name']}")
            if "description" in product_info:
                desc = str(product_info["description"])[:150]
                lines.append(f"- Description: {desc}")
        
        # Features
        features = product_context.get("features", [])
        if features and isinstance(features, list):
            feature_names = [f.get("name", "") for f in features[:3] if isinstance(f, dict)]
            if feature_names:
                lines.append(f"- Features: {', '.join(feature_names)}")
        
        return lines
    
    def _minimal_template(self, base_prompt: str, context_lines: List[str]) -> str:
        """Minimal template - adds context subtly."""
        if not context_lines:
            return base_prompt
        
        context_block = "\n".join(context_lines)
        return f"""{base_prompt}

CURRENT CONTEXT:
{context_block}
"""
    
    def _verbose_template(self, base_prompt: str, context_lines: List[str]) -> str:
        """Verbose template - more explicit about context usage."""
        if not context_lines:
            return base_prompt
        
        context_block = "\n".join(context_lines)
        return f"""{base_prompt}

CONTEXTUAL INFORMATION:
{context_block}

INSTRUCTIONS:
- Use the above context when relevant to the user's question
- Reference specific context details naturally in your response
- If context is insufficient for a complete answer, ask clarifying questions
"""


# Singleton instance
context_builder = ContextBuilder()
