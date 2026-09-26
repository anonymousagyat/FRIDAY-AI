"""
Web Researcher — Autonomous Agentic Web Intelligence Engine powered by Tavily AI.
Performs live web crawling, bypasses paywalls/bot-detection, strips ads,
and extracts clean markdown content for Friday's AI brain.
"""

import json
import logging
import requests
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class WebResearcher:
    """Agentic web search and deep content extraction using Tavily AI."""

    TAVILY_SEARCH_URL = "https://api.tavily.com/search"
    TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ""
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Friday-AI/2.0 (Windows 11 Personal Executive Assistant)"
        })

    def is_configured(self) -> bool:
        """Check if a valid Tavily API key is set."""
        return bool(self.api_key and self.api_key.startswith("tvly-"))

    def search(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 5,
        include_answer: bool = True,
        include_raw_content: bool = False
    ) -> Dict[str, Any]:
        """
        Execute an autonomous agentic web search.
        
        Args:
            query: The search query or question
            search_depth: 'basic' (fast sub-second) or 'advanced' (deep multi-layer research)
            max_results: Number of top results to return (1-10)
            include_answer: Request Tavily's pre-synthesized factual answer
            include_raw_content: Include raw HTML/text if needed
            
        Returns:
            Dict containing:
            - 'success': bool
            - 'query': str
            - 'answer': synthesized direct answer (if available)
            - 'results': list of {title, url, content, score}
            - 'formatted_context': clean markdown string ready for LLM consumption
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "Tavily API key not configured in config.json",
                "formatted_context": "Tavily search is not configured."
            }

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max(1, min(max_results, 10)),
            "include_answer": include_answer,
            "include_raw_content": include_raw_content
        }

        try:
            response = self.session.post(
                self.TAVILY_SEARCH_URL,
                json=payload,
                timeout=12
            )

            if response.status_code != 200:
                logger.error(f"[WebResearcher] Tavily error HTTP {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "error": f"Tavily HTTP {response.status_code}",
                    "formatted_context": f"Search failed with error {response.status_code}"
                }

            data = response.json()
            answer = data.get("answer", "")
            raw_results = data.get("results", [])

            clean_results = []
            context_lines = []

            if answer:
                context_lines.append(f"### Direct Fact Summary:\n{answer}\n")

            context_lines.append("### Web Sources & Details:")
            for i, r in enumerate(raw_results, 1):
                title = r.get("title", "Untitled")
                url = r.get("url", "")
                content = r.get("content", "").strip()

                clean_results.append({
                    "title": title,
                    "url": url,
                    "content": content,
                    "score": r.get("score", 0.0)
                })

                context_lines.append(f"{i}. **{title}**\n   URL: {url}\n   Snippet: {content}\n")

            formatted_context = "\n".join(context_lines)

            return {
                "success": True,
                "query": query,
                "answer": answer,
                "results": clean_results,
                "formatted_context": formatted_context,
                "response_time": data.get("response_time", 0)
            }

        except requests.Timeout:
            logger.error(f"[WebResearcher] Search timed out for query: '{query}'")
            return {
                "success": False,
                "error": "Search timed out",
                "formatted_context": "Web search timed out."
            }
        except Exception as e:
            logger.error(f"[WebResearcher] Search exception: {e}")
            return {
                "success": False,
                "error": str(e),
                "formatted_context": f"Search failed: {str(e)}"
            }

    def deep_research(self, query: str) -> Dict[str, Any]:
        """Deep research mode — searches with advanced depth for complex topics."""
        return self.search(query, search_depth="advanced", max_results=6, include_answer=True)

    def extract_url(self, url: str) -> Dict[str, Any]:
        """Extract clean markdown content from a specific URL."""
        if not self.is_configured():
            return {"success": False, "error": "Tavily API key not configured"}

        payload = {
            "api_key": self.api_key,
            "urls": [url]
        }

        try:
            response = self.session.post(
                self.TAVILY_EXTRACT_URL,
                json=payload,
                timeout=15
            )
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    return {
                        "success": True,
                        "url": url,
                        "content": results[0].get("raw_content", "") or results[0].get("text", "")
                    }
            return {"success": False, "error": f"Failed to extract URL (HTTP {response.status_code})"}
        except Exception as e:
            return {"success": False, "error": str(e)}
