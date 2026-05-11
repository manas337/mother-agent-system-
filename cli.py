#!/usr/bin/env python3
"""
Mother-Agent CLI - Command-line interface for the multi-agent system
Provides easy access to all system functionality
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional
import os

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mother_agent import MotherAgent
from config import load_config, SystemConfig
from output_packager import OutputPackager


class MotherAgentCLI:
    """Command-line interface for Mother-Agent system"""
    
    def __init__(self):
        self.config = load_config()
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser"""
        parser = argparse.ArgumentParser(
            description="Mother-Agent Multi-Agent Software Development System",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Create project from specification file
  python cli.py create --spec project_spec.txt --output ./my_project
  
  # Create project from inline specification
  python cli.py create --inline "Create a REST API for a blog"
  
  # List available roles
  python cli.py roles
  
  # List available templates
  python cli.py templates
  
  # Validate configuration
  python cli.py config --validate
  
  # Run demo
  python cli.py demo
            """
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Command to execute')
        
        # Create project command
        create_parser = subparsers.add_parser('create', help='Create a new project')
        create_parser.add_argument('--spec', type=str, help='Path to specification file')
        create_parser.add_argument('--inline', type=str, help='Inline specification text')
        create_parser.add_argument('--output', type=str, help='Output directory (default: from config)')
        create_parser.add_argument('--archive', action='store_true', help='Create tar.gz archive')
        create_parser.add_argument('--timeout', type=int, help='Timeout in seconds (default: 300)')
        create_parser.add_argument('--api-key', type=str, help='Anthropic API key (or use env var)')
        
        # Roles command
        subparsers.add_parser('roles', help='List available agent roles')
        
        # Templates command
        subparsers.add_parser('templates', help='List available project templates')
        
        # Config command
        config_parser = subparsers.add_parser('config', help='Configuration management')
        config_parser.add_argument('--show', action='store_true', help='Show current configuration')
        config_parser.add_argument('--validate', action='store_true', help='Validate configuration')
        config_parser.add_argument('--save', type=str, help='Save configuration to file')
        
        # Demo command
        subparsers.add_parser('demo', help='Run interactive demo')
        
        # Version command
        subparsers.add_parser('version', help='Show version information')
        
        return parser
    
    async def cmd_create(self, args):
        """Create a new project"""
        # Get specification
        if args.spec:
            spec_path = Path(args.spec)
            if not spec_path.exists():
                print(f"❌ Error: Specification file not found: {args.spec}")
                return 1
            with open(spec_path, 'r') as f:
                spec = f.read()
            print(f"📄 Loaded specification from {args.spec}")
        elif args.inline:
            spec = args.inline
            print(f"📝 Using inline specification")
        else:
            print("❌ Error: Must provide either --spec or --inline")
            return 1
        
        # Get API key
        api_key = args.api_key or self.config.mother.api_key
        if not api_key:
            print("❌ Error: No API key provided. Set ANTHROPIC_API_KEY or use --api-key")
            return 1
        
        # Get output directory
        output_dir = args.output or self.config.workspace.working_folder
        
        # Get timeout
        timeout = args.timeout or self.config.mother.timeout_seconds
        
        print("\n" + "="*80)
        print("🧠 MOTHER-AGENT SYSTEM")
        print("="*80 + "\n")
        
        # Initialize Mother Agent
        mother = MotherAgent(
            api_key=api_key,
            working_folder=output_dir,
            timeout_seconds=timeout
        )
        
        # Run Mother Agent
        result = await mother.run(spec)
        
        if result["status"] == "success":
            print("\n" + "="*80)
            print("✅ PROJECT COMPLETED SUCCESSFULLY")
            print("="*80 + "\n")
            
            print(f"⏱️  Execution Time: {result['execution_time']:.2f} seconds")
            print(f"✔️  Tasks Completed: {result['tasks_completed']}/{result['total_tasks']}")
            
            # Package output if requested
            if args.archive and result.get("output"):
                print("\n📦 Packaging output...")
                packager = OutputPackager(output_dir)
                
                # Extract files from output
                output_data = result["output"]
                files = output_data.get("files", {})
                readme = output_data.get("readme", "# Project\n\nGenerated by Mother-Agent")
                
                if files:
                    package_result = packager.package_project(
                        project_name="generated_project",
                        files=files,
                        readme_content=readme,
                        metadata={
                            "execution_time": result["execution_time"],
                            "tasks_completed": result["tasks_completed"],
                            "total_tasks": result["total_tasks"]
                        },
                        create_archive=True
                    )
                    
                    print(f"✅ Archive created: {package_result['archive']}")
                    print(f"🔐 Checksum: {package_result['checksum']}")
            
            return 0
        else:
            print("\n" + "="*80)
            print("❌ PROJECT FAILED")
            print("="*80 + "\n")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return 1
    
    def cmd_roles(self, args):
        """List available agent roles"""
        print("\n📋 Available Agent Roles:")
        print("="*80 + "\n")
        
        for role_key in self.config.roles.list_roles():
            role = self.config.roles.get_role(role_key)
            print(f"🤖 {role.role_name} ({role_key})")
            print(f"   Expertise: {role.expertise}")
            print(f"   Tools: {', '.join(role.tools)}")
            print(f"   File Types: {', '.join(role.file_patterns)}")
            print()
        
        return 0
    
    def cmd_templates(self, args):
        """List available project templates"""
        print("\n📋 Available Project Templates:")
        print("="*80 + "\n")
        
        for template_key in self.config.templates.list_templates():
            template = self.config.templates.get_template(template_key)
            print(f"📦 {template['name']} ({template_key})")
            print(f"   Required Roles: {', '.join(template['required_roles'])}")
            if template['optional_roles']:
                print(f"   Optional Roles: {', '.join(template['optional_roles'])}")
            print(f"   Tech Stack:")
            for key, value in template['tech_stack'].items():
                print(f"      - {key}: {value}")
            print()
        
        return 0
    
    def cmd_config(self, args):
        """Configuration management"""
        if args.show or (not args.validate and not args.save):
            print("\n⚙️  Current Configuration:")
            print("="*80 + "\n")
            print(json.dumps(self.config.to_dict(), indent=2))
            print()
        
        if args.validate:
            print("\n🔍 Validating Configuration...")
            issues = self.config.validate()
            
            if not issues:
                print("✅ Configuration is valid!")
            else:
                print("⚠️  Configuration Issues Found:")
                for issue in issues:
                    print(f"   - {issue}")
                return 1
        
        if args.save:
            print(f"\n💾 Saving configuration to {args.save}...")
            self.config.save(args.save)
            print("✅ Configuration saved!")
        
        return 0
    
    async def cmd_demo(self, args):
        """Run interactive demo"""
        print("\n" + "="*80)
        print("🎮 INTERACTIVE DEMO")
        print("="*80 + "\n")
        
        print("Choose a demo scenario:")
        print("1. Simple Web Application (Backend + Frontend)")
        print("2. REST API Service (Backend only)")
        print("3. Custom Specification")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            spec = """
Create a simple task management web application with:

Backend:
- Python Flask REST API
- SQLite database
- CRUD operations for tasks (title, description, completed status)

Frontend:
- React application
- Task list with add/edit/delete
- Mark tasks as complete
- Basic CSS styling
"""
            print("\n📝 Using Web Application template")
        
        elif choice == "2":
            spec = """
Create a weather API service with:

Backend:
- FastAPI framework
- Endpoint: GET /weather/{city}
- Returns mock weather data (temperature, conditions, humidity)
- OpenAPI documentation
- Basic error handling
"""
            print("\n📝 Using API Service template")
        
        elif choice == "3":
            spec = input("\nEnter your project specification:\n")
        
        else:
            print("Exiting demo...")
            return 0
        
        # Get API key
        api_key = input("\nEnter your Anthropic API key (or press Enter to use env var): ").strip()
        if not api_key:
            api_key = self.config.mother.api_key
        
        if not api_key:
            print("❌ No API key available")
            return 1
        
        # Create temporary args object
        class DemoArgs:
            inline = spec
            spec_file = None
            output = "/tmp/mother_agent_demo"
            archive = True
            timeout = 300
            api_key = api_key
        
        return await self.cmd_create(DemoArgs())
    
    def cmd_version(self, args):
        """Show version information"""
        print("\n" + "="*80)
        print("MOTHER-AGENT SYSTEM")
        print("="*80 + "\n")
        print("Version: 0.1.0 (V0)")
        print("Model: Claude Sonnet 4")
        print("Author: Multi-Agent Architecture")
        print("\nComponents:")
        print("  - Mother Agent: Orchestrator")
        print("  - Ghost MCP: Health Monitor")
        print("  - Inter-Agent MCP: Collaboration Server")
        print("  - Sub-Agents: Specialized Workers")
        print()
        return 0
    
    async def run(self, argv=None):
        """Run CLI"""
        args = self.parser.parse_args(argv)
        
        if not args.command:
            self.parser.print_help()
            return 0
        
        # Execute command
        if args.command == 'create':
            return await self.cmd_create(args)
        elif args.command == 'roles':
            return self.cmd_roles(args)
        elif args.command == 'templates':
            return self.cmd_templates(args)
        elif args.command == 'config':
            return self.cmd_config(args)
        elif args.command == 'demo':
            return await self.cmd_demo(args)
        elif args.command == 'version':
            return self.cmd_version(args)
        else:
            self.parser.print_help()
            return 1


def main():
    """Main entry point"""
    cli = MotherAgentCLI()
    
    try:
        exit_code = asyncio.run(cli.run())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
