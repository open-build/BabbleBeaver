"""
Cost Estimation Module for AI Providers

Provides cost estimation and monthly billing projections for:
- DigitalOcean Gradient AI Platform
- Google Gemini (Vertex AI)
- OpenAI
- Other LLM providers

All pricing is accurate as of December 2024.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class WorkflowType(Enum):
    """Types of AI workflows for cost estimation."""
    SIMPLE_CHAT = "simple_chat"
    CONTEXT_AWARE = "context_aware"
    AGENT_WITH_TOOLS = "agent_with_tools"
    LONG_DOCUMENT = "long_document"
    CODE_GENERATION = "code_generation"


@dataclass
class TokenEstimate:
    """Token count estimates for different workflow types."""
    input_tokens: int
    output_tokens: int
    workflow_type: WorkflowType
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


# Workflow token estimates
WORKFLOW_ESTIMATES = {
    WorkflowType.SIMPLE_CHAT: TokenEstimate(
        input_tokens=100,
        output_tokens=150,
        workflow_type=WorkflowType.SIMPLE_CHAT
    ),
    WorkflowType.CONTEXT_AWARE: TokenEstimate(
        input_tokens=800,  # includes context
        output_tokens=300,
        workflow_type=WorkflowType.CONTEXT_AWARE
    ),
    WorkflowType.AGENT_WITH_TOOLS: TokenEstimate(
        input_tokens=1200,  # includes tool definitions
        output_tokens=500,
        workflow_type=WorkflowType.AGENT_WITH_TOOLS
    ),
    WorkflowType.LONG_DOCUMENT: TokenEstimate(
        input_tokens=5000,
        output_tokens=1000,
        workflow_type=WorkflowType.LONG_DOCUMENT
    ),
    WorkflowType.CODE_GENERATION: TokenEstimate(
        input_tokens=600,
        output_tokens=800,
        workflow_type=WorkflowType.CODE_GENERATION
    ),
}


class CostEstimator:
    """
    Calculate costs for different AI providers based on token usage.
    
    Pricing as of December 2024:
    
    **DigitalOcean Gradient AI Platform:**
    - Hosted models (Llama 3.1 70B): $0.80/1M tokens (input + output)
    - Partner models: Pass-through + 10% markup
    - Knowledge base indexing: $0.09/1M tokens
    - OpenSearch DB: $20-200/month (depends on size)
    
    **Google Gemini (Vertex AI):**
    - Gemini 1.5 Flash: $0.075/1M input, $0.30/1M output (≤128K)
    - Gemini 1.5 Pro: $1.25/1M input, $5.00/1M output (≤128K)
    - Gemini 2.0 Flash: $0.15/1M input, $0.60/1M output
    
    **OpenAI:**
    - GPT-4o: $2.50/1M input, $10.00/1M output
    - GPT-4o-mini: $0.15/1M input, $0.60/1M output
    - GPT-3.5-turbo: $0.50/1M input, $1.50/1M output
    """
    
    # Pricing per 1M tokens (USD)
    PRICING = {
        'digitalocean': {
            'llama_3_1_70b': {'input': 0.80, 'output': 0.80},
            'mistral_7b': {'input': 0.40, 'output': 0.40},
            'knowledge_base_indexing': 0.09,
            'opensearch_db_min': 20.00,  # per month
            'opensearch_db_max': 200.00,  # per month
        },
        'gemini': {
            'flash_1_5': {'input': 0.075, 'output': 0.30},
            'flash_2_0': {'input': 0.15, 'output': 0.60},
            'pro_1_5': {'input': 1.25, 'output': 5.00},
        },
        'openai': {
            'gpt_4o': {'input': 2.50, 'output': 10.00},
            'gpt_4o_mini': {'input': 0.15, 'output': 0.60},
            'gpt_3_5_turbo': {'input': 0.50, 'output': 1.50},
        },
        'anthropic': {
            'claude_3_5_sonnet': {'input': 3.00, 'output': 15.00},
            'claude_3_5_haiku': {'input': 0.80, 'output': 4.00},
        }
    }
    
    @classmethod
    def calculate_cost(
        cls,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Dict[str, Any]:
        """
        Calculate cost for a specific request.
        
        Args:
            provider: Provider name (digitalocean, gemini, openai, anthropic)
            model: Model name (e.g., 'flash_2_0', 'gpt_4o_mini')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost breakdown dictionary
        """
        if provider not in cls.PRICING:
            return {
                'error': f'Unknown provider: {provider}',
                'available_providers': list(cls.PRICING.keys())
            }
        
        if model not in cls.PRICING[provider]:
            return {
                'error': f'Unknown model: {model} for provider: {provider}',
                'available_models': list(cls.PRICING[provider].keys())
            }
        
        pricing = cls.PRICING[provider][model]
        
        # Handle models with symmetric pricing (DigitalOcean)
        if isinstance(pricing, dict) and 'input' in pricing:
            input_cost = (input_tokens / 1_000_000) * pricing['input']
            output_cost = (output_tokens / 1_000_000) * pricing['output']
        else:
            # Flat rate pricing
            total_tokens = input_tokens + output_tokens
            input_cost = (total_tokens / 1_000_000) * pricing
            output_cost = 0
        
        total_cost = input_cost + output_cost
        
        return {
            'provider': provider,
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'total_cost': round(total_cost, 6),
            'currency': 'USD'
        }
    
    @classmethod
    def estimate_workflow_cost(
        cls,
        provider: str,
        model: str,
        workflow_type: WorkflowType
    ) -> Dict[str, Any]:
        """
        Estimate cost for a typical workflow type.
        
        Args:
            provider: Provider name
            model: Model name
            workflow_type: Type of workflow
            
        Returns:
            Cost estimate dictionary
        """
        if workflow_type not in WORKFLOW_ESTIMATES:
            return {
                'error': f'Unknown workflow type: {workflow_type}',
                'available_types': [w.value for w in WorkflowType]
            }
        
        estimate = WORKFLOW_ESTIMATES[workflow_type]
        cost = cls.calculate_cost(
            provider,
            model,
            estimate.input_tokens,
            estimate.output_tokens
        )
        
        cost['workflow_type'] = workflow_type.value
        cost['workflow_description'] = cls._get_workflow_description(workflow_type)
        
        return cost
    
    @classmethod
    def estimate_monthly_cost(
        cls,
        provider: str,
        model: str,
        requests_per_day: int = 1000,
        workflow_type: WorkflowType = WorkflowType.SIMPLE_CHAT,
        include_infrastructure: bool = True
    ) -> Dict[str, Any]:
        """
        Estimate monthly costs based on usage patterns.
        
        Args:
            provider: Provider name
            model: Model name
            requests_per_day: Number of requests per day
            workflow_type: Type of workflow
            include_infrastructure: Include infrastructure costs (DB, etc.)
            
        Returns:
            Monthly cost estimate dictionary
        """
        if workflow_type not in WORKFLOW_ESTIMATES:
            return {
                'error': f'Unknown workflow type: {workflow_type}',
                'available_types': [w.value for w in WorkflowType]
            }
        
        estimate = WORKFLOW_ESTIMATES[workflow_type]
        days_per_month = 30
        total_requests = requests_per_day * days_per_month
        
        total_input_tokens = total_requests * estimate.input_tokens
        total_output_tokens = total_requests * estimate.output_tokens
        
        api_cost = cls.calculate_cost(
            provider,
            model,
            total_input_tokens,
            total_output_tokens
        )
        
        # Add infrastructure costs
        infrastructure_cost = 0
        infrastructure_notes = []
        
        if include_infrastructure:
            if provider == 'digitalocean':
                # Estimate OpenSearch DB cost (mid-range)
                infrastructure_cost = 100.00  # $100/month mid-range
                infrastructure_notes.append(
                    'Includes OpenSearch database for knowledge bases ($20-200/month)'
                )
            elif provider == 'gemini':
                # Vertex AI has minimal infrastructure costs
                infrastructure_cost = 0
                infrastructure_notes.append('Serverless - no infrastructure costs')
            elif provider == 'openai':
                # OpenAI is fully managed
                infrastructure_cost = 0
                infrastructure_notes.append('Fully managed - no infrastructure costs')
        
        total_cost = api_cost['total_cost'] + infrastructure_cost
        
        return {
            'provider': provider,
            'model': model,
            'period': 'monthly',
            'workflow_type': workflow_type.value,
            'requests_per_day': requests_per_day,
            'total_requests': total_requests,
            'avg_tokens_per_request': estimate.total_tokens,
            'total_tokens': total_input_tokens + total_output_tokens,
            'api_cost': round(api_cost['total_cost'], 2),
            'infrastructure_cost': round(infrastructure_cost, 2),
            'total_cost': round(total_cost, 2),
            'cost_per_request': round(total_cost / total_requests, 6),
            'currency': 'USD',
            'notes': infrastructure_notes
        }
    
    @classmethod
    def compare_providers(
        cls,
        workflow_type: WorkflowType = WorkflowType.SIMPLE_CHAT,
        requests_per_day: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Compare costs across all providers for a given workflow.
        
        Args:
            workflow_type: Type of workflow to compare
            requests_per_day: Number of requests per day
            
        Returns:
            List of cost estimates sorted by total cost
        """
        # Default models for comparison
        comparisons = [
            ('digitalocean', 'llama_3_1_70b'),
            ('gemini', 'flash_2_0'),
            ('gemini', 'flash_1_5'),
            ('openai', 'gpt_4o_mini'),
            ('openai', 'gpt_3_5_turbo'),
            ('anthropic', 'claude_3_5_haiku'),
        ]
        
        results = []
        for provider, model in comparisons:
            try:
                estimate = cls.estimate_monthly_cost(
                    provider,
                    model,
                    requests_per_day,
                    workflow_type,
                    include_infrastructure=True
                )
                if 'error' not in estimate:
                    results.append(estimate)
            except Exception as e:
                continue
        
        # Sort by total cost
        results.sort(key=lambda x: x['total_cost'])
        
        return results
    
    @staticmethod
    def _get_workflow_description(workflow_type: WorkflowType) -> str:
        """Get human-readable description of workflow type."""
        descriptions = {
            WorkflowType.SIMPLE_CHAT: "Simple Q&A without context (~250 tokens)",
            WorkflowType.CONTEXT_AWARE: "Chat with context/history (~1,100 tokens)",
            WorkflowType.AGENT_WITH_TOOLS: "Agent with tool calling (~1,700 tokens)",
            WorkflowType.LONG_DOCUMENT: "Long document analysis (~6,000 tokens)",
            WorkflowType.CODE_GENERATION: "Code generation with examples (~1,400 tokens)",
        }
        return descriptions.get(workflow_type, "Unknown workflow")
    
    @classmethod
    def get_pricing_table(cls) -> Dict[str, Any]:
        """
        Get complete pricing table for all providers and models.
        
        Returns:
            Formatted pricing information
        """
        return {
            'pricing': cls.PRICING,
            'currency': 'USD',
            'unit': 'per 1M tokens',
            'last_updated': '2024-12-09',
            'notes': [
                'Prices may change. Check provider websites for current rates.',
                'DigitalOcean infrastructure costs not included in token pricing.',
                'Some providers offer volume discounts for high usage.',
            ]
        }


def get_current_model_config() -> Dict[str, str]:
    """
    Get currently configured models from environment variables.
    
    Returns:
        Dictionary of current model configuration
    """
    return {
        'gemini_model': os.getenv('VERTEX_MODEL_NAME', 'gemini-2.0-flash-exp'),
        'openai_model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
        'digitalocean_enabled': os.getenv('DIGITALOCEAN_AGENT_ENABLED', 'false'),
        'gemini_enabled': os.getenv('GEMINI_ENABLED', 'true'),
        'openai_enabled': os.getenv('OPENAI_ENABLED', 'false'),
    }


# Convenience function for quick estimates
def quick_estimate(
    requests_per_day: int = 1000,
    workflow_type: str = 'simple_chat'
) -> List[Dict[str, Any]]:
    """
    Quick cost comparison across all providers.
    
    Args:
        requests_per_day: Number of requests per day
        workflow_type: Type of workflow (simple_chat, context_aware, etc.)
        
    Returns:
        Sorted list of cost estimates
    """
    try:
        wf_type = WorkflowType(workflow_type)
    except ValueError:
        wf_type = WorkflowType.SIMPLE_CHAT
    
    return CostEstimator.compare_providers(
        workflow_type=wf_type,
        requests_per_day=requests_per_day
    )
