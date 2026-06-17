"""
Deep Search Service for MiroFish.
Autonomously researches topics using DuckDuckGo + BeautifulSoup + LLM Orchestration.
"""

import logging
import os
import json
import requests
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from ..config import Config

logger = logging.getLogger(__name__)

class DeepSearchService:
    """
    Agente Orquestador de Research.
    Uses DDG Search + LLM to research topics and build seed documents.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        from openai import OpenAI
        self.client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
        
    def perform_research(self, theme: str, max_results: int = 3) -> str:
        """
        Main entry point for autonomous research.
        """
        logger.info(f"Starting Deep Search for theme: {theme}")
        
        try:
            # 1. Expand Queries
            queries = self.expand_queries(theme)
            logger.info(f"Expanded queries: {queries}")
            
            # 2. Search and Scrape
            scraped_data = []
            visited_urls = set()
            
            for query in queries:
                urls = self.search(query, limit=2)
                for url in urls:
                    if url in visited_urls:
                        continue
                    visited_urls.add(url)
                    content = self.scrape(url)
                    if content:
                        scraped_data.append(f"Source: {url}\n{content[:2000]}") # Keep it bounded
            
            if not scraped_data:
                logger.warning("Scraping failed (possibly blocked). Falling back to LLM internal knowledge for research...")
                fallback_prompt = f"""
                You are an Expert Research Agent. The web search failed, but I need you to generate a detailed briefing document based on your internal knowledge regarding the topic: "{theme}".
                
                Please synthesize all the relevant facts, figures, dates, and actors into a clean, comprehensive briefing document.
                Keep it factual, detailed, and structure it as if it were a scraped research report.
                """
                response = self.client.chat.completions.create(
                    model=Config.LLM_MODEL_NAME,
                    messages=[
                        {"role": "system", "content": "You are a professional research analyst."},
                        {"role": "user", "content": fallback_prompt}
                    ],
                    temperature=0.3
                )
                research_content = response.choices[0].message.content
                logger.info(f"Deep Search (LLM Fallback) complete. Content length: {len(research_content)}")
                return f"--- AUTONOMOUS DEEP SEARCH (LLM INTERNAL) RESEARCH: {theme} ---\n\n{research_content}\n"
                
            raw_text = "\n\n---\n\n".join(scraped_data)
            
            # 3. Consolidate and Summarize using LLM
            logger.info("Consolidating search results via LLM...")
            prompt = f"""
            You are a Research Assistant preparing a seed document for a social simulation.
            I have scraped several web sources regarding the topic: "{theme}".
            
            Please synthesize all the relevant facts, figures, dates, and actors into a clean, comprehensive briefing document.
            Keep it factual and detailed.
            
            RAW SCRAPED DATA:
            {raw_text}
            """
            
            messages = [
                {"role": "system", "content": "You are a professional research analyst."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.client.chat.completions.create(
                model=Config.LLM_MODEL_NAME,
                messages=messages,
                temperature=0.3
            )
            
            research_content = response.choices[0].message.content
            
            logger.info(f"Deep Search complete. Content length: {len(research_content)}")
            full_report = f"--- AUTONOMOUS DEEP SEARCH RESEARCH: {theme} ---\n\n{research_content}\n"
            return full_report
            
        except Exception as e:
            logger.error(f"Deep Search failed: {e}")
            return f"Deep Search failed due to an error: {str(e)}"

    def expand_queries(self, theme: str) -> List[str]:
        """
        Uses LLM to generate orthogonal sub-queries.
        """
        try:
            prompt = f"""Generate exactly 3 short search engine queries to research the following topic: "{theme}".
            Return ONLY a valid JSON list of strings."""
            
            response = self.client.chat.completions.create(
                model=Config.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            content = response.choices[0].message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            queries = json.loads(content)
            return queries[:3] if isinstance(queries, list) else [theme]
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return [theme]

    def search(self, query: str, limit: int = 2) -> List[str]:
        """
        DuckDuckGo HTML fallback search using lite version.
        """
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            url = f"https://html.duckduckgo.com/html/?q={query}"
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = []
            for a in soup.find_all('a', class_='result__snippet', href=True):
                href = a['href']
                if 'duckduckgo.com/l/?' in href:
                    href = href.split('uddg=')[1].split('&')[0]
                    from urllib.parse import unquote
                    href = unquote(href)
                links.append(href)
                if len(links) >= limit:
                    break
            
            # If standard class fails, try fallback
            if not links:
                for a in soup.find_all('a', class_='result__url', href=True):
                    href = a['href']
                    if 'duckduckgo.com/l/?' in href:
                        href = href.split('uddg=')[1].split('&')[0]
                        from urllib.parse import unquote
                        href = unquote(href)
                    links.append(href)
                    if len(links) >= limit:
                        break
            
            return links
        except Exception as e:
            logger.error(f"DDG search failed: {e}")
            return []

    def scrape(self, url: str) -> Optional[str]:
        """
        Scrapes and cleans content from a URL.
        """
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
                
            lines = [line.strip() for line in soup.get_text(separator='\n').splitlines() if len(line.strip()) > 30]
            return "\n".join(lines)
        except:
            return None
