"""
Passive worldbuilding trace capture for simulation preparation.

This module records the factual artifacts MiroFish already produced before a
simulation runs. It does not add planners, judges, or gating behavior.
"""

import hashlib
import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import Config
from ..models.project import ProjectManager
from ..utils.logger import get_logger

logger = get_logger('mirofish.worldbuilding_trace')


class WorldbuildingTraceCapture:
    """Build and save worldbuilding_trace.json for one prepared simulation."""

    TRACE_VERSION = 2
    TRACE_FILENAME = "worldbuilding_trace.json"

    @classmethod
    def save_trace(
        cls,
        *,
        simulation_dir: str,
        state: Any,
        filtered_entities: Any,
        profiles: List[Any],
        simulation_params: Any,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]],
        use_llm_for_profiles: bool,
        parallel_profile_count: int,
        llm_call_records: Optional[List[Dict[str, Any]]] = None,
        warnings: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Write a passive capture artifact and return its path."""
        if not Config.PLANNING_CAPTURE_ENABLED:
            logger.info("Worldbuilding trace capture disabled")
            return None

        trace = cls.build_trace(
            simulation_dir=simulation_dir,
            state=state,
            filtered_entities=filtered_entities,
            profiles=profiles,
            simulation_params=simulation_params,
            simulation_requirement=simulation_requirement,
            document_text=document_text,
            defined_entity_types=defined_entity_types,
            use_llm_for_profiles=use_llm_for_profiles,
            parallel_profile_count=parallel_profile_count,
            llm_call_records=llm_call_records,
            warnings=warnings,
        )

        os.makedirs(simulation_dir, exist_ok=True)
        trace_path = os.path.join(simulation_dir, cls.TRACE_FILENAME)

        # Write once so the manifest can include a stable self-reference entry.
        cls._write_json(trace_path, trace)
        trace["artifact_manifest"] = cls._build_artifact_manifest(simulation_dir)
        cls._write_json(trace_path, trace)

        logger.info(f"Worldbuilding trace saved: {trace_path}")
        return trace_path

    @classmethod
    def build_trace(
        cls,
        *,
        simulation_dir: str,
        state: Any,
        filtered_entities: Any,
        profiles: List[Any],
        simulation_params: Any,
        simulation_requirement: str,
        document_text: str,
        defined_entity_types: Optional[List[str]],
        use_llm_for_profiles: bool,
        parallel_profile_count: int,
        llm_call_records: Optional[List[Dict[str, Any]]] = None,
        warnings: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build the trace payload without writing it to disk."""
        created_at = datetime.now().isoformat()
        project = ProjectManager.get_project(state.project_id)
        entities = getattr(filtered_entities, "entities", [])
        profiles_data = [cls._to_plain_dict(profile) for profile in profiles]
        sim_params_data = cls._to_plain_dict(simulation_params)
        state_data = cls._to_plain_dict(state)
        project_metadata = cls._to_plain_dict(getattr(project, "metadata", {}) or {})
        warnings = [str(item) for item in (warnings or []) if item]

        source_files = cls._build_source_file_snapshot(project)
        excluded_files = cls._build_excluded_file_snapshot(project_metadata)
        entity_types = sorted(list(getattr(filtered_entities, "entity_types", []) or []))
        total_count = getattr(filtered_entities, "total_count", None)
        filtered_count = getattr(filtered_entities, "filtered_count", None)
        llm_call_records = cls._to_plain_dict(llm_call_records or [])
        project_status = cls._to_plain_dict(getattr(project, "status", None))
        profile_output_files = cls._build_expected_output_files(
            simulation_dir,
            ["reddit_profiles.json", "twitter_profiles.csv"],
        )
        config_output_file = cls._build_expected_output_files(
            simulation_dir,
            ["simulation_config.json"],
        )
        graph_snapshot_entities = [cls._to_plain_dict(entity) for entity in entities]

        return {
            "trace_version": cls.TRACE_VERSION,
            "simulation_id": state.simulation_id,
            "project_id": state.project_id,
            "graph_id": state.graph_id,
            "created_at": created_at,
            "capture": {
                "enabled": Config.PLANNING_CAPTURE_ENABLED,
                "mode": Config.PLANNING_CAPTURE_MODE,
                "save_raw_artifacts": Config.PLANNING_CAPTURE_SAVE_RAW_ARTIFACTS,
                "redact_secrets": Config.PLANNING_CAPTURE_REDACT_SECRETS,
                "behavior": "passive_capture_only",
            },
            "input_context": {
                "original_prompt": project_metadata.get("original_user_prompt") or simulation_requirement,
                "normalized_task_prompt": project_metadata.get("normalized_task_prompt") or simulation_requirement,
                "task_objective": project_metadata.get("task_objective"),
                "simulation_requirement": simulation_requirement,
                "system_constraints": project_metadata.get("system_constraints_text"),
                "document_text_length": len(document_text or ""),
                "document_text_sha256": cls._sha256_text(document_text or ""),
                "document_text_saved_raw": False,
                "project_name": getattr(project, "name", None) if project else None,
                "language": os.environ.get("MIROFISH_LOCALE") or os.environ.get("LANG"),
                "enable_twitter": bool(getattr(state, "enable_twitter", False)),
                "enable_reddit": bool(getattr(state, "enable_reddit", False)),
                "defined_entity_types_requested": defined_entity_types or None,
                "use_llm_for_profiles": use_llm_for_profiles,
                "parallel_profile_count": parallel_profile_count,
                "cutoff_date": project_metadata.get("cutoff_date"),
                "temporal_package": project_metadata.get("temporal_package"),
                "source_ids": project_metadata.get("source_ids", []),
                "requested_model": project_metadata.get("model"),
                "requested_seed": project_metadata.get("seed"),
                "requested_rounds": project_metadata.get("rounds"),
                "requested_density": project_metadata.get("density"),
                "source_files": source_files,
                "excluded_files": excluded_files,
            },
            "source_snapshot": {
                "graph_backend": Config.GRAPH_BACKEND,
                "graph_reused": True,
                "graph_id": state.graph_id,
                "graph_build_status": project_status,
                "documents_ingested": len(source_files),
                "chunk_size": getattr(project, "chunk_size", None),
                "chunk_overlap": getattr(project, "chunk_overlap", None),
                "llm_model_for_graph": Config.GRAPHITI_LLM_MODEL,
                "embedding_model": Config.GRAPHITI_EMBEDDER_MODEL,
                "total_nodes_seen": getattr(filtered_entities, "total_count", None),
                "filtered_entities_count": getattr(filtered_entities, "filtered_count", None),
                "filtered_entity_types": entity_types,
                "graph_memory_enabled": not Config.USE_EXPERIMENTAL_MEMORY,
                "experimental_memory_enabled": Config.USE_EXPERIMENTAL_MEMORY,
                "warnings": warnings,
            },
            "prompt_snapshot": {
                "original_user_prompt": project_metadata.get("original_user_prompt") or simulation_requirement,
                "normalized_task_prompt": project_metadata.get("normalized_task_prompt") or simulation_requirement,
                "system_constraints_text": project_metadata.get("system_constraints_text"),
                "simulation_requirement": simulation_requirement,
                "llm_calls": llm_call_records,
                "profile_generation_prompts_captured": any(
                    item.get("stage") == "profile_generation" for item in llm_call_records
                ),
                "config_generation_prompts_captured": any(
                    str(item.get("stage", "")).startswith("config_") for item in llm_call_records
                ),
                "note": "LLM prompts/outputs are referenced as secondary artifacts when capture is enabled.",
            },
            "graph_snapshot": {
                "filtered_entities": graph_snapshot_entities,
                "metrics": {
                    "node_count": filtered_count,
                    "candidate_node_count": total_count,
                    "edge_count": sum(len(item.get("edges", []) or []) for item in graph_snapshot_entities),
                    "connected_components": None,
                },
            },
            "entity_filtering_trace": {
                "requested_entity_types": defined_entity_types or None,
                "candidate_count": total_count,
                "accepted_count": filtered_count,
                "rejected_count": max((total_count or 0) - (filtered_count or 0), 0),
                "total_count": total_count,
                "filtered_count": filtered_count,
                "entity_types_found": entity_types,
                "filter_rule": "keep nodes with labels other than Entity/Node, optionally restricted by requested types",
                "candidate_entities": [
                    {
                        "uuid": item.get("uuid"),
                        "name": item.get("name"),
                        "entity_type": item.get("entity_type") or item.get("type"),
                        "summary": item.get("summary"),
                        "status": "accepted",
                        "reason": "selected_by_defined_entity_filter",
                    }
                    for item in graph_snapshot_entities
                ],
            },
            "agent_selection_trace": {
                "candidate_entity_count": filtered_count,
                "selected_agent_count": len(profiles_data),
                "configured_agent_count": len(profiles_data),
                "discarded_entities_count": max((filtered_count or 0) - len(profiles_data), 0),
                "selected_agents": [
                    {
                        "user_id": profile.get("user_id"),
                        "name": profile.get("name"),
                        "username": profile.get("user_name") or profile.get("username"),
                        "source_entity_uuid": profile.get("source_entity_uuid"),
                        "source_entity_type": profile.get("source_entity_type"),
                    }
                    for profile in profiles_data
                ],
            },
            "simulation_social_graph_trace": {
                "construction_method": "simulation_config_generator_agent_activity_only",
                "explicit_social_graph_generated": False,
                "agent_activity_configs_count": len(sim_params_data.get("agent_configs", []) or []),
                "agent_activity_configs": sim_params_data.get("agent_configs", []),
                "platform_configs": {
                    "twitter": sim_params_data.get("twitter_config"),
                    "reddit": sim_params_data.get("reddit_config"),
                },
                "metrics": {
                    "agent_count": len(profiles_data),
                    "edge_count": 0,
                    "density": None,
                },
            },
            "profile_generation_trace": {
                "profile_generator": "OasisProfileGenerator",
                "use_llm_for_profiles": use_llm_for_profiles,
                "parallel_profile_count": parallel_profile_count,
                "profiles_count": len(profiles_data),
                "profiles": profiles_data,
                "output_files": profile_output_files,
                "model": Config.LLM_MODEL_NAME,
                "warnings": warnings,
            },
            "simulation_config_trace": {
                **sim_params_data,
                "config_generator": "SimulationConfigGenerator",
                "output_file": config_output_file[0] if config_output_file else None,
            },
            "pre_simulation_validation": {
                "status": state_data.get("status"),
                "status_after_prepare": state_data.get("status"),
                "config_generated": state_data.get("config_generated"),
                "simulation_config_generated": state_data.get("config_generated"),
                "entities_count": state_data.get("entities_count"),
                "profiles_count": state_data.get("profiles_count"),
                "profiles_generated": bool(profiles_data),
                "blocking_issues": [state_data.get("error")] if state_data.get("error") else [],
                "warnings": warnings,
                "oasis_graph_instantiated": False,
                "env_reset_completed": False,
                "env_step_completed": False,
                "error": state_data.get("error"),
            },
            "provenance": {
                "generated_by": "WorldbuildingTraceCapture",
                "capture_point": "SimulationManager.prepare_simulation.after_config_saved",
                "simulation_dir": cls._relpath(simulation_dir, Config.UPLOAD_FOLDER),
                "config_snapshot": cls._build_config_snapshot(),
                "backtesting_context": project_metadata,
            },
            "artifact_manifest": {},
            "training_labels": None,
        }

    @classmethod
    def _build_source_file_snapshot(cls, project: Any) -> List[Dict[str, Any]]:
        if not project:
            return []

        files = []
        for file_info in getattr(project, "files", []) or []:
            path = file_info.get("path", "")
            files.append({
                "original_filename": file_info.get("original_filename"),
                "saved_filename": file_info.get("saved_filename"),
                "path": cls._relpath(path, Config.UPLOAD_FOLDER) if path else None,
                "size_bytes": file_info.get("size") or cls._safe_file_size(path),
                "sha256": cls._sha256_file(path) if path and os.path.exists(path) else None,
                "included": True,
            })
        return files

    @classmethod
    def _build_artifact_manifest(cls, simulation_dir: str) -> Dict[str, Any]:
        artifacts = []
        if os.path.isdir(simulation_dir):
            for root, _dirs, files in os.walk(simulation_dir):
                for filename in sorted(files):
                    path = os.path.join(root, filename)
                    relpath = cls._relpath(path, simulation_dir)
                    if relpath == cls.TRACE_FILENAME:
                        artifacts.append({
                            "path": relpath,
                            "size_bytes": None,
                            "sha256": None,
                            "self_reference": True,
                        })
                        continue

                    artifacts.append({
                        "path": relpath,
                        "size_bytes": cls._safe_file_size(path),
                        "sha256": cls._sha256_file(path),
                    })

        artifacts.sort(key=lambda item: item["path"])
        return {
            "base_dir": cls._relpath(simulation_dir, Config.UPLOAD_FOLDER),
            "artifacts": artifacts,
        }

    @classmethod
    def _build_excluded_file_snapshot(cls, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        excluded = []
        for item in metadata.get("excluded_files", []) or []:
            if isinstance(item, dict):
                excluded.append(item)
            else:
                excluded.append({"path": str(item), "reason": "excluded_by_case_config"})
        return excluded

    @classmethod
    def _build_expected_output_files(cls, simulation_dir: str, filenames: List[str]) -> List[Dict[str, Any]]:
        outputs = []
        for filename in filenames:
            path = os.path.join(simulation_dir, filename)
            if not os.path.exists(path):
                continue
            outputs.append({
                "path": cls._relpath(path, simulation_dir),
                "sha256": cls._sha256_file(path),
                "size_bytes": cls._safe_file_size(path),
            })
        return outputs

    @classmethod
    def _build_config_snapshot(cls) -> Dict[str, Any]:
        return {
            "llm_model": Config.LLM_MODEL_NAME,
            "llm_base_url": Config.LLM_BASE_URL,
            "llm_api_key_set": bool(Config.LLM_API_KEY),
            "graph_backend": Config.GRAPH_BACKEND,
            "graph_search_reranker": Config.GRAPH_SEARCH_RERANKER,
            "graph_search_app_reranker": Config.GRAPH_SEARCH_APP_RERANKER,
            "zep_mode": Config.ZEP_MODE,
            "zep_base_url": Config.ZEP_BASE_URL,
            "zep_api_key_set": bool(Config.ZEP_API_KEY),
            "graphiti_uri": Config.GRAPHITI_URI,
            "graphiti_database": Config.GRAPHITI_DATABASE,
            "graphiti_user_set": bool(Config.GRAPHITI_USER),
            "graphiti_password_set": bool(Config.GRAPHITI_PASSWORD),
            "graphiti_llm_model": Config.GRAPHITI_LLM_MODEL,
            "graphiti_llm_base_url": Config.GRAPHITI_LLM_BASE_URL,
            "graphiti_llm_client_mode": Config.GRAPHITI_LLM_CLIENT_MODE,
            "graphiti_embedder_model": Config.GRAPHITI_EMBEDDER_MODEL,
            "graphiti_embedder_base_url": Config.GRAPHITI_EMBEDDER_BASE_URL,
            "graphiti_max_coroutines": Config.GRAPHITI_MAX_COROUTINES,
            "use_experimental_memory": Config.USE_EXPERIMENTAL_MEMORY,
            "oasis_default_max_rounds": Config.OASIS_DEFAULT_MAX_ROUNDS,
        }

    @classmethod
    def _to_plain_dict(cls, value: Any) -> Any:
        if hasattr(value, "to_dict") and callable(value.to_dict):
            return cls._to_plain_dict(value.to_dict())
        if is_dataclass(value):
            return cls._to_plain_dict(asdict(value))
        if isinstance(value, dict):
            return {str(k): cls._to_plain_dict(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [cls._to_plain_dict(item) for item in value]
        if hasattr(value, "value"):
            return value.value
        return value

    @staticmethod
    def _write_json(path: str, payload: Dict[str, Any]) -> None:
        temp_path = f"{path}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(temp_path, path)

    @staticmethod
    def _sha256_text(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _sha256_file(path: str) -> Optional[str]:
        try:
            digest = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        except OSError:
            return None

    @staticmethod
    def _safe_file_size(path: str) -> Optional[int]:
        try:
            return os.path.getsize(path)
        except OSError:
            return None

    @staticmethod
    def _relpath(path: str, base: str) -> str:
        try:
            return os.path.relpath(path, base)
        except ValueError:
            return path
