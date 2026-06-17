"""
Deep Search Service for MiroFish.
Autonomously researches topics, expands queries, and scrapes content to build seed documents.
"""

import logging
import json
import requests
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ..utils.llm_client import LLMClient
from ..config import Config

logger = logging.getLogger(__name__)

class DeepSearchService:
    """
    Agente Orquestador de Research.
    Takes a theme, plans sub-queries, searches, scrapes, and consolidates content.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.llm = LLMClient()
        self.search_api_key = api_key or getattr(Config, 'DEEP_SEARCH_API_KEY', None)
        self.search_provider = getattr(Config, 'DEEP_SEARCH_PROVIDER', 'duckduckgo')
        
    def perform_research(self, theme: str, max_results: int = 5) -> str:
        """
        Main entry point for autonomous research.
        """
        logger.info(f"Starting Deep Search for theme: {theme}")
        
        # 1. Query Expansion
        queries = self.expand_queries(theme)
        logger.info(f"Expanded queries: {queries}")
        
        # 2. Search and Scrape
        all_content = []
        for query in queries:
            urls = self.search(query, limit=max_results)
            for url in urls:
                content = self.scrape(url)
                if content:
                    all_content.append(f"Source: {url}\n\n{content}\n\n" + "="*50 + "\n")
        
        # 3. Consolidate
        consolidated_text = "\n".join(all_content)
        logger.info(f"Deep Search complete. Total content length: {len(consolidated_text)}")
        
        return consolidated_text

    def expand_queries(self, theme: str) -> List[str]:
        """
        Uses LLM to generate 3-5 orthogonal sub-queries for the given theme.
        """
        prompt = f"""
        Given the following simulation theme: "{theme}"
        Generate 3 to 5 orthogonal and specific search queries to gather comprehensive context for a social simulation.
        Focus on facts, dates, key actors, and specific events.
        
        Return the queries as a JSON list of strings.
        Example: ["query 1", "query 2", "query 3"]
        """
        
        messages = [
            {"role": "system", "content": "You are a research planning assistant. Respond only with a JSON list of search queries."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            queries = self.llm.chat_json(messages)
            if isinstance(queries, list):
                return queries[:5]
            return [theme]
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return [theme]

    def search(self, query: str, limit: int = 5) -> List[str]:
        """
        Performs a web search using the configured provider.
        """
        if self.search_provider == 'tavily' and self.search_api_key:
            return self._search_tavily(query, limit)
        else:
            # Fallback to a simple DuckDuckGo search (via public lite interface or similar)
            return self._search_duckduckgo(query, limit)

    def _search_tavily(self, query: str, limit: int) -> List[str]:
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.search_api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": limit
                }
            )
            data = response.json()
            return [result['url'] for result in data.get('results', [])]
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []

    def _search_duckduckgo(self, query: str, limit: int) -> List[str]:
        """
        Basic DuckDuckGo search using the HTML interface.
        Note: This is brittle and for fallback/demo purposes.
        """
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            url = f"https://html.duckduckgo.com/html/?q={query}"
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = []
            for a in soup.find_all('a', class_='result__a', href=True):
                href = a['href']
                # DDG sometimes wraps URLs
                if 'duckduckgo.com/l/?kh=-1&uddg=' in href:
                    href = href.split('uddg=')[1].split('&')[0]
                    from urllib.parse import unquote
                    href = unquote(href)
                links.append(href)
                if len(links) >= limit:
                    break
            return links
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []

    def scrape(self, url: str) -> Optional[str]:
        """
        Scrapes and cleans content from a URL.
        """
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove scripts, styles, ads
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
                
            text = soup.get_text(separator='\n')
            
            # Basic cleaning
            lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 20]
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {e}")
            return None
