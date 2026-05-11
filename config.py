"""
Configuration Management for Mother-Agent System
Centralizes all system configuration and environment variables
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path
import json


@dataclass
class MotherConfig:
    """Mother Agent configuration"""
    api_key: str
    model: str = "claude-sonnet-4-20250514"
    timeout_seconds: int = 300
    max_retries: int = 3
    max_parallel_agents: int = 4
    health_check_interval: float = 0.2
    ghost_mcp_tick_interval: float = 0.05
    
    @classmethod
    def from_env(cls):
        """Load configuration from environment variables"""
        return cls(
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            timeout_seconds=int(os.getenv("TIMEOUT_SECONDS", "300")),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            max_parallel_agents=int(os.getenv("MAX_PARALLEL_AGENTS", "4")),
            health_check_interval=float(os.getenv("HEALTH_CHECK_INTERVAL", "0.2")),
            ghost_mcp_tick_interval=float(os.getenv("GHOST_MCP_TICK", "0.05"))
        )


@dataclass
class MCPConfig:
    """MCP Server configuration"""
    ghost_mcp_host: str = "0.0.0.0"
    ghost_mcp_port: int = 8000
    inter_agent_mcp_host: str = "0.0.0.0"
    inter_agent_mcp_port: int = 8001
    
    @classmethod
    def from_env(cls):
        """Load MCP configuration from environment"""
        return cls(
            ghost_mcp_host=os.getenv("GHOST_MCP_HOST", "0.0.0.0"),
            ghost_mcp_port=int(os.getenv("GHOST_MCP_PORT", "8000")),
            inter_agent_mcp_host=os.getenv("INTER_AGENT_MCP_HOST", "0.0.0.0"),
            inter_agent_mcp_port=int(os.getenv("INTER_AGENT_MCP_PORT", "8001"))
        )


@dataclass
class WorkspaceConfig:
    """Workspace and output configuration"""
    working_folder: str
    output_format: str = "tar.gz"
    preserve_temp_files: bool = False
    
    @classmethod
    def from_env(cls):
        """Load workspace configuration from environment"""
        return cls(
            working_folder=os.getenv("WORKING_FOLDER", "/tmp/multi_agent_output"),
            output_format=os.getenv("OUTPUT_FORMAT", "tar.gz"),
            preserve_temp_files=os.getenv("PRESERVE_TEMP_FILES", "false").lower() == "true"
        )


@dataclass
class RoleConfig:
    """Agent role definitions and templates"""
    role_name: str
    expertise: str
    tools: List[str]
    system_prompt_template: str
    file_patterns: List[str]  # File types this role typically works with


class RoleRegistry:
    """Registry of all available agent roles"""
    
    ROLES: Dict[str, RoleConfig] = {
        "backend": RoleConfig(
            role_name="Backend Developer",
            expertise="API design, database modeling, server-side logic, Python/Node.js/Go",
            tools=["file_operations", "code_execution", "inter_agent_mcp", "ghost_mcp"],
            system_prompt_template="""You are an expert backend developer.
Your strengths: RESTful APIs, database design, authentication, scalability.
You write clean, maintainable server-side code with proper error handling.""",
            file_patterns=["*.py", "*.js", "*.go", "*.java", "requirements.txt", "package.json"]
        ),
        
        "frontend": RoleConfig(
            role_name="Frontend Developer",
            expertise="React, Vue, Angular, TypeScript, responsive design, state management",
            tools=["file_operations", "code_execution", "inter_agent_mcp", "ghost_mcp"],
            system_prompt_template="""You are an expert frontend developer.
Your strengths: Modern frameworks (React/Vue), component architecture, UX implementation.
You create responsive, accessible, performant user interfaces.""",
            file_patterns=["*.jsx", "*.tsx", "*.vue", "*.html", "*.css", "*.scss", "package.json"]
        ),
        
        "ux_designer": RoleConfig(
            role_name="UX Designer",
            expertise="User research, wireframing, design systems, accessibility, Figma",
            tools=["file_operations", "design_tools", "inter_agent_mcp", "ghost_mcp"],
            system_prompt_template="""You are an expert UX designer.
Your strengths: User-centered design, information architecture, usability.
You create intuitive, accessible experiences backed by design principles.""",
            file_patterns=["*.fig", "*.sketch", "*.svg", "design-system.json"]
        ),
        
        "devops": RoleConfig(
            role_name="DevOps Engineer",
            expertise="Docker, Kubernetes, CI/CD, infrastructure as code, cloud platforms",
            tools=["file_operations", "deployment_tools", "inter_agent_mcp", "ghost_mcp"],
            system_prompt_template="""You are an expert DevOps engineer.
Your strengths: Container orchestration, automation, monitoring, scalability.
You build reliable, automated deployment pipelines and infrastructure.""",
            file_patterns=["Dockerfile", "docker-compose.yml", "*.tf", ".gitlab-ci.yml", ".github/workflows/*"]
        ),
        
        "qa": RoleConfig(
            role_name="QA Engineer",
            expertise="Test automation, quality assurance, test strategy, debugging",
            tools=["file_operations", "testing_tools", "inter_agent_mcp", "ghost_mcp"],
            system_prompt_template="""You are an expert QA engineer.
Your strengths: Test planning, automated testing, bug detection, quality metrics.
You ensure software quality through comprehensive testing strategies.""",
            file_patterns=["*test*.py", "*spec*.js", "*.test.tsx", "pytest.ini", "jest.config.js"]
        ),
        
        "supervisor": RoleConfig(
            role_name="Supervisor",
            expertise="Code review, functional testing, architecture validation, quality assurance",
            tools=["file_operations", "testing_tools", "inter_agent_mcp", "ghost_mcp"],
            system_prompt_template="""You are an expert Supervisor.
Your strengths: Work validation, code quality review, architectural consistency, test execution.
You ensure the overall quality and integration of the project by reviewing and validating agent outputs.""",
            file_patterns=["*"]
        ),
        
        "fullstack": RoleConfig(
            role_name="Full-Stack Developer",
            expertise="End-to-end development, both frontend and backend, database to UI",
            tools=["file_operations", "code_execution", "inter_agent_mcp", "ghost_mcp"],
            system_prompt_template="""You are an expert full-stack developer.
Your strengths: Complete application development, system integration, architecture.
You build complete features from database to user interface.""",
            file_patterns=["*.py", "*.js", "*.jsx", "*.tsx", "*.html", "*.css"]
        )
    }
    
    @classmethod
    def get_role(cls, role_key: str) -> Optional[RoleConfig]:
        """Get role configuration by key"""
        return cls.ROLES.get(role_key.lower())
    
    @classmethod
    def list_roles(cls) -> List[str]:
        """List all available roles"""
        return list(cls.ROLES.keys())


class ProjectTemplates:
    """Pre-defined project templates for common use cases"""
    
    TEMPLATES = {
        "web_app": {
            "name": "Web Application",
            "required_roles": ["backend", "frontend"],
            "optional_roles": ["ux_designer", "devops", "qa"],
            "tech_stack": {
                "backend": "Python Flask or FastAPI",
                "frontend": "React with TypeScript",
                "database": "SQLite or PostgreSQL"
            }
        },
        
        "api_service": {
            "name": "API Service",
            "required_roles": ["backend"],
            "optional_roles": ["devops", "qa"],
            "tech_stack": {
                "backend": "FastAPI or Express",
                "database": "PostgreSQL or MongoDB",
                "deployment": "Docker"
            }
        },
        
        "mobile_app": {
            "name": "Mobile Application",
            "required_roles": ["frontend", "backend"],
            "optional_roles": ["ux_designer", "qa"],
            "tech_stack": {
                "frontend": "React Native or Flutter",
                "backend": "Node.js or Python",
                "database": "Firebase or SQLite"
            }
        },
        
        "data_pipeline": {
            "name": "Data Pipeline",
            "required_roles": ["backend"],
            "optional_roles": ["devops", "qa"],
            "tech_stack": {
                "processing": "Python with pandas/polars",
                "orchestration": "Airflow or Prefect",
                "storage": "PostgreSQL or data lake"
            }
        }
    }
    
    @classmethod
    def get_template(cls, template_key: str) -> Optional[Dict]:
        """Get project template by key"""
        return cls.TEMPLATES.get(template_key)
    
    @classmethod
    def list_templates(cls) -> List[str]:
        """List all available templates"""
        return list(cls.TEMPLATES.keys())


class SystemConfig:
    """Main system configuration aggregator"""
    
    def __init__(self):
        self.mother = MotherConfig.from_env()
        self.mcp = MCPConfig.from_env()
        self.workspace = WorkspaceConfig.from_env()
        self.roles = RoleRegistry()
        self.templates = ProjectTemplates()
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        if not self.mother.api_key:
            issues.append("ANTHROPIC_API_KEY not set")
        
        if self.mother.timeout_seconds < 60:
            issues.append("TIMEOUT_SECONDS should be at least 60")
        
        if self.mother.max_retries < 1:
            issues.append("MAX_RETRIES should be at least 1")
        
        # Check if working folder is writable
        workspace_path = Path(self.workspace.working_folder)
        try:
            workspace_path.mkdir(parents=True, exist_ok=True)
            test_file = workspace_path / ".write_test"
            test_file.touch()
            test_file.unlink()
        except Exception as e:
            issues.append(f"Working folder not writable: {e}")
        
        return issues
    
    def to_dict(self) -> Dict:
        """Export configuration as dictionary"""
        return {
            "mother": {
                "model": self.mother.model,
                "timeout_seconds": self.mother.timeout_seconds,
                "max_retries": self.mother.max_retries,
                "max_parallel_agents": self.mother.max_parallel_agents
            },
            "mcp": {
                "ghost_mcp": f"{self.mcp.ghost_mcp_host}:{self.mcp.ghost_mcp_port}",
                "inter_agent_mcp": f"{self.mcp.inter_agent_mcp_host}:{self.mcp.inter_agent_mcp_port}"
            },
            "workspace": {
                "working_folder": self.workspace.working_folder,
                "output_format": self.workspace.output_format
            },
            "available_roles": self.roles.list_roles(),
            "available_templates": self.templates.list_templates()
        }
    
    def save(self, filepath: str):
        """Save configuration to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str):
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Set environment variables from loaded config
        if "mother" in data:
            os.environ["TIMEOUT_SECONDS"] = str(data["mother"]["timeout_seconds"])
            os.environ["MAX_RETRIES"] = str(data["mother"]["max_retries"])
        
        return cls()


def load_config() -> SystemConfig:
    """Load system configuration with validation"""
    config = SystemConfig()
    
    issues = config.validate()
    if issues:
        print("⚠️  Configuration Issues:")
        for issue in issues:
            print(f"   - {issue}")
    
    return config


if __name__ == "__main__":
    # Test configuration
    config = load_config()
    
    print("\n📋 System Configuration:")
    print(json.dumps(config.to_dict(), indent=2))
    
    print("\n✅ Configuration loaded successfully")
