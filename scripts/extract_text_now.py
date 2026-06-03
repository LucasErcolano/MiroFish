import sys
import os
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "backend"))

# Load env before imports
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from app.models.project import ProjectManager
from app.utils.file_parser import FileParser

def extract_and_save_project_text():
    project_id = "proj_arg_ipc_2025"
    print(f"=== Extracting Text for Project {project_id} ===")
    
    files = ProjectManager.get_project_files(project_id)
    if not files:
        print("Error: No files found in project upload folder.")
        return False
        
    print(f"Found {len(files)} files. Parsing...")
    
    supported_files = []
    for f in files:
        if any(f.endswith(ext) for ext in ['.pdf', '.md', '.markdown', '.txt', '.html']):
            supported_files.append(f)
            
    if not supported_files:
        print("Error: No supported files for text extraction.")
        return False

    # Extract
    text = FileParser.extract_from_multiple(supported_files)
    
    # Save to file system
    text_path = ProjectManager._get_project_text_path(project_id)
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text)
        
    print(f"Extraction complete. Saved to {text_path} ({len(text)} chars).")
    return True

if __name__ == "__main__":
    extract_and_save_project_text()
