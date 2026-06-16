"""
Schema and versioning for simulation planning workflows.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class PlanningWorkflowArtifact(BaseModel):
    workflow_artifact_version: int = 1
    simulation_id: str
    project_id: str
    graph_id: str
    
    objective: Dict[str, Any] = Field(default_factory=dict)
    source_plan: Dict[str, Any] = Field(default_factory=dict)
    entity_extraction_plan: Dict[str, Any] = Field(default_factory=dict)
    evidence_graph_plan: Dict[str, Any] = Field(default_factory=dict)
    agent_selection_plan: Dict[str, Any] = Field(default_factory=dict)
    simulation_social_graph_plan: Dict[str, Any] = Field(default_factory=dict)
    event_plan: Dict[str, Any] = Field(default_factory=dict)
    platform_plan: Dict[str, Any] = Field(default_factory=dict)
    execution_parameters: Dict[str, Any] = Field(default_factory=dict)
    
    judge_trace: Dict[str, Any] = Field(default_factory=dict)
    uncertainties: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    rejected_alternatives: List[str] = Field(default_factory=list)
    
    verifier: Dict[str, Any] = Field(default_factory=dict)
    execution_ready: bool = False
