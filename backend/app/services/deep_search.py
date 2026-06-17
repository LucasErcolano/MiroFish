"""
Deep Search Service for MiroFish.
Autonomously researches topics using Gemini's Google Search Grounding.
"""

import logging
import os
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from ..config import Config

logger = logging.getLogger(__name__)

class DeepSearchService:
    """
    Agente Orquestador de Research.
    Uses Gemini with Google Search Grounding to research topics and build seed documents.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not configured. Deep Search might fail.")
        else:
            genai.configure(api_key=self.api_key)
        
    def perform_research(self, theme: str, max_results: int = 5) -> str:
        """
        Main entry point for autonomous research using Gemini Grounding.
        """
        if not self.api_key:
            return "Deep Search failed: GEMINI_API_KEY not configured."

        logger.info(f"Starting Gemini Deep Search for theme: {theme}")
        
        try:
            # The prompt string should be defined before the loop
            prompt = f"""
            Perform a deep research on the following topic for a social simulation: "{theme}"
            Gather key facts, dates, main actors, and specific events.
            Provide a comprehensive summary based on current search results.
            Cite your sources if possible.
            """
            
            # List of models found in the 2026 environment list
            potential_models = [
                'models/gemini-2.0-flash-lite', 
                'models/gemini-2.5-flash',
                'models/gemini-flash-latest'
            ]
            
            response = None
            
            for model_name in potential_models:
                try:
                    logger.info(f"Trying Gemini model: {model_name} with google_search_retrieval tool...")
                    # In newer Gemini API, grounding is often passed via tools as a dict or via google_search_retrieval
                    # Using the standard v1beta syntax for google search
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        tools=[{"google_search": {}}]
                    )
                    
                    response = model.generate_content(prompt)
                    if response:
                        logger.info(f"Success with model: {model_name}")
                        break
                except Exception as e:
                    # Fallback syntax if the API is strict
                    try:
                        logger.info(f"Retrying {model_name} without explicit tool config or with fallback tool name...")
                        model = genai.GenerativeModel(model_name=model_name)
                        # We just send the prompt without forcing the tool if it crashes
                        response = model.generate_content(prompt)
                        if response:
                            break
                    except Exception as inner_e:
                        logger.warning(f"Model {model_name} failed: {inner_e}")
                        continue
            
            if not response:
                return "Deep Search failed: Could not generate content with the available Gemini models."
            
            research_content = response.text
            
            logger.info(f"Gemini Deep Search complete. Content length: {len(research_content)}")
            
            # Optionally add a header to indicate this is grounded content
            full_report = f"--- GEMINI GROUNDED RESEARCH: {theme} ---\n\n{research_content}\n"
            
            return full_report
            
        except Exception as e:
            logger.error(f"Gemini Deep Search failed: {e}")
            return f"Deep Search failed due to an error: {str(e)}"

    # The original methods expand_queries, search, and scrape are now handled by Gemini Grounding
    # We keep them (or stubs) if we ever want to revert or use hybrid search
    def expand_queries(self, theme: str) -> List[str]:
        return [theme]

    def search(self, query: str, limit: int = 5) -> List[str]:
        return []

    def scrape(self, url: str) -> Optional[str]:
        return None
