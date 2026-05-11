"""
DAG Execution Manager - Handles dependency-based task ordering and execution
"""

import asyncio
from typing import Dict, List, Set, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(Enum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DAGTask:
    task_id: str
    description: str
    role: str
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    output: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    deliverable_paths: List[str] = field(default_factory=list)


class DAGManager:
    """
    Manages task dependencies and execution order using a DAG.
    Ensures tasks only execute when their dependencies are completed.
    """

    def __init__(self):
        self.tasks: Dict[str, DAGTask] = {}
        self._adjacency: Dict[str, List[str]] = {}
        self._reverse_adjacency: Dict[str, List[str]] = {}

    def add_task(self, task: DAGTask):
        self.tasks[task.task_id] = task
        self._adjacency.setdefault(task.task_id, [])
        self._reverse_adjacency.setdefault(task.task_id, [])
        if task.dependencies:
            for dep_id in task.dependencies:
                self._reverse_adjacency.setdefault(task.task_id, []).append(dep_id)
                self._adjacency.setdefault(dep_id, []).append(task.task_id)
        for existing_id, existing_task in list(self.tasks.items()):
            if task.task_id in existing_task.dependencies:
                self._adjacency.setdefault(task.task_id, []).append(existing_id)
                self._reverse_adjacency.setdefault(existing_id, []).append(task.task_id)

    def get_ready_tasks(self) -> List[DAGTask]:
        ready = []
        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            if all(
                self.tasks[dep].status == TaskStatus.COMPLETED
                for dep in task.dependencies
                if dep in self.tasks
            ):
                task.status = TaskStatus.READY
                ready.append(task)
        return ready

    def mark_completed(self, task_id: str, output: Optional[str] = None):
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.COMPLETED
            self.tasks[task_id].output = output

    def mark_failed(self, task_id: str):
        if task_id in self.tasks:
            self.tasks[task_id].status = TaskStatus.FAILED

    def has_unfinished_tasks(self) -> bool:
        return any(
            t.status in (TaskStatus.PENDING, TaskStatus.READY, TaskStatus.IN_PROGRESS)
            for t in self.tasks.values()
        )

    def get_execution_order(self) -> List[List[DAGTask]]:
        layers = []
        remaining = set(self.tasks.keys())
        completed = set()

        while remaining:
            layer = []
            for task_id in list(remaining):
                deps = set(self._reverse_adjacency.get(task_id, []))
                if deps.issubset(completed) or not deps:
                    layer.append(self.tasks[task_id])
            if not layer:
                break
            layers.append(layer)
            for task in layer:
                remaining.discard(task.task_id)
                completed.add(task.task_id)

        return layers

    def has_cycle(self) -> bool:
        visited = set()
        rec_stack = set()

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            for neighbor in self._adjacency.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for task_id in self.tasks:
            if task_id not in visited:
                if dfs(task_id):
                    return True
        return False


class TaskExecutor:
    """
    Executes tasks according to DAG ordering with monitoring and retries.
    """

    def __init__(self, dag: DAGManager,
                 execute_fn: Callable[[DAGTask], Awaitable[bool]],
                 poll_interval: float = 0.1,
                 task_timeout: float = 600.0):
        self.dag = dag
        self.execute_fn = execute_fn
        self.poll_interval = poll_interval
        self.task_timeout = task_timeout

    async def run(self) -> Dict[str, str]:
        if self.dag.has_cycle():
            raise ValueError("DAG contains a cycle - cannot execute")

        results: Dict[str, str] = {}

        while self.dag.has_unfinished_tasks():
            ready_tasks = self.dag.get_ready_tasks()
            if not ready_tasks:
                await asyncio.sleep(self.poll_interval)
                continue

            tasks = []
            for task in ready_tasks:
                task.status = TaskStatus.IN_PROGRESS
                tasks.append(self._execute_with_retry(task))

            completed = await asyncio.gather(*tasks, return_exceptions=True)
            for task, result in zip(ready_tasks, completed):
                if isinstance(result, Exception):
                    self.dag.mark_failed(task.task_id)
                    results[task.task_id] = f"error: {result}"
                elif result:
                    results[task.task_id] = "completed"
                else:
                    self.dag.mark_failed(task.task_id)
                    results[task.task_id] = "failed"

        return results

    async def _execute_with_retry(self, task: DAGTask) -> bool:
        for attempt in range(task.max_retries):
            try:
                success = await asyncio.wait_for(
                    self.execute_fn(task),
                    timeout=self.task_timeout
                )
                if success:
                    return True
            except asyncio.TimeoutError:
                task.retry_count += 1
                print(f"   Task {task.task_id} timed out (attempt {attempt + 1}/{task.max_retries})")
                if attempt >= task.max_retries - 1:
                    raise
            except Exception as e:
                task.retry_count += 1
                if attempt < task.max_retries - 1:
                    continue
                raise e
        return False
