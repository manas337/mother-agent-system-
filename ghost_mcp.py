"""
Ghost MCP Server - Agent Health Monitoring and Work Verification
Implements the 200ms health check system and work quality validation
"""

import asyncio
import json
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn


# Data models for API
class HealthCheckRequest(BaseModel):
    agent_id: str
    timestamp: float
    status: str
    work_sample: Optional[str] = None


class HealthCheckResponse(BaseModel):
    agent_id: str
    is_healthy: bool
    warnings: List[str]
    metrics: Dict[str, float]


class WorkSubmission(BaseModel):
    agent_id: str
    task_id: str
    deliverables: Dict[str, str]
    timestamp: float


class WorkValidationResponse(BaseModel):
    is_valid: bool
    quality_score: float
    issues: List[str]
    recommendations: List[str]


class SupervisorValidationRequest(BaseModel):
    agent_id: str
    task_id: str
    deliverables: Dict[str, str]
    test_results: Optional[Dict[str, str]] = None


class FunctionalValidationResponse(BaseModel):
    is_valid: bool
    tests_passed: int
    tests_failed: int
    coverage_estimate: float
    errors: List[str]


@dataclass
class AgentMetrics:
    agent_id: str
    created_at: float
    last_heartbeat: float
    heartbeat_count: int = 0
    work_submissions: int = 0
    avg_response_time: float = 0.0
    error_count: int = 0
    status_history: List[str] = field(default_factory=list)


class GhostMCP:
    """
    Ghost MCP Server for monitoring agent health and validating work
    Runs as HTTP server for V0 (instead of stdin/stdout)
    """
    
    def __init__(self, check_interval: float = 0.2):
        self.app = FastAPI(title="Ghost MCP Server")
        self.check_interval = check_interval
        self.agent_metrics: Dict[str, AgentMetrics] = {}
        self.work_submissions: Dict[str, List[WorkSubmission]] = {}
        
        # Thresholds for health detection
        self.max_heartbeat_gap = 1.0  # 1 second without heartbeat = warning
        self.max_error_rate = 0.3  # 30% error rate = unhealthy
        self.min_quality_score = 0.6  # 60% quality threshold
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup FastAPI routes for MCP endpoints"""
        
        @self.app.post("/agent/register")
        async def register_agent(agent_id: str):
            """Register a new agent for monitoring"""
            if agent_id not in self.agent_metrics:
                self.agent_metrics[agent_id] = AgentMetrics(
                    agent_id=agent_id,
                    created_at=time.time(),
                    last_heartbeat=time.time()
                )
                return {"status": "registered", "agent_id": agent_id}
            return {"status": "already_registered", "agent_id": agent_id}
        
        @self.app.post("/agent/heartbeat", response_model=HealthCheckResponse)
        async def heartbeat(request: HealthCheckRequest):
            """
            Agent heartbeat endpoint - called every 200ms
            Returns health status and warnings
            """
            agent_id = request.agent_id
            
            if agent_id not in self.agent_metrics:
                # Auto-register if not exists
                await register_agent(agent_id)
            
            metrics = self.agent_metrics[agent_id]
            current_time = time.time()
            
            # Update metrics
            metrics.last_heartbeat = current_time
            metrics.heartbeat_count += 1
            metrics.status_history.append(request.status)
            
            # Keep only last 20 status updates
            if len(metrics.status_history) > 20:
                metrics.status_history = metrics.status_history[-20:]
            
            # Perform health checks
            is_healthy, warnings, health_metrics = self._check_agent_health(metrics, current_time)
            
            return HealthCheckResponse(
                agent_id=agent_id,
                is_healthy=is_healthy,
                warnings=warnings,
                metrics=health_metrics
            )
        
        @self.app.post("/agent/submit_work", response_model=WorkValidationResponse)
        async def submit_work(submission: WorkSubmission):
            """
            Agent submits work for validation
            Returns quality assessment and recommendations
            """
            agent_id = submission.agent_id
            
            # Track submission
            if agent_id not in self.work_submissions:
                self.work_submissions[agent_id] = []
            self.work_submissions[agent_id].append(submission)
            
            # Update metrics
            if agent_id in self.agent_metrics:
                self.agent_metrics[agent_id].work_submissions += 1
            
            # Validate work quality
            validation = await self._validate_work(submission)
            
            return validation
        
        @self.app.get("/agent/{agent_id}/metrics")
        async def get_agent_metrics(agent_id: str):
            """Get detailed metrics for an agent"""
            if agent_id not in self.agent_metrics:
                raise HTTPException(status_code=404, detail="Agent not found")
            
            metrics = self.agent_metrics[agent_id]
            return {
                "agent_id": agent_id,
                "uptime": time.time() - metrics.created_at,
                "heartbeat_count": metrics.heartbeat_count,
                "work_submissions": metrics.work_submissions,
                "avg_response_time": metrics.avg_response_time,
                "error_count": metrics.error_count,
                "recent_status": metrics.status_history[-5:] if metrics.status_history else []
            }
        
        @self.app.delete("/agent/{agent_id}")
        async def deregister_agent(agent_id: str):
            """Remove agent from monitoring (called when agent is destroyed)"""
            if agent_id in self.agent_metrics:
                del self.agent_metrics[agent_id]
            if agent_id in self.work_submissions:
                del self.work_submissions[agent_id]
            return {"status": "deregistered", "agent_id": agent_id}
        
        @self.app.post("/supervisor/validate", response_model=FunctionalValidationResponse)
        async def supervisor_validate(request: SupervisorValidationRequest):
            """Supervisor endpoint for functional validation of agent work"""
            errors = []
            tests_passed = 0
            tests_failed = 0

            for file_path, content in request.deliverables.items():
                if file_path.endswith('.py'):
                    try:
                        compile(content, file_path, 'exec')
                        tests_passed += 1
                    except SyntaxError as e:
                        errors.append(f"Syntax error in {file_path}: {str(e)}")
                        tests_failed += 1
                elif file_path.endswith('.json'):
                    try:
                        json.loads(content)
                        tests_passed += 1
                    except json.JSONDecodeError as e:
                        errors.append(f"Invalid JSON in {file_path}: {str(e)}")
                        tests_failed += 1

            if request.test_results:
                for test_name, test_result in request.test_results.items():
                    if test_result.lower() in ('pass', 'passed', 'true', 'ok'):
                        tests_passed += 1
                    else:
                        tests_failed += 1
                        errors.append(f"Test failed: {test_name} - {test_result}")

            total_tests = tests_passed + tests_failed
            coverage = tests_passed / max(total_tests, 1)
            is_valid = errors == [] and tests_failed == 0

            return FunctionalValidationResponse(
                is_valid=is_valid,
                tests_passed=tests_passed,
                tests_failed=tests_failed,
                coverage_estimate=coverage,
                errors=errors
            )

        @self.app.post("/supervisor/integration_check")
        async def supervisor_integration_check(request: SupervisorValidationRequest):
            """Check if deliverables integrate properly with existing project files"""
            cross_references = []
            missing_refs = []

            all_paths = list(request.deliverables.keys())
            for path in all_paths:
                for other_path in all_paths:
                    if path != other_path:
                        if path.replace('.py', '') in request.deliverables.get(other_path, ''):
                            cross_references.append(f"{other_path} imports/references {path}")
                        if other_path.replace('.py', '') in request.deliverables.get(path, ''):
                            cross_references.append(f"{path} imports/references {other_path}")

            return {
                "has_integration": len(missing_refs) == 0,
                "cross_references": cross_references,
                "potential_issues": missing_refs
            }

        @self.app.get("/health")
        async def health():
            """MCP server health check"""
            return {
                "status": "healthy",
                "active_agents": len(self.agent_metrics),
                "total_submissions": sum(len(subs) for subs in self.work_submissions.values())
            }
    
    def _check_agent_health(self, metrics: AgentMetrics, current_time: float) -> tuple:
        """
        Comprehensive health check logic
        Returns: (is_healthy, warnings, metrics_dict)
        """
        warnings = []
        is_healthy = True
        
        # Check 1: Heartbeat freshness
        time_since_heartbeat = current_time - metrics.last_heartbeat
        if time_since_heartbeat > self.max_heartbeat_gap:
            warnings.append(f"No heartbeat for {time_since_heartbeat:.2f}s")
            is_healthy = False
        
        # Check 2: Error rate
        if len(metrics.status_history) > 5:
            error_count = sum(1 for s in metrics.status_history[-10:] if 'error' in s.lower() or 'failed' in s.lower())
            error_rate = error_count / min(10, len(metrics.status_history))
            
            if error_rate > self.max_error_rate:
                warnings.append(f"High error rate: {error_rate*100:.1f}%")
                is_healthy = False
        
        # Check 3: Progress indicators
        if metrics.heartbeat_count > 20 and metrics.work_submissions == 0:
            warnings.append("No work submissions despite multiple heartbeats")
        
        # Check 4: Status stuck
        if len(metrics.status_history) >= 5:
            last_5 = metrics.status_history[-5:]
            if len(set(last_5)) == 1 and last_5[0] in ['blocked', 'waiting', 'idle']:
                warnings.append(f"Agent stuck in '{last_5[0]}' status")
        
        health_metrics = {
            "uptime": current_time - metrics.created_at,
            "heartbeat_count": metrics.heartbeat_count,
            "work_submissions": metrics.work_submissions,
            "error_count": metrics.error_count,
            "time_since_heartbeat": time_since_heartbeat
        }
        
        return is_healthy, warnings, health_metrics
    
    async def _validate_work(self, submission: WorkSubmission) -> WorkValidationResponse:
        """
        Validate quality of submitted work
        Checks for completeness, code quality, etc.
        """
        issues = []
        quality_score = 1.0
        recommendations = []
        
        # Check 1: Has deliverables
        if not submission.deliverables:
            issues.append("No deliverables submitted")
            quality_score -= 0.5
        
        # Check 2: Code quality heuristics
        for file_path, content in submission.deliverables.items():
            # Check for empty files
            if not content or len(content.strip()) < 10:
                issues.append(f"{file_path} appears empty or too short")
                quality_score -= 0.2
            
            # Check for basic code structure (simplified)
            if file_path.endswith('.py'):
                if 'def ' not in content and 'class ' not in content:
                    issues.append(f"{file_path} has no functions or classes")
                    quality_score -= 0.1
                    recommendations.append("Add proper function/class structure")
            
            elif file_path.endswith(('.js', '.jsx', '.ts', '.tsx')):
                if 'function' not in content and 'const' not in content and 'export' not in content:
                    issues.append(f"{file_path} has no functions or exports")
                    quality_score -= 0.1
            
            # Check for TODO or FIXME comments (indicates incomplete work)
            if 'TODO' in content or 'FIXME' in content:
                recommendations.append("Complete TODO/FIXME items")
                quality_score -= 0.05
        
        # Check 3: Expected file types
        has_code = any(
            path.endswith(('.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css'))
            for path in submission.deliverables.keys()
        )
        
        if not has_code:
            issues.append("No code files detected")
            quality_score -= 0.3
        
        # Clamp quality score
        quality_score = max(0.0, min(1.0, quality_score))
        
        is_valid = quality_score >= self.min_quality_score and len(issues) == 0
        
        return WorkValidationResponse(
            is_valid=is_valid,
            quality_score=quality_score,
            issues=issues,
            recommendations=recommendations
        )
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the Ghost MCP server"""
        print(f"👻 Ghost MCP Server starting on {host}:{port}")
        uvicorn.run(self.app, host=host, port=port)


async def example_agent_integration():
    """
    Example of how an agent would interact with Ghost MCP
    """
    import httpx
    
    async with httpx.AsyncClient() as client:
        agent_id = "agent_backend_001"
        base_url = "http://localhost:8000"
        
        # Register agent
        await client.post(f"{base_url}/agent/register", params={"agent_id": agent_id})
        print(f"✅ Agent {agent_id} registered")
        
        # Simulate work cycle
        for tick in range(10):
            # Heartbeat every 200ms
            heartbeat_data = {
                "agent_id": agent_id,
                "timestamp": time.time(),
                "status": "working" if tick < 8 else "completing",
                "work_sample": f"Processing tick {tick}"
            }
            
            response = await client.post(f"{base_url}/agent/heartbeat", json=heartbeat_data)
            health = response.json()
            print(f"Tick {tick}: Health={health['is_healthy']}, Warnings={health['warnings']}")
            
            await asyncio.sleep(0.2)  # 200ms interval
        
        # Submit work
        work_data = {
            "agent_id": agent_id,
            "task_id": "task_1",
            "deliverables": {
                "app.py": "def main():\n    print('Hello World')\n\nif __name__ == '__main__':\n    main()",
                "README.md": "# My App\n\nA simple application."
            },
            "timestamp": time.time()
        }
        
        response = await client.post(f"{base_url}/agent/submit_work", json=work_data)
        validation = response.json()
        print(f"\n📋 Work Validation:")
        print(f"   Valid: {validation['is_valid']}")
        print(f"   Quality Score: {validation['quality_score']}")
        print(f"   Issues: {validation['issues']}")


if __name__ == "__main__":
    # Start Ghost MCP server
    ghost = GhostMCP(check_interval=0.2)
    ghost.run()
