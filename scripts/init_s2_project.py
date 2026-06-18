import os
import sys
import json
import shutil
import uuid
import time
from pathlib import Path
from datetime import datetime

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "backend"))

# Load env before imports
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# CRITICAL: Force environment for Graphiti/Neo4j
api_key = os.environ.get("OPENROUTER_API_KEY")
os.environ["OPENAI_API_KEY"] = api_key
os.environ["LLM_API_KEY"] = api_key
os.environ["LLM_BASE_URL"] = "https://openrouter.ai/api/v1"
os.environ["LLM_MODEL_NAME"] = "google/gemini-2.5-flash"
# Embedding settings
os.environ["GRAPHITI_EMBEDDER_API_KEY"] = api_key
os.environ["GRAPHITI_EMBEDDER_BASE_URL"] = "https://openrouter.ai/api/v1"
os.environ["GRAPHITI_EMBEDDER_MODEL"] = "openai/text-embedding-3-small"
os.environ["GRAPHITI_EMBEDDER_DIM"] = "1536"

from app.config import Config
from app.models.project import Project, ProjectManager, ProjectStatus
from app.services.graph_builder import GraphBuilderService
from app.services.ontology_generator import OntologyGenerator
from app.models.task import TaskStatus

def init_s2_project_with_graph():
    print("=== MiroFish S2 Project Initialization & Graph Build ===")
    
    # 1. Targeted Project Info
    target_project_id = "proj_arg_ipc_2025"
    case_source_dir = PROJECT_ROOT / "cases" / "CASE-B2-ARG-IPC-2025" / "input_pack_pre_x" / "sources"
    master_text_path = PROJECT_ROOT / "extracted_text.txt"
    
    if not case_source_dir.exists():
        print(f"Error: Source case directory not found at {case_source_dir}")
        return

    # 2. Ensure Directories
    projects_dir = Path(Config.UPLOAD_FOLDER) / "projects"
    project_path = projects_dir / target_project_id
    files_dir = project_path / "files"
    os.makedirs(files_dir, exist_ok=True)

    # 3. Create Project Metadata
    now = datetime.now().isoformat()
    project = Project(
        project_id=target_project_id,
        name="Argentina IPC Inflation 2024-2025 Case",
        status=ProjectStatus.CREATED,
        created_at=now,
        updated_at=now,
        files=[],
        simulation_requirement="Análisis cuantitativo de la inflación IPC en Argentina para el periodo 2024-2025."
    )

    # 4. Copy Case Files
    print(f"Copying files from {case_source_dir}...")
    for file_path in case_source_dir.iterdir():
        if file_path.is_file():
            dest_path = files_dir / file_path.name
            shutil.copy2(file_path, dest_path)
            project.files.append({
                "id": f"file_{uuid.uuid4().hex[:8]}",
                "name": file_path.name,
                "size": file_path.stat().st_size,
                "type": file_path.suffix[1:],
                "uploaded_at": now
            })
    
    # 5. Load Master Text
    if not master_text_path.exists():
        print(f"Error: Master text file {master_text_path} not found.")
        return
        
    with open(master_text_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Save text to project directory
    with open(project_path / "extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(text)
    
    # 6. Build Graph (The "Billed" part)
    print("\n>>> Starting Inferencia Preparatoria (Graph Population)...")
    
    # Generate Ontology
    print("Generating ontology...")
    ont_gen = OntologyGenerator()
    ontology = ont_gen.generate(
        document_texts=[text[:15000]], 
        simulation_requirement=project.simulation_requirement
    )
    print(f"Ontology generated with {len(ontology.get('entity_types', []))} entity types.")
    
    # Build Graph
    builder = GraphBuilderService()
    task_id = builder.build_graph_async(
        text=text,
        ontology=ontology,
        graph_name=f"Graph {target_project_id}"
    )
    
    print(f"Task ID: {task_id}. Polling for completion...")
    while True:
        task = builder.task_manager.get_task(task_id)
        if task.status == TaskStatus.COMPLETED:
            print("\n[SUCCESS] Knowledge Graph built in Neo4j.")
            project.status = ProjectStatus.GRAPH_COMPLETED
            break
        elif task.status == TaskStatus.FAILED:
            print(f"\n[FAILED] Graph construction error: {task.error}")
            return
        
        print(f"  Progress: {task.progress}% - {task.message}...", end="\r")
        time.sleep(15)

    # 7. Save Metadata
    with open(project_path / "project.json", "w", encoding="utf-8") as f:
        json.dump(project.to_dict(), f, indent=2, ensure_ascii=False)
    
    print(f"Project {target_project_id} fully initialized and populated.")

if __name__ == "__main__":
    init_s2_project_with_graph()
