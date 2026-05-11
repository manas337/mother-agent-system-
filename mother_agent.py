"""
Mother Agent - Orchestrator for Multi-Agent Software Development
Handles task decomposition, DAG-based agent creation/destruction, monitoring, and output consolidation
"""

import asyncio
import json
import os
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime

from llm_provider import create_provider, load_llm_config, LLMProvider, extract_json
from task_manager import DAGManager, DAGTask, TaskExecutor, TaskStatus
from file_lock import LockManager


class AgentRole(Enum):
    BACKEND = "backend_developer"
    FRONTEND = "frontend_developer"
    UX_DESIGNER = "ux_designer"
    DEVOPS = "devops_engineer"
    QA = "qa_tester"
    SUPERVISOR = "supervisor"


@dataclass
class AgentConfig:
    identity: str
    context: str
    tools: List[str]
    mission: str


@dataclass
class SubAgent:
    agent_id: str
    role: AgentRole
    config: AgentConfig
    status: TaskStatus
    output: Optional[str] = None
    retry_count: int = 0
    created_at: float = 0.0
    last_health_check: float = 0.0


class MotherAgent:
    def __init__(self, working_folder: str, timeout_seconds: int = 300, llm: Optional[LLMProvider] = None):
        if llm:
            self.llm = llm
        else:
            llm_config = load_llm_config()
            self.llm: LLMProvider = create_provider(llm_config)
        self.working_folder = working_folder
        self.timeout_seconds = timeout_seconds
        self.start_time = None

        self.agents: Dict[str, SubAgent] = {}
        self.dag = DAGManager()
        self.lock_manager = LockManager(working_folder)

        self.health_check_interval = 0.2
        self.max_retries = 5
        self._role_mapping = {
            "BACKEND": AgentRole.BACKEND,
            "FRONTEND": AgentRole.FRONTEND,
            "UX_DESIGNER": AgentRole.UX_DESIGNER,
            "DEVOPS": AgentRole.DEVOPS,
            "QA": AgentRole.QA,
            "SUPERVISOR": AgentRole.SUPERVISOR,
        }

    def _check_timeout(self) -> bool:
        if self.start_time is None:
            return False
        return (time.time() - self.start_time) > self.timeout_seconds

    async def validate_and_clarify_spec(self, user_spec: str) -> Dict:
        print("Mother: Validating project specification...")
        prompt = f"""You are analyzing a software project specification to ensure it's complete.

User Specification:
{user_spec}

Analyze if this specification contains:
1. Clear project goal/purpose
2. Required features and functionality
3. Technology stack preferences (if any)
4. Target platform (web, mobile, desktop, etc.)
5. Any constraints or requirements

Return ONLY a raw JSON object. No markdown, no explanation, no code fences. Just the JSON.

{{
    "is_complete": true/false,
    "missing_elements": ["list of missing critical info"],
    "clarifying_questions": ["questions to ask user"],
    "interpreted_spec": {{
        "project_type": "web_app|mobile_app|api|etc",
        "core_features": ["feature1", "feature2"],
        "tech_stack": {{"frontend": "...", "backend": "..."}},
        "complexity": "simple|moderate|complex"
    }}
}}
"""
        result_raw = self.llm.generate(prompt, max_tokens=2000)
        result = extract_json(result_raw)

        if not isinstance(result, dict):
            return {"project_type": "unknown", "core_features": [], "tech_stack": {}, "complexity": "simple"}

        is_complete = result.get("is_complete", True)
        if not is_complete and result.get("clarifying_questions"):
            print("Mother needs clarification:")
            for q in result["clarifying_questions"]:
                print(f"   - {q}")

        return result.get("interpreted_spec", {
            "project_type": "web_app",
            "core_features": ["implement user requirements"],
            "tech_stack": {"frontend": "react", "backend": "python"},
            "complexity": "simple"
        })

    async def decompose_into_tasks(self, validated_spec: Dict) -> List[DAGTask]:
        print("Mother: Decomposing project into subtasks...")
        prompt = f"""You are decomposing a software project into parallel subtasks for a multi-agent team.

Project Specification:
{json.dumps(validated_spec, indent=2)}

Available Roles:
- BACKEND: API development, database, server logic
- FRONTEND: UI implementation, client-side logic
- UX_DESIGNER: User experience, wireframes, design system
- DEVOPS: Deployment, CI/CD, infrastructure
- QA: Testing strategy, test cases

Create a task breakdown that:
1. Assigns non-overlapping responsibilities
2. Identifies dependencies between tasks
3. Can be completed in parallel where possible
4. Is specific enough for autonomous execution

Return JSON array of tasks:
[
    {{
        "task_id": "task_1",
        "description": "Detailed task description",
        "role": "BACKEND|FRONTEND|UX_DESIGNER|DEVOPS|QA",
        "dependencies": ["task_id of prerequisites"],
        "deliverables": ["specific outputs expected"]
    }}
]

Limit to 2-4 tasks for V0 (5-minute constraint).

Return ONLY a raw JSON array. No markdown, no explanation, no code fences. Just the JSON array.
"""
        result_raw = self.llm.generate(prompt, max_tokens=2000)
        task_specs = extract_json(result_raw)

        if not isinstance(task_specs, list):
            task_specs = task_specs.get("tasks", task_specs.get("task_specs", [])) if isinstance(task_specs, dict) else []

        tasks = []
        for spec in task_specs:
            if not isinstance(spec, dict):
                continue
            task = DAGTask(
                task_id=spec.get("task_id", f"task_{len(tasks) + 1}"),
                description=spec.get("description", "Implement required functionality"),
                role=spec.get("role", "BACKEND"),
                dependencies=spec.get("dependencies", []),
                max_retries=self.max_retries
            )
            tasks.append(task)
            self.dag.add_task(task)

        print(f"Mother: Created {len(tasks)} subtasks")
        return tasks

    def create_agent(self, task: DAGTask, role: AgentRole, project_context: str) -> SubAgent:
        agent_id = f"agent_{task.task_id}_{int(time.time() * 1000)}"
        config = AgentConfig(
            identity=f"""You are a {role.value} in a multi-agent software development team.
Your expertise: {self._get_role_expertise(role)}
Your working style: Autonomous, detail-oriented, collaborative.""",

            context=f"""Project Context:
{project_context}

Working Folder: {self.working_folder}
Collaboration: You can request context from other agents via inter_agent_mcp
Time Constraint: Complete your task efficiently within the 5-minute project window.""",

            tools=self._get_role_tools(role),

            mission=f"""Your Mission:
{task.description}

Deliverables Required:
- Working code/designs in {self.working_folder}
- Clear documentation of your work
- Status updates for health monitoring

Dependencies: {task.dependencies if task.dependencies else 'None - you can start immediately'}
"""
        )

        agent = SubAgent(
            agent_id=agent_id,
            role=role,
            config=config,
            status=TaskStatus.PENDING,
            created_at=time.time()
        )

        self.agents[agent_id] = agent
        task.assigned_agent = agent_id
        print(f"Mother: Created {role.value} agent ({agent_id})")
        return agent

    def _get_role_expertise(self, role: AgentRole) -> str:
        expertise_map = {
            AgentRole.BACKEND: "API design, database modeling, server-side logic, Python/Node.js",
            AgentRole.FRONTEND: "React/Vue, responsive UI, state management, TypeScript",
            AgentRole.UX_DESIGNER: "User flows, wireframing, design systems, accessibility",
            AgentRole.DEVOPS: "Docker, CI/CD, infrastructure as code, deployment",
            AgentRole.QA: "Test strategy, unit/integration tests, quality assurance",
            AgentRole.SUPERVISOR: "Code review, functional testing, work validation, integration verification"
        }
        return expertise_map.get(role, "General software development")

    def _get_role_tools(self, role: AgentRole) -> List[str]:
        tools_map = {
            AgentRole.BACKEND: ["file_operations", "code_execution", "inter_agent_mcp", "ghost_mcp"],
            AgentRole.FRONTEND: ["file_operations", "code_execution", "inter_agent_mcp", "ghost_mcp"],
            AgentRole.UX_DESIGNER: ["file_operations", "design_tools", "inter_agent_mcp", "ghost_mcp"],
            AgentRole.DEVOPS: ["file_operations", "deployment_tools", "inter_agent_mcp", "ghost_mcp"],
            AgentRole.QA: ["file_operations", "testing_tools", "inter_agent_mcp", "ghost_mcp"],
            AgentRole.SUPERVISOR: ["file_operations", "testing_tools", "inter_agent_mcp", "ghost_mcp"]
        }
        return tools_map.get(role, ["file_operations", "ghost_mcp"])

    def infer_role(self, role_str: str) -> AgentRole:
        return self._role_mapping.get(role_str.upper(), AgentRole.BACKEND)

    @staticmethod
    def _compile_check(working_folder: str) -> list:
        import ast
        errors = []
        for f in Path(working_folder).rglob("*.py"):
            if ".locks" in f.parts:
                continue
            try:
                ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError as e:
                errors.append(f"{f.name}: {e.msg} (line {e.lineno})")
        for f in Path(working_folder).rglob("*.html"):
            if ".locks" in f.parts:
                continue
            content = f.read_text(encoding="utf-8")
            if not content.strip().lower().endswith("</html>"):
                errors.append(f"{f.name}: missing closing </html> tag")
            if "<script" in content.lower() and "</script>" not in content.lower():
                errors.append(f"{f.name}: unclosed <script> tag")
        for f in Path(working_folder).rglob("*.js"):
            if ".locks" in f.parts:
                continue
            try:
                ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError as e:
                errors.append(f"{f.name}: {e.msg} (line {e.lineno})")
        return errors

    async def execute_agent_task(self, task: DAGTask) -> bool:
        role = self.infer_role(task.role)
        agent = self.create_agent(task, role, "Project context from decomposition")
        print(f"Agent {agent.agent_id}: Starting task execution...")
        agent.status = TaskStatus.IN_PROGRESS

        full_prompt = f"""{agent.config.identity}

{agent.config.context}

{agent.config.mission}

Available Tools: {', '.join(agent.config.tools)}

Execute your task. Return ONLY a raw JSON object. No markdown, no code fences, no explanation. Just the JSON.

Required structure:
{{
    "status": "completed|blocked|failed",
    "deliverables": {{"relative/file/path.py": "file content here"}},
    "summary": "What I did",
    "blockers": ["any issues"]
}}

CRITICAL: Your deliverables will be written to the working folder. Include ALL file content.
"""
        try:
            result_raw = self.llm.generate(full_prompt, max_tokens=10000)
            result = extract_json(result_raw)
            if not isinstance(result, dict):
                print(f"   Expected dict, got {type(result).__name__}, retrying...")
                result = {"status": "failed", "summary": f"LLM returned {type(result).__name__} instead of dict"}
                agent.output = json.dumps(result)
                agent.status = TaskStatus.FAILED
                self.dag.mark_failed(task.task_id)
                return False

            if result["status"] == "completed":
                deliverables = result.get("deliverables", {})
                written_files = []
                if isinstance(deliverables, dict):
                    for file_path, content in deliverables.items():
                        full_path = Path(self.working_folder) / file_path
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        async with self.lock_manager.lock_resource(str(full_path)):
                            full_path.write_text(content, encoding="utf-8")
                        written_files.append(file_path)
                        print(f"   Wrote {file_path} ({len(content)} bytes)")

                result["written_files"] = written_files
                agent.output = json.dumps(result)
                task.deliverable_paths = written_files
                agent.status = TaskStatus.COMPLETED
                self.dag.mark_completed(task.task_id, json.dumps(result))
                compile_errors = self._compile_check(self.working_folder)
                if compile_errors:
                    print(f"   Compilation issues found:")
                    for err in compile_errors:
                        print(f"     - {err}")
                else:
                    print(f"   All files pass compilation check")
                print(f"Agent {agent.agent_id}: Task completed successfully")
                return True
            else:
                self.dag.mark_failed(task.task_id)
                print(f"Agent {agent.agent_id}: Task blocked or failed - {result.get('summary')}")
                return False
        except Exception as e:
            self.dag.mark_failed(task.task_id)
            print(f"Agent {agent.agent_id}: Execution error - {str(e)}")
            traceback.print_exc()
            return False

    async def supervisor_validate(self, task: DAGTask) -> bool:
        if not task.output:
            print(f"Supervisor: No output to validate for {task.task_id}")
            return False

        print(f"Supervisor: Validating output for {task.task_id}...")
        prompt = f"""You are a Supervisor validating work submitted by an agent.

Task: {task.description}
Agent Output:
{task.output}

Validate that:
1. The deliverables are complete and functional
2. The code follows best practices
3. The task requirements are fully met

Return JSON:
{{
    "is_valid": true/false,
    "issues": ["list of issues found"],
    "quality_score": 0.0-1.0,
    "recommendations": ["improvement suggestions"]
}}
"""
        try:
            result = self.llm.generate_json(prompt, max_tokens=2000)
            if not result.get("is_valid", False):
                print(f"Supervisor: Validation FAILED for {task.task_id}")
                print(f"   Issues: {result.get('issues', [])}")
                return False
            print(f"Supervisor: Validation PASSED for {task.task_id}")
            return True
        except Exception as e:
            print(f"Supervisor: Validation error - {str(e)}")
            return False

    async def handle_failure(self, task: DAGTask):
        print(f"Mother: Handling failure for task {task.task_id}...")
        if task.retry_count < self.max_retries:
            task.retry_count += 1
            print(f"   Retry {task.retry_count}/{self.max_retries}")
            task.status = TaskStatus.PENDING
            self.dag.add_task(task)
        else:
            print(f"   Max retries exceeded for {task.task_id}")

    def destroy_agent(self, agent_id: str):
        if agent_id in self.agents:
            print(f"Mother: Destroying agent {agent_id}")
            del self.agents[agent_id]

    @staticmethod
    def _is_stub_json(content: str) -> bool:
        if not content.strip().startswith("{"):
            return False
        try:
            import json
            parsed = json.loads(content)
            if isinstance(parsed, dict) and len(str(parsed)) < 100:
                vals = set(str(v).lower() for v in parsed.values())
                keys = set(k.lower() for k in parsed.keys())
                code_keywords = {"import", "function", "class ", "def ", "export", "<html", "require(", "from "}
                if not any(kw in content.lower() for kw in code_keywords):
                    return True
            return False
        except json.JSONDecodeError:
            return False

    @staticmethod
    def _filter_output_files(files: dict) -> dict:
        valid_exts = {".html", ".htm", ".js", ".jsx", ".tsx", ".ts", ".css", ".scss",
                      ".py", ".sql", ".sh", ".bat", ".ps1",
                      ".md", ".rst", ".txt",
                      ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".conf",
                      ".env", ".gitignore", ".dockerfile"}
        filtered = {}
        removed = []
        for path, content in files.items():
            if not content:
                removed.append(f"{path} (empty)")
                continue
            ext = Path(path).suffix.lower()
            if not ext:
                removed.append(f"{path} (no extension)")
                continue
            if ext not in valid_exts:
                removed.append(f"{path} (unwanted extension .{ext})")
                continue
            if MotherAgent._is_stub_json(content):
                removed.append(f"{path} (stub JSON)")
                continue
            filtered[path] = content
        if removed:
            print(f"   Scrubbed {len(removed)} non-relevant files:")
            for r in removed:
                print(f"     - {r}")
        return filtered

    async def consolidate_outputs(self, user_spec: str = "") -> Dict:
        print("Mother: Consolidating agent outputs...")

        outputs = {}
        for task_id, task in self.dag.tasks.items():
            if task.status == TaskStatus.COMPLETED and task.output:
                outputs[task_id] = json.loads(task.output)

        work_dir = Path(self.working_folder)
        wants_single_file = "single" in user_spec.lower() and ("index.html" in user_spec.lower() or ".html" in user_spec.lower())

        if outputs:
            if wants_single_file:
                merge_prompt = f"""You MUST return a SINGLE HTML file. NO splitting across multiple files.

The following outputs were produced by different agents. Merge them ALL into ONE complete index.html:

Agent Outputs:
{json.dumps(outputs, indent=2)[:8000]}

RULES:
- Output a SINGLE file: index.html
- ALL CSS goes inside <style> tags in the <head>
- ALL JavaScript goes inside <script> tags at the end of <body>
- Do NOT create any other files
- Do NOT include any explanation or markdown

Return ONLY this JSON:
{{"files": {{"index.html": "the complete merged HTML here"}}, "readme": "Single page application", "summary": "Merged into single index.html"}}
"""
            else:
                merge_prompt = f"""You are consolidating outputs from {len(outputs)} specialized agents into a final software deliverable.

Agent Outputs:
{json.dumps(outputs, indent=2)[:8000]}

Create a unified project structure with:
1. All code organized properly
2. README with setup instructions
3. Integration of components

Return JSON with complete file structure:
{{
    "files": {{
        "path/to/file": "content",
        ...
    }},
    "readme": "Complete README content",
    "summary": "What was built and how to use it"
}}
"""
            try:
                merged = self.llm.generate_json(merge_prompt, max_tokens=8000)
                if merged.get("files"):
                    merged["files"] = self._filter_output_files(merged["files"])
                    num = len(merged["files"])
                    print(f"Mother: LLM consolidation created {num} file(s)")

                    for f in work_dir.rglob("*"):
                        if f.is_file() and ".locks" not in f.parts:
                            try:
                                f.unlink()
                            except Exception:
                                pass
                    for fp, content in merged["files"].items():
                        full = work_dir / fp
                        full.parent.mkdir(parents=True, exist_ok=True)
                        full.write_text(content, encoding="utf-8")
                    if merged.get("readme"):
                        (work_dir / "README.md").write_text(merged["readme"], encoding="utf-8")

                    print(f"Mother: Wrote merged files to {work_dir}")
                    return merged
                print("Mother: LLM returned no files, falling back to disk scan")
            except Exception as e:
                print(f"Mother: LLM consolidation error ({e}), falling back to disk scan")

        if work_dir.exists():
            all_files = {}
            for f in work_dir.rglob("*"):
                if not f.is_file():
                    continue
                if ".locks" in f.parts:
                    continue
                if f.name.startswith("."):
                    continue
                rel = f.relative_to(work_dir).as_posix()
                try:
                    all_files[rel] = f.read_text(encoding="utf-8")
                except Exception:
                    all_files[rel] = f"[binary file: {f.stat().st_size} bytes]"

            all_files = self._filter_output_files(all_files)

            if wants_single_file and len(all_files) > 1:
                print(f"Mother: User requested single file, merging {len(all_files)} on-disk files...")
                merge_prompt = f"""Merge all of the following into ONE index.html with CSS in <style> and JS in <script>.

Files:
{json.dumps(all_files, indent=2)[:6000]}

Return: {{"files": {{"index.html": "merged content"}}, "summary": "...", "readme": "..."}}
"""
                try:
                    merged = self.llm.generate_json(merge_prompt, max_tokens=8000)
                    if merged.get("files") and "index.html" in str(merged.get("files", {})):
                        return merged
                except Exception:
                    pass

            if all_files:
                summary_lines = []
                for path, content in all_files.items():
                    summary_lines.append(f"  {path} ({len(content)} bytes)")
                summary = "\n".join(summary_lines)
                print(f"Mother: Returning {len(all_files)} files from disk")
                return {
                    "files": all_files,
                    "readme": all_files.get("README.md", f"# Project\n\nGenerated by Mother-Agent\n\n## Files\n{summary}"),
                    "summary": f"Generated {len(all_files)} files"
                }

        return {"files": {}, "readme": "", "summary": "No outputs to consolidate"}

    async def execute_single_file_task(self, task: DAGTask, shared_file: str) -> bool:
        role = self.infer_role(task.role)
        agent = self.create_agent(task, role, "Project context from decomposition")
        print(f"Agent {agent.agent_id}: Starting task execution (adding to {shared_file})...")
        agent.status = TaskStatus.IN_PROGRESS

        existing = ""
        shared_path = Path(self.working_folder) / shared_file
        if shared_path.exists():
            existing = shared_path.read_text(encoding="utf-8")

        if existing:
            context_note = f"\n\nThe current state of {shared_file} is:\n```\n{existing[:3000]}\n```\nAdd your part to this file. Do NOT delete existing content."
        else:
            context_note = f"\n\nYou are creating the initial version of {shared_file}. Start with a complete HTML document structure."

        full_prompt = f"""{agent.config.identity}

{agent.config.context}

{agent.config.mission}

Available Tools: {', '.join(agent.config.tools)}
{context_note}

Return ONLY a raw JSON object. No markdown, no code fences, no explanation.

Required structure:
{{
    "status": "completed|blocked|failed",
    "file": "{shared_file}",
    "content": "the COMPLETE updated file content including ALL existing code plus your additions",
    "summary": "What I added",
    "blockers": []
}}

CRITICAL: Return the FULL content of {shared_file}, not just your additions. Include everything that was already there plus your new code.
"""
        try:
            result_raw = self.llm.generate(full_prompt, max_tokens=10000)
            result = extract_json(result_raw)
            if not isinstance(result, dict):
                result = {"status": "failed", "summary": f"LLM returned {type(result).__name__} instead of dict"}

            if result.get("status") == "completed" and result.get("content"):
                content = result["content"]
                async with self.lock_manager.lock_resource(str(shared_path)):
                    shared_path.parent.mkdir(parents=True, exist_ok=True)
                    shared_path.write_text(content, encoding="utf-8")
                agent.output = json.dumps(result)
                agent.status = TaskStatus.COMPLETED
                task.deliverable_paths = [shared_file]
                self.dag.mark_completed(task.task_id, json.dumps(result))
                print(f"   Updated {shared_file} ({len(content)} bytes)")
                return True
            else:
                print(f"   Task {task.task_id} failed or returned no content")
                self.dag.mark_failed(task.task_id)
                return False
        except Exception as e:
            print(f"   Task {task.task_id} error: {e}")
            self.dag.mark_failed(task.task_id)
            return False

    async def run(self, user_spec: str) -> Dict:
        self.start_time = time.time()
        print(f"\n{'='*60}")
        print(f"MOTHER AGENT: Starting orchestration")
        print(f"{'='*60}\n")

        work_dir = Path(self.working_folder)
        if work_dir.exists():
            for f in work_dir.rglob("*"):
                if f.is_file() and ".locks" not in f.parts and not f.name.startswith("."):
                    try:
                        f.unlink()
                    except Exception:
                        pass
            for d in sorted(work_dir.rglob("*"), key=lambda p: len(str(p)), reverse=True):
                if d.is_dir() and ".locks" not in d.parts and d != work_dir:
                    try:
                        d.rmdir()
                    except Exception:
                        pass
            print("Mother: Cleaned working folder from previous run")

        try:
            validated_spec = await self.validate_and_clarify_spec(user_spec)
            if self._check_timeout():
                raise TimeoutError("Timeout during spec validation")

            tasks = await self.decompose_into_tasks(validated_spec)

            print("\nMother: Using serial single-file execution mode")
            print("Mother: Agents will write to index.html one at a time\n")
            shared_file = "index.html"
            shared_path = Path(self.working_folder) / shared_file
            batch_retries = 0
            max_batch_retries = 3

            while batch_retries < max_batch_retries:
                if shared_path.exists():
                    shared_path.unlink()
                for t in tasks:
                    t.status = TaskStatus.PENDING
                    t.retry_count = 0
                    t.output = None

                all_succeeded = True
                for task in tasks:
                    success = await self.execute_single_file_task(task, shared_file)
                    if not success:
                        all_succeeded = False
                        break

                if not all_succeeded:
                    batch_retries += 1
                    print(f"\n   Batch failed, retrying ({batch_retries}/{max_batch_retries})...")
                    continue

                print(f"\nSupervisor: Validating final {shared_file}...")
                valid = True
                for task in tasks:
                    if task.status == TaskStatus.COMPLETED:
                        v = await self.supervisor_validate(task)
                        if not v:
                            valid = False
                            break

                if valid:
                    print(f"Supervisor: All tasks validated successfully")
                    break
                else:
                    batch_retries += 1
                    print(f"\n   Supervisor rejected work, retrying batch ({batch_retries}/{max_batch_retries})...")

            final_output = {"files": {}, "readme": "", "summary": ""}
            if shared_path.exists():
                content = shared_path.read_text(encoding="utf-8")
                final_output = {
                    "files": {shared_file: content},
                    "readme": f"# Project\n\nSingle-page application generated by Mother-Agent\n\nOpen {shared_file} in a browser.",
                    "summary": f"Generated {shared_file} ({len(content)} bytes)"
                }

            project_dir = Path(self.working_folder)
            project_dir.mkdir(parents=True, exist_ok=True)
            files = final_output.get("files", {})
            for file_path, content in files.items():
                fp = project_dir / file_path
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text(content, encoding="utf-8")
            readme = final_output.get("readme", "")
            if readme:
                (project_dir / "README.md").write_text(readme, encoding="utf-8")

            print(f"\nMother: Project saved to {project_dir}")
            print(f"Mother: {len(files)} files written")

            print(f"\nMother: Destroying all agents...")
            for agent_id in list(self.agents.keys()):
                self.destroy_agent(agent_id)

            self.lock_manager.cleanup()

            execution_time = time.time() - self.start_time
            print(f"\n{'='*60}")
            print(f"MOTHER AGENT: Orchestration complete")
            print(f"Time: {execution_time:.2f} seconds")
            print(f"{'='*60}\n")

            return {
                "status": "success",
                "execution_time": execution_time,
                "tasks_completed": len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
                "total_tasks": len(tasks),
                "output": final_output
            }

        except TimeoutError as e:
            print(f"TIMEOUT: {str(e)}")
            for agent_id in list(self.agents.keys()):
                self.destroy_agent(agent_id)
            return {"status": "timeout", "error": str(e)}

        except Exception as e:
            print(f"FATAL ERROR: {str(e)}")
            traceback.print_exc()
            for agent_id in list(self.agents.keys()):
                self.destroy_agent(agent_id)
            return {"status": "error", "error": str(e)}


async def main():
    import sys

    if len(sys.argv) > 1:
        user_spec = " ".join(sys.argv[1:])
    else:
        user_spec = """
    Create a simple task management web application with:
    - Backend API in Python (Flask)
    - Frontend in React
    - Features: Create tasks, mark as complete, delete tasks
    - SQLite database for persistence
    """

    working_folder = os.getenv("WORKING_FOLDER", str(Path.cwd() / "output"))
    Path(working_folder).mkdir(parents=True, exist_ok=True)

    mother = MotherAgent(
        working_folder=working_folder,
        timeout_seconds=86400
    )

    print(f"Output will be saved to: {working_folder}")

    print(f"Prompt: {user_spec[:100]}...")
    result = await mother.run(user_spec)
    print("\nFinal Result:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
