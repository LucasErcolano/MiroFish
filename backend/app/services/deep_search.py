"""
Deep Search Service for MiroFish.
Autonomously researches topics using Tavily API + LLM Orchestration.
"""

import logging
import os
import json
from typing import List, Dict, Any, Optional
from ..config import Config
from openai import OpenAI

logger = logging.getLogger(__name__)

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

class DeepSearchService:
    """
    Agente Orquestador de Research.
    Uses Tavily API to research topics and build seed documents, with LLM fallback.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.tavily_key = api_key or Config.TAVILY_API_KEY
        self.client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
        if not self.tavily_key:
            logger.warning("TAVILY_API_KEY not configured. Deep Search will use LLM Fallback mode exclusively.")
        elif TavilyClient is None:
            logger.warning("tavily package is not installed. Deep Search will use LLM Fallback mode exclusively.")
            
    def perform_research(self, theme: str, max_results: int = 5, max_date: Optional[str] = None) -> str:
        """
        Main entry point for autonomous research.
        """
        logger.info(f"Starting Deep Search for theme: {theme}")
        
        raw_text = ""
        
        # 1. Search via Tavily (if configured)
        if self.tavily_key and TavilyClient is not None:
            try:
                tavily_client = TavilyClient(api_key=self.tavily_key)
                
                # We let Tavily handle the smart search and extraction
                logger.info("Executing Tavily Search...")
                search_kwargs = {
                    "query": theme,
                    "search_depth": "advanced",
                    "max_results": max_results,
                    "include_answer": True,
                    "include_raw_content": False
                }
                if max_date:
                    search_kwargs["end_date"] = max_date
                    
                response = tavily_client.search(**search_kwargs)
                
                # Compile results
                scraped_data = []
                if "answer" in response and response["answer"]:
                    scraped_data.append(f"Tavily Summary: {response['answer']}\n")
                    
                for result in response.get("results", []):
                    content = result.get("content", "")
                    url = result.get("url", "")
                    if content:
                        scraped_data.append(f"Source: {url}\n{content}\n")
                
                if scraped_data:
                    raw_text = "\n\n---\n\n".join(scraped_data)
                    logger.info("Tavily Search successful.")
                else:
                    logger.warning("Tavily returned no data. Proceeding to LLM Fallback.")
                    
            except Exception as e:
                logger.error(f"Tavily search failed: {e}")
        
        # 2. LLM Fallback if Tavily failed or wasn't configured
        if not raw_text:
            logger.warning("Using LLM Internal Knowledge for Deep Search...")
            date_instruction = f"\n\nCRITICAL (ANTI-DATA LEAKAGE): You MUST NOT include any events, facts, or data that occurred after the cutoff date: {max_date}. Act as if your knowledge stops exactly at {max_date}." if max_date else ""
            prompt = f"""
            You are an Expert Research Agent. The web search was unavailable, but I need you to generate a detailed briefing document based on your internal knowledge regarding the topic: "{theme}".
            
            Please synthesize all the relevant facts, figures, dates, and actors into a clean, comprehensive briefing document.
            Keep it factual, detailed, and structure it as if it were a scraped research report.{date_instruction}
            """
            header = f"--- AUTONOMOUS DEEP SEARCH (LLM INTERNAL KNOWLEDGE): {theme} ---\n\n"
        else:
            # 3. Consolidate Tavily results using LLM
            logger.info("Consolidating Tavily search results via LLM...")
            date_instruction = f"\n\nCRITICAL (ANTI-DATA LEAKAGE): You MUST discard any information from the WEB SEARCH DATA that references events or facts occurring after the cutoff date: {max_date}. Do not include them in the briefing." if max_date else ""
            prompt = f"""
            You are a Research Assistant preparing a seed document for a social simulation.
            I have gathered information from the web regarding the topic: "{theme}".
            
            Please synthesize all the relevant facts, figures, dates, and actors into a clean, comprehensive briefing document.
            Keep it factual and detailed.{date_instruction}
            
            WEB SEARCH DATA:
            {raw_text}
            """
            header = f"--- AUTONOMOUS DEEP SEARCH (TAVILY GROUNDED): {theme} ---\n\n"
            
        try:
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
            
            return header + research_content + "\n"
            
        except Exception as e:
            logger.error(f"LLM Synthesis failed: {e}")
            return f"Deep Search failed due to an error: {str(e)}"
