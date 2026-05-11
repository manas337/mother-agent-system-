"""
Inter-Agent MCP Server - Agent-to-Agent Communication
Enables agents to share context, request information, and coordinate work
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn


# Data models
class ContextRequest(BaseModel):
    requesting_agent: str
    target_agent: str
    query: str
    timestamp: float


class ContextResponse(BaseModel):
    source_agent: str
    content: str
    timestamp: float
    is_available: bool


class AgentMessage(BaseModel):
    from_agent: str
    to_agent: str
    message_type: str  # "context_request", "work_update", "dependency_query", "collaboration"
    content: Dict[str, Any]
    timestamp: float


class SharedResource(BaseModel):
    resource_id: str
    agent_id: str
    resource_type: str  # "file", "data", "context", "design"
    content: Any
    metadata: Dict[str, Any]
    timestamp: float


@dataclass
class AgentContext:
    """Stores the current context and state of an agent"""
    agent_id: str
    role: str
    current_task: str
    work_products: Dict[str, str] = field(default_factory=dict)
    shared_context: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    last_update: float = 0.0


class InterAgentMCP:
    """
    Inter-Agent MCP Server for multi-agent coordination
    Facilitates context sharing, dependency management, and collaboration
    """
    
    def __init__(self):
        self.app = FastAPI(title="Inter-Agent MCP Server")
        self.agent_contexts: Dict[str, AgentContext] = {}
        self.message_queue: Dict[str, List[AgentMessage]] = {}
        self.shared_resources: Dict[str, SharedResource] = {}
        self.collaboration_log: List[Dict] = []
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes for inter-agent communication"""
        
        @self.app.post("/agent/register_context")
        async def register_agent_context(
            agent_id: str,
            role: str,
            current_task: str
        ):
            """Register or update agent's context"""
            if agent_id not in self.agent_contexts:
                self.agent_contexts[agent_id] = AgentContext(
                    agent_id=agent_id,
                    role=role,
                    current_task=current_task,
                    last_update=time.time()
                )
            else:
                # Update existing context
                context = self.agent_contexts[agent_id]
                context.current_task = current_task
                context.last_update = time.time()
            
            # Initialize message queue
            if agent_id not in self.message_queue:
                self.message_queue[agent_id] = []
            
            return {
                "status": "registered",
                "agent_id": agent_id,
                "available_agents": [
                    {"id": aid, "role": ctx.role}
                    for aid, ctx in self.agent_contexts.items()
                    if aid != agent_id
                ]
            }
        
        @self.app.post("/agent/request_context", response_model=ContextResponse)
        async def request_context(request: ContextRequest):
            """
            Request context from another agent
            Example: Frontend agent requests API endpoints from Backend agent
            """
            requesting = request.requesting_agent
            target = request.target_agent
            
            if target not in self.agent_contexts:
                return ContextResponse(
                    source_agent=target,
                    content="",
                    timestamp=time.time(),
                    is_available=False
                )
            
            target_context = self.agent_contexts[target]
            
            # Log the request
            self.collaboration_log.append({
                "type": "context_request",
                "from": requesting,
                "to": target,
                "query": request.query,
                "timestamp": request.timestamp
            })
            
            # Build response based on query
            response_content = self._process_context_query(
                target_context,
                request.query
            )
            
            # Send message to target agent (for awareness)
            message = AgentMessage(
                from_agent=requesting,
                to_agent=target,
                message_type="context_request",
                content={"query": request.query},
                timestamp=time.time()
            )
            self.message_queue[target].append(message)
            
            return ContextResponse(
                source_agent=target,
                content=response_content,
                timestamp=time.time(),
                is_available=True
            )
        
        @self.app.post("/agent/share_resource")
        async def share_resource(resource: SharedResource):
            """
            Share a resource (file, data, design) with other agents
            """
            self.shared_resources[resource.resource_id] = resource
            
            # Notify relevant agents
            self.collaboration_log.append({
                "type": "resource_shared",
                "agent": resource.agent_id,
                "resource_type": resource.resource_type,
                "resource_id": resource.resource_id,
                "timestamp": resource.timestamp
            })
            
            return {
                "status": "shared",
                "resource_id": resource.resource_id,
                "accessible_by": "all_agents"
            }
        
        @self.app.get("/agent/get_resource/{resource_id}")
        async def get_resource(resource_id: str, requesting_agent: str):
            """Retrieve a shared resource"""
            if resource_id not in self.shared_resources:
                raise HTTPException(status_code=404, detail="Resource not found")
            
            resource = self.shared_resources[resource_id]
            
            # Log access
            self.collaboration_log.append({
                "type": "resource_accessed",
                "agent": requesting_agent,
                "resource_id": resource_id,
                "timestamp": time.time()
            })
            
            return resource
        
        @self.app.post("/agent/send_message")
        async def send_message(message: AgentMessage):
            """Send a message to another agent"""
            target = message.to_agent
            
            if target not in self.message_queue:
                self.message_queue[target] = []
            
            self.message_queue[target].append(message)
            
            self.collaboration_log.append({
                "type": "message_sent",
                "from": message.from_agent,
                "to": message.to_agent,
                "message_type": message.message_type,
                "timestamp": message.timestamp
            })
            
            return {"status": "sent", "message_id": len(self.message_queue[target])}
        
        @self.app.get("/agent/{agent_id}/messages")
        async def get_messages(agent_id: str, mark_read: bool = True):
            """Get pending messages for an agent"""
            if agent_id not in self.message_queue:
                return {"messages": []}
            
            messages = self.message_queue[agent_id]
            
            if mark_read:
                self.message_queue[agent_id] = []
            
            return {
                "agent_id": agent_id,
                "message_count": len(messages),
                "messages": [msg.dict() for msg in messages]
            }
        
        @self.app.post("/agent/{agent_id}/update_work")
        async def update_work_products(
            agent_id: str,
            work_products: Dict[str, str]
        ):
            """Update agent's work products (files created, etc.)"""
            if agent_id not in self.agent_contexts:
                raise HTTPException(status_code=404, detail="Agent not registered")
            
            context = self.agent_contexts[agent_id]
            context.work_products.update(work_products)
            context.last_update = time.time()
            
            return {
                "status": "updated",
                "agent_id": agent_id,
                "work_product_count": len(context.work_products)
            }
        
        @self.app.get("/agent/{agent_id}/context")
        async def get_agent_context(agent_id: str):
            """Get full context of an agent"""
            if agent_id not in self.agent_contexts:
                raise HTTPException(status_code=404, detail="Agent not registered")
            
            context = self.agent_contexts[agent_id]
            return {
                "agent_id": agent_id,
                "role": context.role,
                "current_task": context.current_task,
                "work_products": list(context.work_products.keys()),
                "dependencies": context.dependencies,
                "last_update": context.last_update
            }
        
        @self.app.post("/agent/{agent_id}/declare_dependency")
        async def declare_dependency(agent_id: str, depends_on: str):
            """Declare that this agent depends on another agent's work"""
            if agent_id not in self.agent_contexts:
                raise HTTPException(status_code=404, detail="Agent not registered")
            
            context = self.agent_contexts[agent_id]
            if depends_on not in context.dependencies:
                context.dependencies.append(depends_on)
            
            return {
                "status": "declared",
                "agent_id": agent_id,
                "dependencies": context.dependencies
            }
        
        @self.app.get("/collaboration/log")
        async def get_collaboration_log(limit: int = 50):
            """Get recent collaboration events"""
            return {
                "total_events": len(self.collaboration_log),
                "recent_events": self.collaboration_log[-limit:]
            }
        
        @self.app.get("/collaboration/graph")
        async def get_collaboration_graph():
            """
            Get collaboration graph showing agent interactions
            Useful for Mother to visualize agent coordination
            """
            nodes = [
                {
                    "id": agent_id,
                    "role": ctx.role,
                    "task": ctx.current_task
                }
                for agent_id, ctx in self.agent_contexts.items()
            ]
            
            edges = []
            for event in self.collaboration_log:
                if event["type"] in ["context_request", "message_sent"]:
                    edges.append({
                        "from": event.get("from", event.get("agent")),
                        "to": event.get("to", ""),
                        "type": event["type"]
                    })
            
            return {
                "nodes": nodes,
                "edges": edges,
                "total_interactions": len(edges)
            }
        
        @self.app.delete("/agent/{agent_id}")
        async def deregister_agent(agent_id: str):
            """Remove agent from system"""
            if agent_id in self.agent_contexts:
                del self.agent_contexts[agent_id]
            if agent_id in self.message_queue:
                del self.message_queue[agent_id]
            
            return {"status": "deregistered", "agent_id": agent_id}
        
        @self.app.get("/health")
        async def health():
            """MCP server health check"""
            return {
                "status": "healthy",
                "active_agents": len(self.agent_contexts),
                "total_messages": sum(len(msgs) for msgs in self.message_queue.values()),
                "shared_resources": len(self.shared_resources)
            }
    
    def _process_context_query(self, target_context: AgentContext, query: str) -> str:
        """
        Process a context query and return relevant information
        This is a simplified version - production would use LLM to understand query
        """
        query_lower = query.lower()
        
        # API endpoints query
        if "api" in query_lower or "endpoint" in query_lower:
            endpoints = [k for k in target_context.work_products.keys() if "api" in k or "route" in k]
            if endpoints:
                return json.dumps({
                    "type": "api_endpoints",
                    "endpoints": endpoints,
                    "details": {k: target_context.work_products[k] for k in endpoints}
                })
        
        # Database schema query
        if "database" in query_lower or "schema" in query_lower or "model" in query_lower:
            schemas = [k for k in target_context.work_products.keys() if "model" in k or "schema" in k]
            if schemas:
                return json.dumps({
                    "type": "database_schema",
                    "schemas": schemas,
                    "details": {k: target_context.work_products[k] for k in schemas}
                })
        
        # Design/UI query
        if "design" in query_lower or "ui" in query_lower or "component" in query_lower:
            designs = [k for k in target_context.work_products.keys() if any(x in k for x in ["design", "ui", "component"])]
            if designs:
                return json.dumps({
                    "type": "designs",
                    "components": designs,
                    "details": {k: target_context.work_products[k] for k in designs}
                })
        
        # Generic: return task description and available work products
        return json.dumps({
            "type": "general_context",
            "agent_role": target_context.role,
            "current_task": target_context.current_task,
            "available_work_products": list(target_context.work_products.keys())
        })
    
    def run(self, host: str = "0.0.0.0", port: int = 8001):
        """Start the Inter-Agent MCP server"""
        print(f"🤝 Inter-Agent MCP Server starting on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)


async def example_agent_collaboration():
    """
    Example of two agents collaborating via Inter-Agent MCP
    """
    import httpx
    
    async with httpx.AsyncClient() as client:
        base_url = "http://localhost:8001"
        
        # Backend agent registers
        await client.post(
            f"{base_url}/agent/register_context",
            params={
                "agent_id": "agent_backend_001",
                "role": "backend_developer",
                "current_task": "Create REST API"
            }
        )
        print("✅ Backend agent registered")
        
        # Frontend agent registers
        await client.post(
            f"{base_url}/agent/register_context",
            params={
                "agent_id": "agent_frontend_001",
                "role": "frontend_developer",
                "current_task": "Create React UI"
            }
        )
        print("✅ Frontend agent registered")
        
        # Backend shares API endpoints
        await client.post(
            f"{base_url}/agent/share_resource",
            json={
                "resource_id": "api_spec_v1",
                "agent_id": "agent_backend_001",
                "resource_type": "data",
                "content": {
                    "endpoints": [
                        {"path": "/api/tasks", "method": "GET"},
                        {"path": "/api/tasks", "method": "POST"},
                        {"path": "/api/tasks/{id}", "method": "DELETE"}
                    ]
                },
                "metadata": {"version": "1.0"},
                "timestamp": time.time()
            }
        )
        print("📤 Backend shared API spec")
        
        # Frontend requests API context
        response = await client.post(
            f"{base_url}/agent/request_context",
            json={
                "requesting_agent": "agent_frontend_001",
                "target_agent": "agent_backend_001",
                "query": "What API endpoints are available?",
                "timestamp": time.time()
            }
        )
        context = response.json()
        print(f"📥 Frontend received context: {context['content'][:100]}...")
        
        # Frontend declares dependency on backend
        await client.post(
            f"{base_url}/agent/agent_frontend_001/declare_dependency",
            params={"depends_on": "agent_backend_001"}
        )
        print("🔗 Frontend declared dependency on Backend")
        
        # Get collaboration graph
        response = await client.get(f"{base_url}/collaboration/graph")
        graph = response.json()
        print(f"\n📊 Collaboration Graph:")
        print(f"   Nodes: {len(graph['nodes'])}")
        print(f"   Interactions: {graph['total_interactions']}")


if __name__ == "__main__":
    # Start Inter-Agent MCP server
    inter_agent_mcp = InterAgentMCP()
    inter_agent_mcp.run()
