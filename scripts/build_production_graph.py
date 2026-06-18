import sys
import os
import time
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "backend"))

# Load env before imports
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Force credentials and URL
api_key = os.environ.get("OPENROUTER_API_KEY")
os.environ["OPENAI_API_KEY"] = api_key
os.environ["LLM_API_KEY"] = api_key
os.environ["LLM_BASE_URL"] = "https://openrouter.ai/api/v1"
os.environ["LLM_MODEL_NAME"] = "qwen/qwen3-8b"

from app.services.graph_builder import GraphBuilderService
from app.services.ontology_generator import OntologyGenerator
from app.models.project import ProjectManager
from app.models.task import TaskStatus
from app.config import Config

def build_production_graph():
    project_id = "proj_arg_ipc_2025"
    print(f"=== Starting Production Graph Build for {project_id} ===")
    
    # 1. Prepare Text
    project = ProjectManager.get_project(project_id)
    text = ProjectManager.get_extracted_text(project_id)
    if not text:
        print("Error: No text found for project.")
        return
    
    requirement = project.simulation_requirement or "Análisis cuantitativo de la inflación IPC en Argentina para el periodo 2024-2025."
    
    # 2. Generate Ontology
    print("Generating ontology (identifying entity types)...")
    ont_gen = OntologyGenerator()
    # Correct signature: (document_texts: List[str], simulation_requirement: str, ...)
    ontology = ont_gen.generate(
        document_texts=[text[:15000]], 
        simulation_requirement=requirement
    )
    print(f"Ontology generated. Found {len(ontology.get('entity_types', []))} entity types.")
    
    # 3. Build Graph
    print("Beginning asynchronous graph construction...")
    builder = GraphBuilderService()
    task_id = builder.build_graph_async(
        text=text,
        ontology=ontology,
        graph_name=f"Graph {project_id}"
    )
    
    print(f"Task ID: {task_id}. Polling for completion...")
    
    # 4. Wait for completion
    while True:
        task = builder.task_manager.get_task(task_id)
        if task.status == TaskStatus.COMPLETED:
            print("\n[SUCCESS] Knowledge Graph built in Neo4j.")
            # Update project status
            project.status = "graph_completed"
            ProjectManager.save_project(project)
            break
        elif task.status == TaskStatus.FAILED:
            print(f"\n[FAILED] Graph construction error: {task.error}")
            break
        
        print(f"  Progress: {task.progress}% - {task.message}...", end="\r")
        time.sleep(20)

if __name__ == "__main__":
    build_production_graph()
