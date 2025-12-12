"""
DigitalOcean Gradient AI Agent Module

This module provides integration with DigitalOcean's Gradient AI Platform agents
to provide AI-powered chat capabilities as a fallback or alternative provider.

Environment Variables:
    DIGITALOCEAN_AGENT_ENABLED: Set to 'true' or '1' to enable (default: disabled)
    DIGITALOCEAN_API_TOKEN: API token for authentication
    DIGITALOCEAN_AGENT_URL: Agent endpoint URL
    DIGITALOCEAN_PRIORITY: Priority level (0=highest, default: 2)
"""

import os
import logging
from typing import Dict, List, Optional, Any
import httpx
import asyncio
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class DigitalOceanAgent:
    """
    Integration client for DigitalOcean Gradient AI Platform agents.
    
    Provides async methods to interact with DigitalOcean agents for
    chat completion and context-aware responses.
    """
    
    def __init__(
        self, 
        api_token: Optional[str] = None,
        agent_url: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize the DigitalOcean Agent client.
        
        Args:
            api_token: API token for authentication
            agent_url: Full agent endpoint URL
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.api_token = api_token or os.getenv('DIGITALOCEAN_API_TOKEN')
        self.agent_url = agent_url or os.getenv('DIGITALOCEAN_AGENT_URL')
        self.timeout = timeout
        self.enabled = self._check_if_enabled()
        self.priority = int(os.getenv('DIGITALOCEAN_PRIORITY', '2'))
        
        if self.enabled and not self.api_token:
            logger.warning("DigitalOcean agent enabled but no API_TOKEN provided")
        
        logger.info(
            f"DigitalOceanAgent initialized. "
            f"Enabled: {self.enabled}, "
            f"Priority: {self.priority}, "
            f"URL: {self.agent_url if self.agent_url else 'Not set'}"
        )
    
    def _check_if_enabled(self) -> bool:
        """Check if the agent is enabled via environment variable."""
        enabled = os.getenv('DIGITALOCEAN_AGENT_ENABLED', 'false').lower()
        return enabled in ('true', '1', 'yes', 'on')
    
    async def chat_completion(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Optional[str]:
        """
        Send a chat completion request to the DigitalOcean agent.
        
        Args:
            prompt: User message/prompt
            context: Optional context dictionary for contextual responses
            stream: Whether to stream the response (default: False)
            
        Returns:
            Agent response as string, or None if request fails
        """
        if not self.enabled:
            logger.debug("DigitalOcean agent is disabled")
            return None
        
        if not self.agent_url:
            logger.error("DigitalOcean agent URL not configured")
            return None
        
        if not self.api_token:
            logger.error("DigitalOcean API token not configured")
            return None
        
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        # Build payload according to DigitalOcean Gradient AI API
        payload = {
            'messages': [
                {'role': 'user', 'content': prompt}
            ]
        }
        
        # Add context if provided
        if context:
            # Prepend context as a system message
            context_message = self._format_context(context)
            payload['messages'].insert(0, {
                'role': 'system',
                'content': context_message
            })
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.agent_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Extract response based on DigitalOcean response format
                # Format: {"response": "...", "status": "success"}
                if isinstance(data, dict):
                    if 'response' in data:
                        return data['response']
                    elif 'choices' in data and len(data['choices']) > 0:
                        # OpenAI-compatible format
                        return data['choices'][0]['message']['content']
                    elif 'content' in data:
                        return data['content']
                
                logger.warning(f"Unexpected response format: {data}")
                return str(data)
                
        except httpx.TimeoutException:
            logger.warning(f"Timeout calling DigitalOcean agent at {self.agent_url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"HTTP error {e.response.status_code} calling DigitalOcean agent: "
                f"{e.response.text}"
            )
            return None
        except Exception as e:
            logger.error(f"Error calling DigitalOcean agent: {e}")
            return None
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """
        Format context dictionary into a readable system message.
        
        Args:
            context: Context dictionary
            
        Returns:
            Formatted context string
        """
        lines = ["Context information:"]
        for key, value in context.items():
            formatted_key = key.replace('_', ' ').title()
            lines.append(f"- {formatted_key}: {value}")
        return "\n".join(lines)
    
    def get_cost_estimate(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> Dict[str, Any]:
        """
        Estimate the cost of a request based on token count.
        
        DigitalOcean Gradient AI Platform pricing (as of Dec 2024):
        - Hosted models (Llama, Mistral): $0.40-$2.00 per 1M tokens
        - Partner models (GPT-4o, Claude): Pass-through pricing + 10%
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost breakdown dictionary
        """
        # Conservative estimate using Llama 3.1 70B pricing
        input_cost_per_1m = 0.80  # $0.80 per 1M input tokens
        output_cost_per_1m = 0.80  # $0.80 per 1M output tokens
        
        input_cost = (input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * output_cost_per_1m
        total_cost = input_cost + output_cost
        
        return {
            'provider': 'digitalocean',
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'input_cost': round(input_cost, 6),
            'output_cost': round(output_cost, 6),
            'total_cost': round(total_cost, 6),
            'currency': 'USD',
            'pricing_tier': 'hosted_model',
            'notes': 'Estimate based on Llama 3.1 70B pricing. Partner models may vary.'
        }
    
    def estimate_monthly_cost(
        self,
        requests_per_day: int = 1000,
        avg_input_tokens: int = 500,
        avg_output_tokens: int = 300
    ) -> Dict[str, Any]:
        """
        Estimate monthly costs based on usage patterns.
        
        Args:
            requests_per_day: Number of requests per day
            avg_input_tokens: Average input tokens per request
            avg_output_tokens: Average output tokens per request
            
        Returns:
            Monthly cost estimate dictionary
        """
        days_per_month = 30
        total_requests = requests_per_day * days_per_month
        
        total_input_tokens = total_requests * avg_input_tokens
        total_output_tokens = total_requests * avg_output_tokens
        
        cost_estimate = self.get_cost_estimate(
            total_input_tokens,
            total_output_tokens
        )
        
        return {
            'provider': 'digitalocean',
            'period': 'monthly',
            'requests_per_day': requests_per_day,
            'total_requests': total_requests,
            'avg_input_tokens': avg_input_tokens,
            'avg_output_tokens': avg_output_tokens,
            'total_input_tokens': total_input_tokens,
            'total_output_tokens': total_output_tokens,
            'estimated_cost': cost_estimate['total_cost'],
            'currency': 'USD',
            'notes': (
                'Includes API usage only. '
                'Add OpenSearch database costs ($20-200/month) if using knowledge bases. '
                'Knowledge base indexing billed separately at $0.09/1M tokens.'
            )
        }


# Global instance
_agent_instance = None


def get_agent() -> DigitalOceanAgent:
    """
    Get or create the global DigitalOcean agent instance.
    
    Returns:
        DigitalOceanAgent instance
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = DigitalOceanAgent()
    return _agent_instance


async def test_connection() -> Dict[str, Any]:
    """
    Test the DigitalOcean agent connection with a simple request.
    
    Returns:
        Test result dictionary with status and response
    """
    agent = get_agent()
    
    if not agent.enabled:
        return {
            'status': 'disabled',
            'message': 'DigitalOcean agent is not enabled',
            'enabled': False
        }
    
    if not agent.agent_url or not agent.api_token:
        return {
            'status': 'error',
            'message': 'DigitalOcean agent URL or API token not configured',
            'enabled': True,
            'configured': False
        }
    
    try:
        start_time = datetime.now()
        response = await agent.chat_completion("Hello, are you working?")
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if response:
            return {
                'status': 'success',
                'message': 'Connection successful',
                'enabled': True,
                'configured': True,
                'response_time': round(elapsed, 2),
                'sample_response': response[:100] + '...' if len(response) > 100 else response
            }
        else:
            return {
                'status': 'error',
                'message': 'Request completed but no response received',
                'enabled': True,
                'configured': True,
                'response_time': round(elapsed, 2)
            }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Connection test failed: {str(e)}',
            'enabled': True,
            'configured': True,
            'error': str(e)
        }
