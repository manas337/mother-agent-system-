"""
Output Packager - Creates deliverable tar.gz packages
Organizes project files and creates standardized output structure
"""

import os
import tarfile
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import hashlib


class OutputPackager:
    """
    Packages agent outputs into deliverable tar.gz archives
    Following the specified output structure
    """
    
    def __init__(self, working_folder: str):
        self.working_folder = Path(working_folder)
        self.working_folder.mkdir(parents=True, exist_ok=True)
    
    def create_project_structure(
        self,
        project_name: str,
        files: Dict[str, str],
        readme_content: str,
        metadata: Optional[Dict] = None
    ) -> Path:
        """
        Create standardized project structure
        
        Args:
            project_name: Name of the project
            files: Dictionary of file_path: content
            readme_content: README.md content
            metadata: Additional metadata about the project
            
        Returns:
            Path to created project directory
        """
        # Create project directory
        project_dir = self.working_folder / project_name
        project_dir.mkdir(exist_ok=True)
        
        # Organize files by directory
        organized_files = self._organize_files(files)
        
        # Create directory structure
        for filepath, content in organized_files.items():
            full_path = project_dir / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Create README.md
        readme_path = project_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        # Create metadata file
        if metadata:
            metadata_path = project_dir / ".mother_agent_metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
        
        # Create .gitignore
        gitignore_path = project_dir / ".gitignore"
        with open(gitignore_path, 'w') as f:
            f.write(self._generate_gitignore())
        
        return project_dir
    
    def _organize_files(self, files: Dict[str, str]) -> Dict[str, str]:
        """
        Organize files into proper directory structure
        
        Standard structure:
        ├── src/
        │   ├── backend/
        │   ├── frontend/
        │   └── shared/
        ├── config/
        ├── tests/
        └── docs/
        """
        organized = {}
        
        for filepath, content in files.items():
            # Determine proper location
            if filepath.startswith('src/') or filepath.startswith('config/') or filepath.startswith('tests/'):
                # Already organized
                organized[filepath] = content
            else:
                # Categorize based on file type and content
                new_path = self._categorize_file(filepath, content)
                organized[new_path] = content
        
        return organized
    
    def _categorize_file(self, filepath: str, content: str) -> str:
        """Categorize file into appropriate directory"""
        filename = Path(filepath).name
        
        # Backend files
        if any(ext in filename for ext in ['.py', 'requirements.txt', 'Pipfile']):
            if 'test' in filename.lower():
                return f"tests/{filename}"
            return f"src/backend/{filename}"
        
        # Frontend files
        if any(ext in filename for ext in ['.jsx', '.tsx', '.vue', 'package.json']):
            if 'test' in filename.lower() or 'spec' in filename.lower():
                return f"tests/{filename}"
            return f"src/frontend/{filename}"
        
        # Config files
        if any(name in filename for name in ['Dockerfile', 'docker-compose', '.env', 'config']):
            return f"config/{filename}"
        
        # Test files
        if 'test' in filename.lower() or 'spec' in filename.lower():
            return f"tests/{filename}"
        
        # Shared/common files
        if filename in ['package.json', 'tsconfig.json', '.eslintrc']:
            return filename
        
        # Default to src/shared
        return f"src/shared/{filename}"
    
    def _generate_gitignore(self) -> str:
        """Generate standard .gitignore"""
        return """# Mother-Agent Generated Project

# Dependencies
node_modules/
venv/
env/
__pycache__/
*.pyc
.Python

# Build outputs
dist/
build/
*.egg-info/

# Environment
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Testing
.coverage
htmlcov/
.pytest_cache/

# Mother Agent metadata
.mother_agent_metadata.json
"""
    
    def create_tarball(
        self,
        project_dir: Path,
        output_name: Optional[str] = None
    ) -> Path:
        """
        Create tar.gz archive of project
        
        Args:
            project_dir: Directory to archive
            output_name: Optional custom name for archive
            
        Returns:
            Path to created tar.gz file
        """
        if not output_name:
            output_name = f"{project_dir.name}.tar.gz"
        
        tarball_path = self.working_folder / output_name
        
        with tarfile.open(tarball_path, 'w:gz') as tar:
            tar.add(project_dir, arcname=project_dir.name)
        
        return tarball_path
    
    def package_project(
        self,
        project_name: str,
        files: Dict[str, str],
        readme_content: str,
        metadata: Optional[Dict] = None,
        create_archive: bool = True
    ) -> Dict[str, Path]:
        """
        Complete packaging workflow
        
        Returns:
            Dictionary with 'directory' and optionally 'archive' paths
        """
        # Create project structure
        project_dir = self.create_project_structure(
            project_name=project_name,
            files=files,
            readme_content=readme_content,
            metadata=metadata
        )
        
        result = {"directory": project_dir}
        
        # Create archive if requested
        if create_archive:
            tarball_path = self.create_tarball(project_dir)
            result["archive"] = tarball_path
            
            # Calculate checksum
            checksum = self._calculate_checksum(tarball_path)
            result["checksum"] = checksum
            
            # Save checksum file
            checksum_file = tarball_path.with_suffix('.tar.gz.sha256')
            with open(checksum_file, 'w') as f:
                f.write(f"{checksum}  {tarball_path.name}\n")
            result["checksum_file"] = checksum_file
        
        return result
    
    def _calculate_checksum(self, filepath: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def generate_project_report(
        self,
        project_name: str,
        files: Dict[str, str],
        execution_time: float,
        agents_used: List[Dict],
        tasks_completed: int,
        total_tasks: int
    ) -> str:
        """Generate comprehensive project report"""
        
        # Count lines of code
        total_lines = sum(len(content.split('\n')) for content in files.values())
        
        # Categorize files
        file_types = {}
        for filepath in files.keys():
            ext = Path(filepath).suffix or 'no_extension'
            file_types[ext] = file_types.get(ext, 0) + 1
        
        report = f"""# {project_name} - Project Report

**Generated by Mother-Agent System**  
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Executive Summary

This project was automatically generated by the Mother-Agent multi-agent system in **{execution_time:.2f} seconds**.

- **Tasks Completed:** {tasks_completed}/{total_tasks}
- **Agents Used:** {len(agents_used)}
- **Total Files:** {len(files)}
- **Total Lines of Code:** {total_lines:,}
- **Success Rate:** {(tasks_completed/total_tasks*100):.1f}%

---

## Project Structure

```
{project_name}/
├── README.md
├── src/
│   ├── backend/
│   ├── frontend/
│   └── shared/
├── config/
├── tests/
└── docs/
```

---

## File Breakdown

| File Type | Count |
|-----------|-------|
"""
        
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            report += f"| {ext} | {count} |\n"
        
        report += f"""
---

## Agent Contributions

"""
        
        for agent in agents_used:
            report += f"""
### {agent.get('role', 'Unknown Role')}
- **Agent ID:** `{agent.get('agent_id', 'N/A')}`
- **Task:** {agent.get('task', 'N/A')}
- **Status:** {agent.get('status', 'N/A')}
- **Files Created:** {agent.get('files_created', 0)}
"""
        
        report += f"""
---

## Build Instructions

### Prerequisites
- Python 3.9+ (for backend)
- Node.js 18+ (for frontend)
- Docker (optional, for containerized deployment)

### Setup

1. **Install Backend Dependencies**
   ```bash
   cd src/backend
   pip install -r requirements.txt
   ```

2. **Install Frontend Dependencies**
   ```bash
   cd src/frontend
   npm install
   ```

3. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Running Locally

**Backend:**
```bash
cd src/backend
python app.py
```

**Frontend:**
```bash
cd src/frontend
npm start
```

### Testing

```bash
# Backend tests
pytest tests/

# Frontend tests
npm test
```

---

## Next Steps

1. Review generated code for business logic
2. Customize configuration in `config/`
3. Add additional tests in `tests/`
4. Set up CI/CD pipeline
5. Deploy to production

---

## Notes

This project was automatically generated. While the Mother-Agent system strives for high quality, 
please review all code before deploying to production.

**Execution Time:** {execution_time:.2f}s  
**System Version:** V0.1.0
"""
        
        return report
    
    def cleanup(self, keep_archives: bool = True):
        """Clean up working folder"""
        if keep_archives:
            # Keep .tar.gz files, remove directories
            for item in self.working_folder.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
        else:
            # Remove everything
            shutil.rmtree(self.working_folder)
            self.working_folder.mkdir(parents=True)


def example_usage():
    """Example of using the OutputPackager"""
    
    packager = OutputPackager("/tmp/mother_agent_output")
    
    # Example files from agents
    files = {
        "app.py": """from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    return jsonify({"tasks": []})

if __name__ == '__main__':
    app.run(debug=True)
""",
        "requirements.txt": """Flask==3.0.0
SQLAlchemy==2.0.23
""",
        "App.jsx": """import React from 'react';

function App() {
    return <div>Task Manager</div>;
}

export default App;
""",
        "package.json": """{"name": "task-manager", "version": "1.0.0"}"""
    }
    
    readme = """# Task Manager

A simple task management application.

## Features
- Create tasks
- Mark as complete
- Delete tasks
"""
    
    metadata = {
        "generated_by": "Mother-Agent v0.1",
        "timestamp": datetime.now().isoformat(),
        "agents_used": ["backend", "frontend"],
        "execution_time": 45.2
    }
    
    # Package project
    result = packager.package_project(
        project_name="task_manager",
        files=files,
        readme_content=readme,
        metadata=metadata,
        create_archive=True
    )
    
    print(f"✅ Project packaged:")
    print(f"   Directory: {result['directory']}")
    print(f"   Archive: {result['archive']}")
    print(f"   Checksum: {result['checksum']}")
    
    # Generate report
    report = packager.generate_project_report(
        project_name="task_manager",
        files=files,
        execution_time=45.2,
        agents_used=[
            {"agent_id": "agent_001", "role": "Backend", "task": "Create API", "status": "completed", "files_created": 2},
            {"agent_id": "agent_002", "role": "Frontend", "task": "Create UI", "status": "completed", "files_created": 2}
        ],
        tasks_completed=2,
        total_tasks=2
    )
    
    print("\n📄 Project Report:")
    print(report[:500] + "...")


if __name__ == "__main__":
    example_usage()
