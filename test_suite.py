"""
Test Suite for Mother-Agent System
Runs fully offline using MockProvider - no API keys needed
"""

import pytest
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).parent))

from mother_agent import MotherAgent, AgentRole, SubAgent
from task_manager import DAGManager, DAGTask, TaskExecutor, TaskStatus
from file_lock import AsyncFileQueue, LockManager
from llm_provider import MockProvider, load_llm_config, create_provider
from config import RoleRegistry, ProjectTemplates


# ============================================================================
# LLM PROVIDER TESTS
# ============================================================================

class TestLLMProvider:
    def test_mock_provider_works_without_api_key(self):
        provider = MockProvider()
        text = provider.generate("test prompt")
        assert text is not None
        assert len(text) > 0

    def test_mock_provider_json(self):
        provider = MockProvider()
        result = provider.generate_json("test prompt")
        assert isinstance(result, dict)
        assert result["status"] == "completed"

    def test_mock_provider_counts_calls(self):
        provider = MockProvider()
        provider.generate("a")
        provider.generate("b")
        provider.generate_json("c")
        assert provider.call_count == 3

    def test_create_mock_provider(self):
        config = {"provider": "mock"}
        provider = create_provider(config)
        assert isinstance(provider, MockProvider)


# ============================================================================
# DAG MANAGER TESTS
# ============================================================================

class TestDAGManager:
    def test_create_dag(self):
        dag = DAGManager()
        assert dag.tasks == {}

    def test_add_task(self):
        dag = DAGManager()
        task = DAGTask(task_id="t1", description="Test", role="BACKEND")
        dag.add_task(task)
        assert "t1" in dag.tasks
        assert dag.tasks["t1"].status == TaskStatus.PENDING

    def test_get_ready_tasks_no_deps(self):
        dag = DAGManager()
        t1 = DAGTask(task_id="t1", description="Task 1", role="BACKEND")
        dag.add_task(t1)
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "t1"

    def test_get_ready_tasks_with_deps(self):
        dag = DAGManager()
        t1 = DAGTask(task_id="t1", description="Task 1", role="BACKEND")
        t2 = DAGTask(task_id="t2", description="Task 2", role="FRONTEND", dependencies=["t1"])
        dag.add_task(t1)
        dag.add_task(t2)
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "t1"

    def test_task_becomes_ready_after_dep_completes(self):
        dag = DAGManager()
        t1 = DAGTask(task_id="t1", description="Dep", role="BACKEND")
        t2 = DAGTask(task_id="t2", description="Depends", role="FRONTEND", dependencies=["t1"])
        dag.add_task(t1)
        dag.add_task(t2)
        assert len(dag.get_ready_tasks()) == 1
        dag.mark_completed("t1")
        ready = dag.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "t2"

    def test_cycle_detection(self):
        dag = DAGManager()
        t1 = DAGTask(task_id="t1", description="A", role="BACKEND", dependencies=["t2"])
        t2 = DAGTask(task_id="t2", description="B", role="FRONTEND", dependencies=["t1"])
        dag.add_task(t1)
        dag.add_task(t2)
        assert dag.has_cycle() is True

    def test_no_cycle(self):
        dag = DAGManager()
        t1 = DAGTask(task_id="t1", description="A", role="BACKEND")
        t2 = DAGTask(task_id="t2", description="B", role="FRONTEND", dependencies=["t1"])
        dag.add_task(t1)
        dag.add_task(t2)
        assert dag.has_cycle() is False

    def test_execution_order(self):
        dag = DAGManager()
        t1 = DAGTask(task_id="t1", description="A", role="BACKEND")
        t2 = DAGTask(task_id="t2", description="B", role="FRONTEND", dependencies=["t1"])
        t3 = DAGTask(task_id="t3", description="C", role="QA", dependencies=["t1"])
        t4 = DAGTask(task_id="t4", description="D", role="DEVOPS", dependencies=["t2", "t3"])
        for t in [t1, t2, t3, t4]:
            dag.add_task(t)
        layers = dag.get_execution_order()
        assert len(layers) == 3
        assert layers[0][0].task_id == "t1"
        assert len(layers[1]) == 2
        assert layers[2][0].task_id == "t4"


class TestTaskExecutor:
    @pytest.mark.asyncio
    async def test_execute_single_task(self):
        dag = DAGManager()
        task = DAGTask(task_id="t1", description="Test", role="BACKEND")
        dag.add_task(task)

        async def execute_fn(t: DAGTask) -> bool:
            dag.mark_completed(t.task_id, '{"done": true}')
            return True

        executor = TaskExecutor(dag, execute_fn, poll_interval=0.01)
        results = await executor.run()
        assert results["t1"] == "completed"
        assert dag.tasks["t1"].status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_dag_order(self):
        dag = DAGManager()
        execution_order = []

        t1 = DAGTask(task_id="t1", description="A", role="BACKEND")
        t2 = DAGTask(task_id="t2", description="B", role="FRONTEND", dependencies=["t1"])
        dag.add_task(t1)
        dag.add_task(t2)

        async def execute_fn(t: DAGTask) -> bool:
            execution_order.append(t.task_id)
            dag.mark_completed(t.task_id, f'{{"done":"{t.task_id}"}}')
            return True

        executor = TaskExecutor(dag, execute_fn, poll_interval=0.01)
        await executor.run()
        assert execution_order == ["t1", "t2"]


# ============================================================================
# FILE LOCK TESTS
# ============================================================================

class TestFileLock:
    @pytest.mark.asyncio
    async def test_acquire_and_release(self):
        queue = AsyncFileQueue()
        acquired = await queue.acquire("test_resource")
        assert acquired is True
        queue.release("test_resource")
        queue.cleanup()

    @pytest.mark.asyncio
    async def test_double_acquire_queues(self):
        queue = AsyncFileQueue()
        await queue.acquire("test_resource")

        acquired = False
        async def try_acquire():
            nonlocal acquired
            acquired = await queue.acquire("test_resource")

        task = asyncio.create_task(try_acquire())
        await asyncio.sleep(0.05)
        assert acquired is False
        queue.release("test_resource")
        await asyncio.sleep(0.05)
        assert acquired is True
        queue.release("test_resource")
        queue.cleanup()

    @pytest.mark.asyncio
    async def test_release_all(self):
        queue = AsyncFileQueue()
        await queue.acquire("res1")
        await queue.acquire("res2")
        queue.release_all()
        assert all(not lock.locked() for lock in queue._locks.values())
        queue.cleanup()

    @pytest.mark.asyncio
    async def test_lock_manager_context(self, tmp_path):
        manager = LockManager(str(tmp_path))
        async with manager.lock_resource("test_file"):
            pass
        manager.cleanup()

    @pytest.mark.asyncio
    async def test_two_agents_queue_for_same_file(self, tmp_path):
        manager = LockManager(str(tmp_path))
        writes = []
        async def agent_a():
            async with manager.lock_resource("shared.txt"):
                writes.append("A_start")
                await asyncio.sleep(0.1)
                writes.append("A_end")
        async def agent_b():
            await asyncio.sleep(0.02)
            async with manager.lock_resource("shared.txt"):
                writes.append("B_start")
                writes.append("B_end")

        await asyncio.gather(agent_a(), agent_b())
        assert writes == ["A_start", "A_end", "B_start", "B_end"]
        manager.cleanup()


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================

class TestRoleRegistry:
    def test_roles_exist(self):
        roles = RoleRegistry.list_roles()
        assert len(roles) >= 6
        assert "backend" in roles
        assert "frontend" in roles
        assert "supervisor" in roles

    def test_supervisor_role(self):
        role = RoleRegistry.get_role("supervisor")
        assert role is not None
        assert "validation" in role.expertise.lower()
        assert "testing_tools" in role.tools

    def test_project_templates(self):
        templates = ProjectTemplates.list_templates()
        assert "web_app" in templates
        web = ProjectTemplates.get_template("web_app")
        assert "backend" in web["required_roles"]


# ============================================================================
# MOTHER AGENT UNIT TESTS
# ============================================================================

class TestMotherAgent:
    @pytest.fixture
    def agent(self):
        return MotherAgent(working_folder="/tmp/test_mother", timeout_seconds=300, llm=MockProvider())

    def test_creation(self, agent):
        assert agent is not None
        assert agent.timeout_seconds == 300
        assert agent.max_retries == 5
        assert isinstance(agent.llm, MockProvider)

    def test_timeout_check(self, agent):
        import time
        agent.start_time = None
        assert agent._check_timeout() is False
        agent.start_time = time.time() - 400
        assert agent._check_timeout() is True

    def test_create_backend_agent(self, agent):
        task = DAGTask(task_id="t1", description="Build API", role="BACKEND")
        sub = agent.create_agent(task, AgentRole.BACKEND, "Test project")
        assert sub is not None
        assert sub.role == AgentRole.BACKEND
        assert sub.config.identity is not None
        assert sub.config.context is not None
        assert sub.config.tools is not None
        assert sub.config.mission is not None
        assert "ghost_mcp" in sub.config.tools

    def test_create_supervisor_agent(self, agent):
        task = DAGTask(task_id="t_sup", description="Validate", role="SUPERVISOR")
        sub = agent.create_agent(task, AgentRole.SUPERVISOR, "Test")
        assert sub.role == AgentRole.SUPERVISOR

    def test_agent_lifecycle(self, agent):
        task = DAGTask(task_id="t_life", description="Test", role="BACKEND")
        sub = agent.create_agent(task, AgentRole.BACKEND, "Test")
        assert sub.agent_id in agent.agents
        agent.destroy_agent(sub.agent_id)
        assert sub.agent_id not in agent.agents

    def test_destroy_all_agents(self, agent):
        for i in range(3):
            t = DAGTask(task_id=f"t{i}", description=f"Task {i}", role="BACKEND")
            agent.create_agent(t, AgentRole.BACKEND, "Test")
        assert len(agent.agents) == 3
        for aid in list(agent.agents.keys()):
            agent.destroy_agent(aid)
        assert len(agent.agents) == 0

    def test_role_inference(self, agent):
        assert agent.infer_role("backend") == AgentRole.BACKEND
        assert agent.infer_role("FRONTEND") == AgentRole.FRONTEND
        assert agent.infer_role("unknown") == AgentRole.BACKEND

    def test_role_expertise_mapping(self, agent):
        exp = agent._get_role_expertise(AgentRole.BACKEND)
        assert "API" in exp
        exp = agent._get_role_expertise(AgentRole.SUPERVISOR)
        assert "validation" in exp

    def test_role_tools(self, agent):
        tools = agent._get_role_tools(AgentRole.BACKEND)
        assert "ghost_mcp" in tools
        assert "inter_agent_mcp" in tools

    @pytest.mark.asyncio
    async def test_validate_spec_offline(self, agent):
        result = await agent.validate_and_clarify_spec("Build a web app")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_execute_agent_offline(self, agent):
        task = DAGTask(task_id="t_exec", description="Test task", role="BACKEND")
        success = await agent.execute_agent_task(task)
        assert success is True

    def test_uses_mock_provider(self, agent):
        assert isinstance(agent.llm, MockProvider)


# ============================================================================
# INTEGRATION TEST
# ============================================================================

class TestIntegration:
    @pytest.mark.asyncio
    async def test_end_to_end_offline(self):
        mother = MotherAgent(working_folder="/tmp/test_e2e", timeout_seconds=60, llm=MockProvider())
        spec = "Create a simple web app with a Python backend and React frontend"
        result = await mother.run(spec)
        assert result["status"] == "success"
        assert "tasks_completed" in result
        assert "execution_time" in result
        assert result["execution_time"] < 60
        mother.lock_manager.cleanup()


# ============================================================================
# RUN
# ============================================================================

def run_tests():
    print("\n" + "="*80)
    print("MOTHER-AGENT SYSTEM TEST SUITE")
    print("No API keys needed - uses MockProvider")
    print("="*80 + "\n")
    exit_code = pytest.main([__file__, "-v", "--tb=short", "--color=yes"])
    return exit_code


if __name__ == "__main__":
    sys.exit(run_tests())
