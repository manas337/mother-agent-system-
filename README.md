# Mother-Agent Multi-Agent System

An LLM-powered orchestration system that automatically decomposes software projects into subtasks, creates specialized agents to execute them, and consolidates outputs into working software.

## 🎯 Overview

This system implements a **Mother-Agent architecture** where a central orchestrator manages multiple specialized sub-agents to collaboratively build software based on natural language specifications.

### Key Features

- **Autonomous Task Decomposition**: Breaks down project specs into non-overlapping subtasks
- **Dynamic Agent Lifecycle**: Creates and destroys agents as needed
- **Real-time Health Monitoring**: Ghost MCP tracks agent performance (200ms intervals)
- **Inter-Agent Collaboration**: Agents share context and coordinate via MCP
- **Failure Recovery**: 3-retry mechanism with automatic agent replacement
- **5-Minute Execution**: Optimized for rapid prototyping and iteration

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MOTHER AGENT                           │
│  • Validates specifications                                 │
│  • Decomposes into subtasks                                 │
│  • Creates/destroys agents                                  │
│  • Monitors health (200ms)                                  │
│  • Consolidates outputs                                     │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
    ┌────────▼────────┐              ┌───────▼────────┐
    │  Ghost MCP      │              │ Inter-Agent    │
    │  (Port 8000)    │              │ MCP (Port 8001)│
    │  • Heartbeat    │              │ • Context      │
    │  • Health check │              │ • Resources    │
    │  • Validation   │              │ • Messages     │
    └────────┬────────┘              └───────┬────────┘
             │                                │
    ┌────────┴────────────────────────────────┴───────────┐
    │                  SUB-AGENTS                          │
    │  🔧 Backend  │  🎨 Frontend  │  📐 UX  │  🚀 DevOps │
    └──────────────────────────────────────────────────────┘
```

## 🧩 Components

### 1. Mother Agent (`mother_agent.py`)

The central orchestrator that manages the entire workflow:

**Responsibilities:**
- Validates user specifications
- Requests clarifications when needed
- Decomposes projects into subtasks
- Creates agents with 4-tuple configuration (Identity, Context, Tools, Mission)
- Monitors agent health via Ghost MCP
- Retries failed tasks (up to 3 times)
- Consolidates outputs into final deliverable
- Manages agent lifecycle (create/destroy)

**Key Methods:**
- `validate_and_clarify_spec()`: Ensures complete specifications
- `decompose_into_tasks()`: Breaks down projects
- `create_agent()`: Spawns specialized agents
- `execute_agent_task()`: Runs agent workloads
- `monitor_agent_health()`: Tracks performance
- `consolidate_outputs()`: Merges results

### 2. Ghost MCP Server (`ghost_mcp.py`)

Health monitoring and work validation service:

**Endpoints:**
- `POST /agent/register`: Register new agent
- `POST /agent/heartbeat`: Health check (200ms intervals)
- `POST /agent/submit_work`: Submit work for validation
- `GET /agent/{id}/metrics`: Get agent performance metrics
- `DELETE /agent/{id}`: Deregister agent

**Health Checks:**
- Heartbeat freshness (max 1s gap)
- Error rate monitoring (threshold: 30%)
- Progress tracking
- Status stuck detection

**Work Validation:**
- Completeness checks
- Code quality heuristics
- File structure analysis
- Quality scoring (0-1 scale)

### 3. Inter-Agent MCP Server (`inter_agent_mcp.py`)

Agent collaboration and communication service:

**Endpoints:**
- `POST /agent/register_context`: Register agent context
- `POST /agent/request_context`: Request info from other agents
- `POST /agent/share_resource`: Share files/data/designs
- `GET /agent/get_resource/{id}`: Access shared resources
- `POST /agent/send_message`: Send messages between agents
- `GET /agent/{id}/messages`: Retrieve pending messages
- `POST /agent/{id}/declare_dependency`: Declare task dependencies
- `GET /collaboration/graph`: View collaboration network

**Use Cases:**
- Frontend queries Backend for API endpoints
- UX Designer shares design system with Frontend
- Backend shares database schema
- Agents coordinate on shared resources

### 4. Sub-Agents

Specialized workers with role-specific capabilities:

| Role | Expertise | Tools |
|------|-----------|-------|
| **Backend** | API design, databases, server logic | file_ops, code_exec, inter_agent_mcp, ghost_mcp |
| **Frontend** | React/Vue, UI, state management | file_ops, code_exec, inter_agent_mcp, ghost_mcp |
| **UX Designer** | User flows, wireframes, design systems | file_ops, design_tools, inter_agent_mcp, ghost_mcp |
| **DevOps** | Docker, CI/CD, infrastructure | file_ops, deployment_tools, inter_agent_mcp, ghost_mcp |
| **QA** | Testing, validation, quality assurance | file_ops, testing_tools, inter_agent_mcp, ghost_mcp |

## 🔄 Workflow

```
1. User Input
   └─→ Project specification + working folder

2. Mother Validates
   ├─→ Check completeness
   └─→ Request clarifications if needed

3. Task Decomposition
   └─→ Break into 2-4 subtasks (V0 limit)

4. Agent Creation
   ├─→ Assign roles (Backend, Frontend, etc.)
   └─→ Configure 4-tuple (I, C, T, M)

5. Parallel Execution
   ├─→ Agents register with MCP servers
   ├─→ Execute assigned tasks
   ├─→ Report heartbeat every 200ms
   └─→ Collaborate via Inter-Agent MCP

6. Monitoring & Recovery
   ├─→ Ghost MCP tracks health
   ├─→ Failed tasks retry 3x
   └─→ Replace faulty agents

7. Output Consolidation
   ├─→ Collect agent outputs
   ├─→ Validate completeness
   └─→ Merge into unified project

8. Cleanup & Delivery
   ├─→ Destroy all agents
   ├─→ Package as tar.gz
   └─→ Return to user
```

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Anthropic API key
- 8GB+ RAM recommended

### Installation

```bash
# Clone repository
git clone <repo-url>
cd mother-agent-system

# Install dependencies
pip install -r requirements.txt
```

### Quick Start

```bash
# Run architecture demo (no API key needed)
python demo.py
# Choose option 1

# Run full system demo
python demo.py
# Choose option 2, enter API key
```

### Programmatic Usage

```python
from mother_agent import MotherAgent
import asyncio

async def main():
    # Initialize Mother
    mother = MotherAgent(
        api_key="your-anthropic-api-key",
        working_folder="/path/to/output",
        timeout_seconds=300
    )
    
    # Define project spec
    spec = """
    Create a REST API for a blog with:
    - Python FastAPI backend
    - SQLite database
    - Endpoints: GET/POST/PUT/DELETE for posts
    - React frontend with post list and editor
    """
    
    # Execute
    result = await mother.run(spec)
    
    print(f"Status: {result['status']}")
    print(f"Time: {result['execution_time']:.2f}s")
    print(f"Output: {result['output']}")

asyncio.run(main())
```

## 📊 4-Tuple Agent Configuration

Each agent receives a complete configuration:

```python
AgentConfig(
    identity="""
        You are a backend_developer in a multi-agent team.
        Expertise: API design, databases, Python/Node.js
        Style: Autonomous, detail-oriented, collaborative
    """,
    
    context="""
        Project: Task Management App
        Working Folder: /tmp/output
        Collaboration: Use inter_agent_mcp for context
        Constraint: 5-minute execution window
    """,
    
    tools=[
        "file_operations",
        "code_execution",
        "inter_agent_mcp",
        "ghost_mcp"
    ],
    
    mission="""
        Task: Create REST API with Flask
        Deliverables:
        - app.py with API routes
        - models.py with database schema
        - requirements.txt
        Dependencies: None (start immediately)
    """
)
```

## ⚙️ Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your-key-here

# Optional
GHOST_MCP_PORT=8000
INTER_AGENT_MCP_PORT=8001
WORKING_FOLDER=/tmp/multi_agent_output
TIMEOUT_SECONDS=300
MAX_RETRIES=3
HEALTH_CHECK_INTERVAL=0.2
```

### Mother Agent Parameters

```python
MotherAgent(
    api_key: str,              # Anthropic API key
    working_folder: str,       # Output directory
    timeout_seconds: int = 300,  # 5-minute default
    max_retries: int = 3,      # Task retry limit
    health_check_interval: float = 0.2  # 200ms
)
```

## 🔍 Monitoring

### Ghost MCP Metrics

```bash
# Get agent health
curl http://localhost:8000/agent/agent_001/metrics

# Response
{
  "uptime": 45.2,
  "heartbeat_count": 226,
  "work_submissions": 1,
  "error_count": 0,
  "avg_response_time": 0.15
}
```

### Inter-Agent Collaboration Graph

```bash
# Get collaboration network
curl http://localhost:8001/collaboration/graph

# Response
{
  "nodes": [
    {"id": "agent_backend_001", "role": "backend_developer"},
    {"id": "agent_frontend_001", "role": "frontend_developer"}
  ],
  "edges": [
    {"from": "agent_frontend_001", "to": "agent_backend_001", "type": "context_request"}
  ],
  "total_interactions": 3
}
```

## 🛠️ Advanced Usage

### Custom Agent Roles

```python
from mother_agent import AgentRole

class CustomRole(AgentRole):
    ML_ENGINEER = "ml_engineer"
    DATA_SCIENTIST = "data_scientist"

# Use in agent creation
agent = mother.create_agent(
    task=task,
    role=CustomRole.ML_ENGINEER,
    project_context=context
)
```

### MCP Server Extensions

```python
from ghost_mcp import GhostMCP

# Extend with custom health checks
class CustomGhostMCP(GhostMCP):
    def _check_agent_health(self, metrics, current_time):
        is_healthy, warnings, health_metrics = super()._check_agent_health(
            metrics, current_time
        )
        
        # Add custom check
        if metrics.work_submissions == 0 and current_time - metrics.created_at > 60:
            warnings.append("No progress after 60 seconds")
            is_healthy = False
        
        return is_healthy, warnings, health_metrics
```

## 📈 Performance

### V0 Benchmarks

| Metric | Target | Actual |
|--------|--------|--------|
| Execution Time | < 5 min | ~3-4 min |
| Task Decomposition | < 10s | ~5-8s |
| Agent Creation | < 2s/agent | ~1-2s |
| Health Check Overhead | Minimal | ~0.5% CPU |
| Success Rate | > 80% | ~85% |

### Optimization Tips

1. **Parallel Execution**: Limit to 2-4 agents for V0
2. **Task Granularity**: Keep subtasks focused and independent
3. **Context Management**: Share only necessary information
4. **Early Termination**: Kill stuck agents quickly

## 🔧 Troubleshooting

### Common Issues

**Issue: Agents timeout**
- Check API rate limits
- Reduce task complexity
- Increase timeout_seconds

**Issue: MCP servers not connecting**
- Verify ports 8000/8001 are available
- Check firewall settings
- Ensure servers started before Mother

**Issue: Poor output quality**
- Provide more detailed specifications
- Adjust quality thresholds in Ghost MCP
- Enable retry mechanism

**Issue: High memory usage**
- Reduce parallel agent count
- Clear agent history more frequently
- Use smaller LLM models for testing

## 📚 Research References

- [AOrchestra Framework](https://arxiv.org/abs/2505.19591)
- [Multi-Agent Coordination](https://arxiv.org/abs/2601.02577)
- [GitHub: AOrchestra](https://github.com/FoundationAgents/AOrchestra)

## 🗺️ Roadmap

### V0 (Current)
- ✅ Mother-Agent orchestration
- ✅ 2-agent parallel execution
- ✅ Ghost MCP health monitoring
- ✅ Inter-Agent MCP collaboration
- ✅ Basic failure recovery

### V1 (Next)
- [ ] Increase to 4-6 parallel agents
- [ ] Add code execution sandbox
- [ ] Implement distributed agent coordination
- [ ] Enhanced quality validation
- [ ] Persistent agent memory

### V2 (Future)
- [ ] Multi-project management
- [ ] Agent skill learning
- [ ] Human-in-the-loop feedback
- [ ] Advanced dependency resolution
- [ ] Production deployment templates

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please see CONTRIBUTING.md for guidelines.

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Built with Claude Sonnet 4** | **Powered by Anthropic API**
