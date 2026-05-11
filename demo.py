"""
Complete Demo of Mother-Agent Multi-Agent System
Demonstrates the full workflow from user spec to consolidated output
"""

import asyncio
import json
import os
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mother_agent import MotherAgent, AgentRole, TaskStatus
import subprocess
import time


class MultiAgentSystemDemo:
    """
    Demonstration of the complete multi-agent system
    Shows Mother creating agents, monitoring them, and consolidating outputs
    """
    
    def __init__(self):
        self.ghost_mcp_process = None
        self.inter_agent_mcp_process = None
        
    async def start_mcp_servers(self):
        """Start the Ghost MCP and Inter-Agent MCP servers"""
        print("🚀 Starting MCP servers...")
        
        # Start Ghost MCP (port 8000)
        self.ghost_mcp_process = subprocess.Popen(
            [sys.executable, "ghost_mcp.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Start Inter-Agent MCP (port 8001)
        self.inter_agent_mcp_process = subprocess.Popen(
            [sys.executable, "inter_agent_mcp.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for servers to start
        await asyncio.sleep(2)
        print("✅ MCP servers running")
        
    def stop_mcp_servers(self):
        """Stop MCP servers"""
        print("\n🛑 Stopping MCP servers...")
        if self.ghost_mcp_process:
            self.ghost_mcp_process.terminate()
        if self.inter_agent_mcp_process:
            self.inter_agent_mcp_process.terminate()
        print("✅ MCP servers stopped")
        
    async def run_demo(self, api_key: str):
        """Run complete demo"""
        
        print("\n" + "="*80)
        print("MOTHER-AGENT MULTI-AGENT SYSTEM DEMO")
        print("="*80 + "\n")
        
        # Create working directory
        working_folder = "/tmp/multi_agent_demo"
        os.makedirs(working_folder, exist_ok=True)
        
        # Example 1: Simple Task Management App
        print("\n📝 DEMO 1: Task Management Web Application")
        print("-" * 80)
        
        spec_1 = """
        Create a task management web application with:
        
        Backend Requirements:
        - REST API using Python Flask
        - SQLite database for task storage
        - Endpoints: GET /tasks, POST /tasks, DELETE /tasks/{id}, PUT /tasks/{id}
        - Task model: id, title, description, completed (boolean), created_at
        
        Frontend Requirements:
        - React single-page application
        - Task list view with add/edit/delete functionality
        - Mark tasks as complete
        - Responsive design
        
        Additional:
        - Basic CSS styling
        - README with setup instructions
        """
        
        mother = MotherAgent(
            api_key=api_key,
            working_folder=working_folder,
            timeout_seconds=300
        )
        
        result_1 = await mother.run(spec_1)
        
        print("\n" + "="*80)
        print("DEMO 1 RESULTS")
        print("="*80)
        print(json.dumps({
            "status": result_1["status"],
            "execution_time": f"{result_1.get('execution_time', 0):.2f}s",
            "tasks_completed": result_1.get("tasks_completed", 0),
            "total_tasks": result_1.get("total_tasks", 0)
        }, indent=2))
        
        # Example 2: API Service
        print("\n\n📝 DEMO 2: Weather API Service")
        print("-" * 80)
        
        spec_2 = """
        Create a simple weather API service:
        
        Requirements:
        - Python FastAPI backend
        - Endpoint: GET /weather/{city}
        - Returns mock weather data (temp, conditions, humidity)
        - OpenAPI documentation
        - Docker configuration for deployment
        - Unit tests
        """
        
        mother_2 = MotherAgent(
            api_key=api_key,
            working_folder=working_folder + "_demo2",
            timeout_seconds=300
        )
        
        result_2 = await mother_2.run(spec_2)
        
        print("\n" + "="*80)
        print("DEMO 2 RESULTS")
        print("="*80)
        print(json.dumps({
            "status": result_2["status"],
            "execution_time": f"{result_2.get('execution_time', 0):.2f}s",
            "tasks_completed": result_2.get("tasks_completed", 0),
            "total_tasks": result_2.get("total_tasks", 0)
        }, indent=2))
        
        print("\n" + "="*80)
        print("DEMO COMPLETE")
        print("="*80)
        print("\nKey Achievements:")
        print("✅ Mother validated and decomposed project specs")
        print("✅ Created specialized agents with non-overlapping roles")
        print("✅ Agents executed tasks autonomously")
        print("✅ Ghost MCP monitored agent health")
        print("✅ Inter-Agent MCP facilitated collaboration")
        print("✅ Mother consolidated outputs into deliverables")
        print("✅ All agents destroyed after completion")
        

async def quick_test():
    """
    Quick test without requiring API key - demonstrates architecture
    """
    print("\n" + "="*80)
    print("ARCHITECTURE DEMONSTRATION")
    print("="*80 + "\n")
    
    print("📐 System Components:")
    print("\n1️⃣  Mother Agent (Orchestrator)")
    print("   - Validates user specifications")
    print("   - Decomposes projects into subtasks")
    print("   - Creates/destroys specialized agents")
    print("   - Monitors agent health (200ms intervals)")
    print("   - Consolidates outputs")
    
    print("\n2️⃣  Ghost MCP Server (Health Monitor)")
    print("   - HTTP server on port 8000")
    print("   - Agent heartbeat tracking (200ms)")
    print("   - Work quality validation")
    print("   - Performance metrics")
    
    print("\n3️⃣  Inter-Agent MCP Server (Collaboration)")
    print("   - HTTP server on port 8001")
    print("   - Context sharing between agents")
    print("   - Dependency management")
    print("   - Resource sharing")
    
    print("\n4️⃣  Sub-Agents (Specialized Workers)")
    print("   - Backend Developer: API, database, server logic")
    print("   - Frontend Developer: UI, client-side code")
    print("   - UX Designer: User flows, wireframes")
    print("   - DevOps: Deployment, infrastructure")
    print("   - QA Tester: Testing strategy, validation")
    
    print("\n" + "="*80)
    print("WORKFLOW")
    print("="*80 + "\n")
    
    workflow_steps = [
        ("1", "User provides project specification"),
        ("2", "Mother validates spec and requests clarifications"),
        ("3", "Mother decomposes project into 2-4 subtasks"),
        ("4", "Mother creates specialized agents (4-tuple config)"),
        ("5", "Agents register with Ghost MCP and Inter-Agent MCP"),
        ("6", "Agents execute tasks autonomously"),
        ("7", "Ghost MCP monitors health every 200ms"),
        ("8", "Agents collaborate via Inter-Agent MCP"),
        ("9", "Failed tasks retry up to 3 times"),
        ("10", "Mother collects and validates outputs"),
        ("11", "Mother consolidates into final deliverable"),
        ("12", "Mother destroys all agents"),
        ("13", "Returns tar.gz package to user")
    ]
    
    for step, description in workflow_steps:
        print(f"  {step}. {description}")
        await asyncio.sleep(0.3)  # Dramatic effect
    
    print("\n" + "="*80)
    print("4-TUPLE AGENT CONFIGURATION")
    print("="*80 + "\n")
    
    print("Each agent receives:")
    print("  I (Identity):  Role definition and expertise")
    print("  C (Context):   Project context and constraints")
    print("  T (Tools):     Available MCP tools")
    print("  M (Mission):   Specific task assignment")
    
    print("\n" + "="*80)
    print("FAILURE HANDLING")
    print("="*80 + "\n")
    
    print("Retry Logic:")
    print("  • Task fails → Retry #1")
    print("  • Still fails → Retry #2")
    print("  • Still fails → Retry #3")
    print("  • Still fails → Kill agent, create replacement")
    print("  • Majority fail → Report to user")
    
    print("\n" + "="*80)
    print("SUCCESS CRITERIA (V0)")
    print("="*80 + "\n")
    
    print("✅ Non-overlapping agent roles")
    print("✅ Each agent completes assigned subtask")
    print("✅ Mother consolidates without human intervention")
    print("✅ Complete execution < 5 minutes")
    print("✅ Proper agent lifecycle management")
    print("✅ Health monitoring via Ghost MCP")
    print("✅ Inter-agent collaboration via MCP")
    

def main():
    """Main entry point"""
    
    print("\n" + "="*80)
    print("MOTHER-AGENT SYSTEM")
    print("Multi-Agent Software Development Orchestration")
    print("="*80 + "\n")
    
    print("Choose demo mode:")
    print("1. Quick Architecture Demo (no API key needed)")
    print("2. Full System Demo (requires Anthropic API key)")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(quick_test())
    elif choice == "2":
        api_key = input("\nEnter your Anthropic API key: ").strip()
        if not api_key:
            print("❌ API key required for full demo")
            return
        
        demo = MultiAgentSystemDemo()
        try:
            asyncio.run(demo.start_mcp_servers())
            asyncio.run(demo.run_demo(api_key))
        finally:
            demo.stop_mcp_servers()
    else:
        print("Goodbye!")


if __name__ == "__main__":
    main()
