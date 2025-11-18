"""
Buildly Labs Agent Module

This module provides agentic capabilities for querying Buildly Labs API endpoints
to retrieve product information, features, and releases. It uses async operations
to minimize latency and enriches AI prompts with real-time product data.

Environment Variables:
    BUILDLY_AGENT: Set to 'true' or '1' to enable the agent (default: disabled)
    BUILDLY_API_BASE_URL: Base URL for Buildly Labs API (default: https://labs-api.buildly.io)
"""

import os
import logging
from typing import Dict, List, Optional, Any
import httpx
import asyncio
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class BuildlyAgent:
    """
    Agentic interface for Buildly Labs API integration.
    
    Provides async methods to fetch product data and enrich AI prompts
    with contextual information about Buildly Labs products.
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        """
        Initialize the Buildly Agent.
        
        Args:
            base_url: Base URL for Buildly Labs API
            timeout: Request timeout in seconds (default: 5.0)
        """
        self.base_url = base_url or os.getenv(
            'BUILDLY_API_BASE_URL', 
            'https://labs-api.buildly.io'
        )
        self.timeout = timeout
        self.enabled = self._check_if_enabled()
        
        logger.info(f"BuildlyAgent initialized. Enabled: {self.enabled}, Base URL: {self.base_url}")
    
    def _check_if_enabled(self) -> bool:
        """Check if the agent is enabled via environment variable."""
        enabled = os.getenv('BUILDLY_AGENT', 'false').lower()
        return enabled in ('true', '1', 'yes', 'on')
    
    async def _fetch_endpoint(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Fetch data from a specific API endpoint.
        
        Args:
            endpoint: API endpoint path (e.g., '/products/uuid')
            
        Returns:
            JSON response as dict, or None if request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching {url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error {e.response.status_code} fetching {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    async def get_product_info(self, product_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Fetch basic product information.
        
        Args:
            product_uuid: UUID of the product
            
        Returns:
            Product information dict or None
        """
        endpoint = f"/products/{product_uuid}"
        return await self._fetch_endpoint(endpoint)
    
    async def get_product_features(self, product_uuid: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch product features.
        
        Args:
            product_uuid: UUID of the product
            
        Returns:
            List of features or None
        """
        endpoint = f"/products/{product_uuid}/features"
        return await self._fetch_endpoint(endpoint)
    
    async def get_product_releases(self, product_uuid: str) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch product releases.
        
        Args:
            product_uuid: UUID of the product
            
        Returns:
            List of releases or None
        """
        endpoint = f"/products/{product_uuid}/releases"
        return await self._fetch_endpoint(endpoint)
    
    async def gather_product_context(self, product_uuid: str) -> Dict[str, Any]:
        """
        Gather all product context in parallel for maximum performance.
        
        Args:
            product_uuid: UUID of the product
            
        Returns:
            Dictionary containing product info, features, and releases
        """
        if not self.enabled:
            logger.debug("BuildlyAgent is disabled. Skipping product context gathering.")
            return {"enabled": False}
        
        logger.info(f"Gathering product context for UUID: {product_uuid}")
        
        # Fetch all data in parallel to minimize latency
        results = await asyncio.gather(
            self.get_product_info(product_uuid),
            self.get_product_features(product_uuid),
            self.get_product_releases(product_uuid),
            return_exceptions=True
        )
        
        product_info, features, releases = results
        
        # Handle any exceptions from gather
        if isinstance(product_info, Exception):
            logger.error(f"Error fetching product info: {product_info}")
            product_info = None
        if isinstance(features, Exception):
            logger.error(f"Error fetching features: {features}")
            features = None
        if isinstance(releases, Exception):
            logger.error(f"Error fetching releases: {releases}")
            releases = None
        
        return {
            "enabled": True,
            "product_uuid": product_uuid,
            "product_info": product_info,
            "features": features,
            "releases": releases,
            "fetched_at": datetime.utcnow().isoformat()
        }
    
    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format the gathered context into a string suitable for AI prompt enrichment.
        
        Args:
            context: Dictionary from gather_product_context()
            
        Returns:
            Formatted string to append to the AI prompt
        """
        if not context.get("enabled"):
            return ""
        
        parts = []
        parts.append("\n--- BUILDLY LABS PRODUCT CONTEXT ---\n")
        
        # Format product info
        product_info = context.get("product_info")
        if product_info:
            parts.append("Product Information:")
            if isinstance(product_info, dict):
                for key, value in product_info.items():
                    parts.append(f"  - {key}: {value}")
            else:
                parts.append(f"  {product_info}")
            parts.append("")
        
        # Format features
        features = context.get("features")
        if features:
            parts.append("Product Features:")
            if isinstance(features, list):
                for idx, feature in enumerate(features, 1):
                    if isinstance(feature, dict):
                        name = feature.get('name', feature.get('title', f'Feature {idx}'))
                        desc = feature.get('description', '')
                        parts.append(f"  {idx}. {name}")
                        if desc:
                            parts.append(f"     {desc}")
                    else:
                        parts.append(f"  {idx}. {feature}")
            else:
                parts.append(f"  {features}")
            parts.append("")
        
        # Format releases
        releases = context.get("releases")
        if releases:
            parts.append("Product Releases:")
            if isinstance(releases, list):
                for idx, release in enumerate(releases, 1):
                    if isinstance(release, dict):
                        version = release.get('version', release.get('name', f'Release {idx}'))
                        date = release.get('release_date', release.get('date', ''))
                        notes = release.get('notes', release.get('description', ''))
                        parts.append(f"  {idx}. Version {version}")
                        if date:
                            parts.append(f"     Released: {date}")
                        if notes:
                            parts.append(f"     Notes: {notes}")
                    else:
                        parts.append(f"  {idx}. {release}")
            else:
                parts.append(f"  {releases}")
            parts.append("")
        
        parts.append("--- END PRODUCT CONTEXT ---\n")
        
        return "\n".join(parts)
    
    async def enrich_prompt(self, user_message: str, product_uuid: Optional[str] = None) -> tuple[str, Dict[str, Any]]:
        """
        Enrich a user message with product context if product_uuid is detected.
        
        Args:
            user_message: Original user message
            product_uuid: Optional product UUID (will attempt to extract if not provided)
            
        Returns:
            Tuple of (enriched_message, context_data)
        """
        if not self.enabled:
            return user_message, {"enabled": False}
        
        # If product_uuid not provided, try to extract it from the message
        if not product_uuid:
            product_uuid = self.extract_product_uuid(user_message)
        
        if not product_uuid:
            logger.debug("No product_uuid found in message")
            return user_message, {"enabled": True, "product_uuid": None}
        
        # Gather product context
        context = await self.gather_product_context(product_uuid)
        
        # Format and enrich the prompt
        context_text = self.format_context_for_prompt(context)
        
        if context_text:
            enriched_message = f"{user_message}\n\n{context_text}"
        else:
            enriched_message = user_message
        
        return enriched_message, context
    
    @staticmethod
    def extract_product_uuid(text: str) -> Optional[str]:
        """
        Extract product_uuid from text using pattern matching.
        
        Looks for patterns like:
        - product_uuid: <uuid>
        - product_uuid=<uuid>
        - "product_uuid": "<uuid>"
        
        Args:
            text: Text to search for product_uuid
            
        Returns:
            Extracted UUID or None
        """
        import re
        
        # Pattern to match UUID format (8-4-4-4-12 hex digits)
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        
        # Patterns to look for product_uuid
        patterns = [
            rf'product_uuid[:\s=]+["\']?({uuid_pattern})["\']?',
            rf'product[_\s]uuid[:\s=]+["\']?({uuid_pattern})["\']?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None


# Singleton instance for easy access
_agent_instance: Optional[BuildlyAgent] = None


def get_agent() -> BuildlyAgent:
    """
    Get or create the singleton BuildlyAgent instance.
    
    Returns:
        BuildlyAgent instance
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = BuildlyAgent()
    return _agent_instance


async def enrich_user_message(user_message: str, product_uuid: Optional[str] = None) -> tuple[str, Dict[str, Any]]:
    """
    Convenience function to enrich a user message with Buildly Labs product context.
    
    Args:
        user_message: Original user message
        product_uuid: Optional product UUID
        
    Returns:
        Tuple of (enriched_message, context_data)
    """
    agent = get_agent()
    return await agent.enrich_prompt(user_message, product_uuid)
