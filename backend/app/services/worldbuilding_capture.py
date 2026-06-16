"""
Observational capture of worldbuilding traces for MiroFish.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class WorldbuildingCapture:
    """
    Captures all pre-simulation decisions and artifacts for training and audit.
    """
    
    def __init__(self, simulation_id: str, simulation_dir: str):
        self.simulation_id = simulation_id
        self.simulation_dir = simulation_dir
        self.trace_file = os.path.join(simulation_dir, "worldbuilding_trace.json")
        self.trace_data: Dict[str, Any] = {
            "trace_version": 1,
            "simulation_id": simulation_id,
            "created_at": datetime.now().isoformat(),
            "input_context": {},
            "source_snapshot": {},
            "prompt_snapshot": {},
            "graph_snapshot": {},
            "entity_filtering_trace": {},
            "agent_selection_trace": {},
            "simulation_social_graph_trace": {},
            "profile_generation_trace": {},
            "simulation_config_trace": {},
            "pre_simulation_validation": {}
        }
    
    def capture_input(self, input_context: Dict[str, Any]):
        self.trace_data["input_context"] = input_context
        self._save()
        
    def capture_stage(self, stage_name: str, data: Dict[str, Any]):
        if stage_name in self.trace_data:
            self.trace_data[stage_name] = data
            self._save()
        else:
            logger.warning(f"Unknown worldbuilding stage: {stage_name}")

    def _save(self):
        try:
            with open(self.trace_file, 'w', encoding='utf-8') as f:
                json.dump(self.trace_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save worldbuilding trace: {str(e)}")
