# Quick Start Guide - Mother-Agent System

Get up and running with the Mother-Agent multi-agent system in 5 minutes.

## Prerequisites

- **Python 3.9+** installed
- **Anthropic API key** (get one at https://console.anthropic.com/)
- **8GB RAM** recommended
- **Internet connection** for API calls

## 5-Minute Setup

### Step 1: Install Dependencies (1 minute)

```bash
# Install required packages
pip install anthropic fastapi uvicorn pydantic httpx

# Or use requirements.txt
pip install -r requirements.txt
```

### Step 2: Configure Environment (30 seconds)

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API key
# ANTHROPIC_API_KEY=your-key-here
```

Or set environment variable directly:
```bash
export ANTHROPIC_API_KEY=your-api-key-here
```

### Step 3: Run Your First Project (3 minutes)

**Option A: Use CLI (Recommended)**

```bash
# Run interactive demo
python cli.py demo

# Or create directly from specification
python cli.py create --inline "Create a REST API for a todo app with Python Flask"
```

**Option B: Use Python API**

Create a file `my_project.py`:

```python
from mother_agent import MotherAgent
import asyncio

async def main():
    mother = MotherAgent(
        api_key="your-api-key",
        working_folder="./output",
        timeout_seconds=300
    )
    
    spec = """
    Create a simple blog API with:
    - Python Flask backend
    - SQLite database
    - CRUD operations for blog posts
    - Basic validation
    """
    
    result = await mother.run(spec)
    print(f"Status: {result['status']}")
    print(f"Time: {result['execution_time']:.2f}s")

asyncio.run(main())
```

Run it:
```bash
python my_project.py
```

## What Happens Next?

The Mother-Agent will:

1. ✅ **Validate** your specification
2. 🔄 **Decompose** into subtasks (2-4 tasks)
3. 🤖 **Create** specialized agents (Backend, Frontend, etc.)
4. ⚡ **Execute** tasks in parallel
5. 👁️ **Monitor** health every 200ms
6. 🔁 **Retry** failed tasks (up to 3x)
7. 📦 **Consolidate** outputs
8. 🎯 **Deliver** working software

**Execution time:** Usually 2-4 minutes for simple projects

## Example Projects

### 1. Task Management App

```bash
python cli.py create --inline "Create a task management web app with React frontend and Python Flask backend"
```

### 2. Weather API

```bash
python cli.py create --inline "Create a weather API service using FastAPI with mock data endpoints"
```

### 3. Custom Specification

Create `spec.txt`:
```
Create a user authentication system with:

Backend:
- FastAPI framework
- JWT token authentication
- User registration and login
- Password hashing with bcrypt
- SQLite database

Frontend:
- React with hooks
- Login and register forms
- Protected routes
- Token storage in localStorage

Additional:
- Input validation
- Error handling
- API documentation
```

Then run:
```bash
python cli.py create --spec spec.txt --archive
```

## CLI Commands Cheatsheet

```bash
# Show available agent roles
python cli.py roles

# Show project templates
python cli.py templates

# Show configuration
python cli.py config --show

# Validate configuration
python cli.py config --validate

# Run demo
python cli.py demo

# Show version
python cli.py version

# Create with custom timeout (10 minutes)
python cli.py create --spec myspec.txt --timeout 600

# Create and package as tar.gz
python cli.py create --inline "..." --archive
```

## Understanding Output

After execution, you'll get:

```
output/
├── generated_project/
│   ├── README.md              # Setup instructions
│   ├── src/
│   │   ├── backend/          # Backend code
│   │   ├── frontend/         # Frontend code
│   │   └── shared/           # Shared utilities
│   ├── config/               # Configuration files
│   ├── tests/                # Test files
│   └── .gitignore
└── generated_project.tar.gz  # Packaged deliverable (if --archive used)
```

## Troubleshooting

### "No API key provided"
```bash
# Set environment variable
export ANTHROPIC_API_KEY=your-key-here

# Or use --api-key flag
python cli.py create --api-key your-key-here --inline "..."
```

### "Timeout during execution"
```bash
# Increase timeout (default: 300s)
python cli.py create --timeout 600 --inline "..."
```

### "MCP servers not connecting"
```bash
# Check ports 8000 and 8001 are available
lsof -i :8000
lsof -i :8001

# If occupied, kill process or change ports in .env
```

### "Poor output quality"
- Provide more detailed specifications
- Include specific technology preferences
- Mention expected features explicitly
- Use project templates as reference

## Advanced Usage

### Running MCP Servers Separately

For advanced monitoring and debugging:

**Terminal 1: Ghost MCP (Health Monitor)**
```bash
python ghost_mcp.py
```

**Terminal 2: Inter-Agent MCP (Collaboration)**
```bash
python inter_agent_mcp.py
```

**Terminal 3: Mother Agent**
```bash
python cli.py create --inline "..."
```

### Custom Configuration

Create `custom_config.json`:
```json
{
  "mother": {
    "timeout_seconds": 600,
    "max_retries": 5,
    "max_parallel_agents": 6
  },
  "mcp": {
    "ghost_mcp": "0.0.0.0:8000",
    "inter_agent_mcp": "0.0.0.0:8001"
  }
}
```

### Programmatic Usage with Custom Roles

```python
from mother_agent import MotherAgent, AgentRole
from config import RoleConfig

# Define custom role
custom_role = AgentRole.BACKEND  # Or create custom enum

# Initialize with config
mother = MotherAgent(
    api_key="your-key",
    working_folder="./custom_output",
    timeout_seconds=600
)

# Run with custom settings
result = await mother.run(your_spec)
```

## Performance Tips

1. **Keep specifications focused**: Limit to 2-4 major features for V0
2. **Use templates**: Pre-defined templates are optimized
3. **Parallel agents**: V0 supports 2-4 agents efficiently
4. **Clear requirements**: Specific specs = better outputs
5. **Adequate timeout**: Complex projects need 5-10 minutes

## Next Steps

- Read the [complete README](README.md) for architecture details
- Explore [configuration options](config.py)
- Review [example projects](examples/)
- Check [API documentation](docs/api.md)
- Join the community discussions

## Getting Help

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Full docs in `/docs` folder
- **Examples**: Sample projects in `/examples` folder
- **Tests**: See `test_suite.py` for usage patterns

---

**Ready to build?** Run `python cli.py demo` to get started! 🚀
