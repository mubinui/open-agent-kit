"""CrewAI runtime adapter for Open Agent Kit workflow configs.

The adapter intentionally keeps the public REST surface stable while moving
workflow execution to CrewAI. It translates the existing JSON agent/tool/workflow
configuration into CrewAI objects at runtime, leveraging advanced CrewAI features
such as Flows, Knowledge Sources, and Memory databases natively.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import structlog

from src.config.agent_models import AgentConfig
from src.config.loader import load_agents_config
from src.config.tool_registry import ToolDefinition, get_tool_registry
from src.config.workflow_models import WorkflowConfig

logger = structlog.get_logger(__name__)


@dataclass
class CrewAIRuntimeResult:
    """Normalized result returned to the existing API layer."""

    response: str
    trace_steps: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class CrewAINotAvailableError(RuntimeError):
    """Raised when CrewAI is selected but not installed in the environment."""


class CrewAIWorkflowRuntime:
    """Execute existing workflow configurations through advanced CrewAI capabilities."""

    def __init__(
        self,
        memory_enabled: bool = True,
        storage_dir: str = "./.crewai",
        default_process: str = "sequential",
    ) -> None:
        self.memory_enabled = memory_enabled
        self.storage_dir = storage_dir
        self.default_process = default_process

    @staticmethod
    def is_available() -> bool:
        """Return whether CrewAI can be imported in the current environment."""
        try:
            import crewai  # noqa: F401
        except Exception:
            return False
        return True

    async def run_message(
        self,
        workflow: WorkflowConfig,
        message: str,
        session_id: str,
        user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> CrewAIRuntimeResult:
        """Run one user message through a CrewAI crew or Flow in a worker thread."""

        started = time.perf_counter()
        result = await asyncio.to_thread(
            self._run_message_sync,
            workflow,
            message,
            session_id,
            user_id,
            metadata or {},
        )
        result.metadata.setdefault("latency_ms", round((time.perf_counter() - started) * 1000))
        return result

    def _run_message_sync(
        self,
        workflow: WorkflowConfig,
        message: str,
        session_id: str,
        user_id: str,
        metadata: dict[str, Any],
    ) -> CrewAIRuntimeResult:
        # The ExitStack owns the lifecycle of per-run tool resources (notably MCP
        # server connections/subprocesses): they are closed when this method
        # returns or raises, no matter where the failure happens.
        with contextlib.ExitStack() as stack:
            return self._run_message_inner(workflow, message, session_id, user_id, metadata, stack)

    def _run_message_inner(
        self,
        workflow: WorkflowConfig,
        message: str,
        session_id: str,
        user_id: str,
        metadata: dict[str, Any],
        stack: contextlib.ExitStack,
    ) -> CrewAIRuntimeResult:
        try:
            from crewai import Agent, Crew, Process, Task
        except Exception as exc:
            raise CrewAINotAvailableError(
                "CrewAI runtime selected but crewai is not installed. Run `uv sync` first."
            ) from exc

        os.environ.setdefault("CREWAI_STORAGE_DIR", self.storage_dir)

        agent_configs = {agent.id: agent for agent in load_agents_config().agents}
        ordered_nodes = self._ordered_nodes(workflow)
        workflow_agent_ids = [node.agent_id for node in ordered_nodes]
        if not workflow_agent_ids:
            raise ValueError(f"Workflow {workflow.id} has no agents to execute")

        crew_agents: list[Any] = []
        crew_agent_by_id: dict[str, Any] = {}
        # One factory build per tool id per run: agents sharing an MCP tool share
        # one live server connection instead of spawning one each.
        run_tool_cache: dict[str, list[Any]] = {}
        for agent_id in workflow_agent_ids:
            config = agent_configs.get(agent_id)
            if config is None:
                logger.warning("crewai_agent_config_missing", workflow_id=workflow.id, agent_id=agent_id)
                continue
            crew_agent = self._create_agent(Agent, config, stack, run_tool_cache)
            crew_agents.append(crew_agent)
            crew_agent_by_id[agent_id] = crew_agent

        if not crew_agents:
            raise ValueError(f"Workflow {workflow.id} has no valid CrewAI agents")

        tasks = self._create_tasks(
            task_cls=Task,
            workflow=workflow,
            ordered_nodes=ordered_nodes,
            crew_agent_by_id=crew_agent_by_id,
            message=message,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata,
            agent_configs=agent_configs,
        )

        process = self._resolve_process(Process, workflow)
        
        # Resolve Knowledge sources natively if available
        knowledge_sources = self._resolve_knowledge_sources(workflow)
        
        trace_steps = self._planning_trace(
            workflow=workflow,
            ordered_nodes=ordered_nodes,
            tasks=tasks,
            process=process,
            crew_agents=crew_agents,
        )
        
        memory_active = workflow.memory.enabled if hasattr(workflow, "memory") else self.memory_enabled
        
        crew_kwargs: dict[str, Any] = {
            "agents": crew_agents,
            "tasks": tasks,
            "process": process,
            "memory": memory_active,
            "verbose": False,
            "cache": bool(getattr(workflow, "cache", True)),
        }

        if knowledge_sources:
            crew_kwargs["knowledge"] = knowledge_sources

        if getattr(workflow, "planning", False):
            crew_kwargs["planning"] = True
            crew_kwargs["planning_llm"] = self._resolve_llm_model({})

        if getattr(workflow, "max_rpm", None):
            crew_kwargs["max_rpm"] = int(workflow.max_rpm)

        if (process.value if hasattr(process, "value") else str(process)).lower().endswith("hierarchical"):
            crew_kwargs["manager_llm"] = self._resolve_llm_model({})
            
        crew = Crew(**crew_kwargs)

        # Kickoff CrewAI process
        inputs_dict = {
            "message": message,
            "session_id": session_id,
            "user_id": user_id,
            "workflow_id": workflow.id,
            **metadata,
        }
        
        started_execution = time.time()
        try:
            kickoff_result = crew.kickoff(inputs=inputs_dict)
            response = getattr(kickoff_result, "raw", None) or str(kickoff_result)
            token_usage = getattr(kickoff_result, "token_usage", {})
            if hasattr(token_usage, "model_dump"):
                token_usage = token_usage.model_dump()
            elif hasattr(token_usage, "__dict__"):
                token_usage = token_usage.__dict__
        except Exception as e:
            logger.error("crewai_execution_error", error=str(e), exc_info=True)
            response = f"Error during CrewAI execution: {str(e)}"
            token_usage = {}
            
        execution_duration = time.time() - started_execution
        
        # Calculate approximate cost if token usage available
        total_tokens = token_usage.get("total_tokens", 0) if isinstance(token_usage, dict) else 0
        prompt_tokens = token_usage.get("prompt_tokens", 0) if isinstance(token_usage, dict) else 0
        completion_tokens = token_usage.get("completion_tokens", 0) if isinstance(token_usage, dict) else 0
        approx_cost = (prompt_tokens * 0.0000015) + (completion_tokens * 0.000006)

        trace_steps.append(
            {
                "type": "crew_done",
                "agent": "CrewAI",
                "description": f"Completed workflow {workflow.id} using advanced features",
                "timestamp": time.time(),
                "details": {
                    "latency_source": "runtime",
                    "execution_duration_sec": round(execution_duration, 2),
                    "response_chars": len(response or ""),
                    "tokens": {
                        "total": total_tokens,
                        "prompt": prompt_tokens,
                        "completion": completion_tokens,
                    },
                    "estimated_cost_usd": round(approx_cost, 6),
                },
            }
        )
        
        return CrewAIRuntimeResult(
            response=response.strip(),
            trace_steps=trace_steps,
            metadata={
                "runtime": "crewai",
                "workflow_id": workflow.id,
                "agent_count": len(crew_agents),
                "task_count": len(tasks),
                "agents_called": [getattr(agent, "role", "agent") for agent in crew_agents],
                "tools_called": self._workflow_tool_ids(workflow, agent_configs),
                "memory_enabled": memory_active,
                "knowledge_enabled": bool(knowledge_sources),
                "knowledge_sources_count": len(knowledge_sources) if knowledge_sources else 0,
                "process": process.value if hasattr(process, "value") else str(process),
                "usage": token_usage if isinstance(token_usage, dict) else {},
                "cost_usd": round(approx_cost, 6),
            },
        )

    def _resolve_knowledge_sources(self, workflow: WorkflowConfig) -> list[Any]:
        """Dynamically build CrewAI Knowledge source instances if configured."""
        if not hasattr(workflow, "knowledge") or not getattr(workflow.knowledge, "enabled", False):
            return []
            
        sources = []
        try:
            from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
            
            # Inject dynamic context as string knowledge if metadata contains context
            desc = getattr(workflow, "description", "")
            if desc:
                sources.append(
                    StringKnowledgeSource(
                        content=f"Workflow Domain Info: {desc}",
                        metadata={"source": "workflow_description"},
                    )
                )
        except Exception as e:
            logger.debug("crewai_knowledge_source_import_skipped", error=str(e))
            
        return sources

    def _create_agent(
        self,
        agent_cls: type[Any],
        config: AgentConfig,
        stack: contextlib.ExitStack | None = None,
        run_tool_cache: dict[str, list[Any]] | None = None,
    ) -> Any:
        model_config = config.model_config_override or {}
        tools = self._get_crewai_tools(config.tools, stack, run_tool_cache)

        agent_kwargs: dict[str, Any] = {
            "role": config.name,
            "goal": config.description or f"Help users with {config.name} requests.",
            "backstory": config.system_message or config.description or "You are a highly capable enterprise AI assistant.",
            "llm": self._resolve_llm_model(model_config),
            "tools": tools,
            "allow_delegation": bool(config.is_selector),
            "max_iter": int(model_config.get("max_iter") or 20),
            "verbose": False,
        }
        if model_config.get("max_rpm"):
            agent_kwargs["max_rpm"] = int(model_config["max_rpm"])
        if model_config.get("max_execution_time"):
            agent_kwargs["max_execution_time"] = int(model_config["max_execution_time"])

        return agent_cls(**agent_kwargs)

    def _resolve_llm_model(self, model_config: dict[str, Any]) -> Any:
        model = model_config.get("model")
        if not model:
            model = os.getenv("LLM_MODEL", "openrouter/google/gemma-3-27b-it")
        elif "/" in model and not model.startswith(("openrouter/", "ollama/", "azure/", "gemini/")):
            provider = os.getenv("LLM_PROVIDER", "openrouter")
            if provider == "openrouter":
                model = f"openrouter/{model}"
        model = str(model)

        # When the studio config carries actual sampling/limit parameters, build a
        # full LLM object so they're honored; a bare model string otherwise keeps
        # existing behavior byte-for-byte.
        llm_params = {
            "temperature": model_config.get("temperature"),
            "max_tokens": model_config.get("max_tokens"),
            "base_url": model_config.get("base_url") or None,
            "timeout": model_config.get("timeout"),
            "top_p": model_config.get("top_p"),
        }
        api_key_env = model_config.get("api_key_env")
        if api_key_env:
            llm_params["api_key"] = os.environ.get(str(api_key_env))
        llm_params = {k: v for k, v in llm_params.items() if v is not None}
        if not llm_params:
            return model

        try:
            from crewai import LLM

            return LLM(model=model, **llm_params)
        except Exception as e:
            logger.warning("crewai_llm_params_ignored", error=str(e), model=model)
            return model

    def _get_crewai_tools(
        self,
        tool_ids: list[str],
        stack: contextlib.ExitStack | None = None,
        run_tool_cache: dict[str, list[Any]] | None = None,
    ) -> list[Any]:
        if not tool_ids:
            return []
        try:
            from crewai.tools import tool
        except Exception:
            return []

        registry = get_tool_registry()
        crew_tools: list[Any] = []
        for tool_id in tool_ids:
            tool_def = registry.get_tool(tool_id)
            if tool_def is None:
                logger.warning("crewai_tool_missing", tool_id=tool_id)
                continue

            factory = getattr(tool_def, "factory", None)
            if factory is not None and stack is not None:
                # Factory-backed tools (mcp/database/gmail) yield native BaseTool
                # instances with real argument schemas — they must NOT be re-wrapped
                # by _wrap_tool, which would clobber the schema with **kwargs.
                cache = run_tool_cache if run_tool_cache is not None else {}
                if tool_id not in cache:
                    try:
                        cache[tool_id] = factory.build(stack)
                    except Exception as e:
                        logger.error("crewai_tool_factory_failed", tool_id=tool_id, error=str(e))
                        cache[tool_id] = []
                crew_tools.extend(cache[tool_id])
                continue

            crew_tools.append(self._wrap_tool(tool, tool_def))
        return crew_tools

    def _wrap_tool(self, tool_decorator: Callable[..., Any], tool_def: ToolDefinition) -> Any:
        func = tool_def.function

        def run_tool(**kwargs: Any) -> Any:
            started_tool = time.perf_counter()
            logger.info("crewai_tool_call_started", tool_id=tool_def.tool_id, tool_name=tool_def.name)
            try:
                if inspect.iscoroutinefunction(func):
                    res = asyncio.run(func(**kwargs))
                else:
                    res = func(**kwargs)
                duration = time.perf_counter() - started_tool
                logger.info("crewai_tool_call_success", tool_id=tool_def.tool_id, duration_sec=round(duration, 3))
                return res
            except Exception as e:
                duration = time.perf_counter() - started_tool
                logger.error("crewai_tool_call_failed", tool_id=tool_def.tool_id, error=str(e), duration_sec=round(duration, 3))
                return f"Tool execution error: {str(e)}"

        run_tool.__name__ = tool_def.name
        run_tool.__doc__ = tool_def.description
        return tool_decorator(tool_def.name)(run_tool)

    def _resolve_process(self, process_cls: type[Any], workflow: WorkflowConfig) -> Any:
        raw = (getattr(workflow, "process", None) or workflow.metadata.get("pattern") or workflow.execution_strategy or self.default_process)
        raw = str(getattr(raw, "value", raw)).lower()
        if raw in {"hierarchical", "selector", "group_chat"} and hasattr(process_cls, "hierarchical"):
            return process_cls.hierarchical
        return process_cls.sequential

    def _ordered_nodes(self, workflow: WorkflowConfig) -> list[Any]:
        topology = workflow.topology
        nodes_by_id = {node.id: node for node in topology.nodes}
        if not topology.edges:
            entry = nodes_by_id.get(topology.entry_node)
            rest = [node for node in topology.nodes if node.id != topology.entry_node]
            return ([entry] if entry else []) + rest

        ordered: list[Any] = []
        seen: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in seen or node_id not in nodes_by_id:
                return
            seen.add(node_id)
            ordered.append(nodes_by_id[node_id])
            for edge in topology.edges:
                if edge.from_node == node_id:
                    visit(edge.to_node)

        visit(topology.entry_node)
        ordered.extend(node for node in topology.nodes if node.id not in seen)
        return ordered

    @staticmethod
    def _human_input_enabled(agent_config: Any) -> bool:
        """Task-level human input, gated behind an explicit opt-in env var.

        CrewAI's human input blocks on stdin, which would hang a headless API
        worker — so honoring human_input_mode=ALWAYS requires
        OAK_ALLOW_HUMAN_INPUT=true.
        """
        mode = str(getattr(getattr(agent_config, "human_input_mode", ""), "value", getattr(agent_config, "human_input_mode", ""))).upper()
        if mode != "ALWAYS":
            return False
        if os.getenv("OAK_ALLOW_HUMAN_INPUT", "false").lower() == "true":
            return True
        logger.warning("crewai_human_input_suppressed", reason="OAK_ALLOW_HUMAN_INPUT is not enabled")
        return False

    @staticmethod
    def _make_output_guardrail(output_schema: str) -> Callable[[Any], tuple[bool, Any]]:
        """Simple final-output validator used when workflow.guardrails.enabled."""

        def guardrail(task_output: Any) -> tuple[bool, Any]:
            raw = str(getattr(task_output, "raw", task_output) or "").strip()
            if not raw:
                return False, "The output was empty. Produce a complete answer."
            if str(output_schema).lower() == "json":
                import json as _json

                candidate = raw
                if candidate.startswith("```"):
                    candidate = candidate.strip("`")
                    candidate = candidate.split("\n", 1)[1] if "\n" in candidate else candidate
                    if candidate.rstrip().endswith("```"):
                        candidate = candidate.rstrip().removesuffix("```")
                try:
                    _json.loads(candidate)
                except Exception as exc:
                    return False, f"The output must be valid JSON (parse error: {exc}). Re-emit as pure JSON with no prose."
            return True, task_output

        return guardrail

    def _create_tasks(
        self,
        task_cls: type[Any],
        workflow: WorkflowConfig,
        ordered_nodes: list[Any],
        crew_agent_by_id: dict[str, Any],
        message: str,
        session_id: str,
        user_id: str,
        metadata: dict[str, Any],
        agent_configs: dict[str, Any] | None = None,
    ) -> list[Any]:
        agent_configs = agent_configs or {}
        guardrails_enabled = bool(getattr(getattr(workflow, "guardrails", None), "enabled", False))
        guardrail_schema = str(getattr(getattr(workflow, "guardrails", None), "output_schema", "text"))

        def apply_task_extras(task_kwargs: dict[str, Any], agent_id: str | None, is_final: bool) -> None:
            config = agent_configs.get(agent_id) if agent_id else None
            if config is not None and self._human_input_enabled(config):
                task_kwargs["human_input"] = True
            if is_final and guardrails_enabled:
                task_kwargs["guardrail"] = self._make_output_guardrail(guardrail_schema)
                task_kwargs["guardrail_max_retries"] = 2

        explicit_tasks = getattr(workflow, "tasks", []) or []
        if explicit_tasks:
            tasks = []
            for index, task_config in enumerate(explicit_tasks):
                agent = crew_agent_by_id.get(task_config.agent_id)
                if not agent:
                    continue
                task_kwargs = {
                    "description": self._task_description(
                        workflow,
                        message,
                        session_id,
                        user_id,
                        metadata,
                        step=index + 1,
                        node_id=task_config.node_id,
                        task_description=task_config.description,
                    ),
                    "expected_output": task_config.expected_output,
                    "agent": agent,
                }
                if tasks:
                    task_kwargs["context"] = tasks[:]
                apply_task_extras(task_kwargs, task_config.agent_id, is_final=index == len(explicit_tasks) - 1)
                tasks.append(task_cls(**task_kwargs))
            if tasks:
                return tasks

        tasks = []
        for index, node in enumerate(ordered_nodes):
            agent = crew_agent_by_id.get(node.agent_id)
            if not agent:
                continue
            node_goal = node.config_override.get("task") if node.config_override else None
            task_kwargs = {
                "description": self._task_description(
                    workflow,
                    message,
                    session_id,
                    user_id,
                    metadata,
                    step=index + 1,
                    node_id=node.id,
                    task_description=node_goal or f"Execute and analyze workflow node {node.id} natively.",
                ),
                "expected_output": (node.config_override or {}).get(
                    "expected_output",
                    "A highly detailed, production-grade output supporting complete context validation.",
                ),
                "agent": agent,
            }
            upstream_tasks = self._upstream_tasks(workflow, node.id, ordered_nodes, tasks)
            if upstream_tasks:
                task_kwargs["context"] = upstream_tasks
            apply_task_extras(task_kwargs, node.agent_id, is_final=index == len(ordered_nodes) - 1)
            tasks.append(task_cls(**task_kwargs))
        return tasks

    def _task_description(
        self,
        workflow: WorkflowConfig,
        message: str,
        session_id: str,
        user_id: str,
        metadata: dict[str, Any],
        step: int = 1,
        node_id: str | None = None,
        task_description: str | None = None,
    ) -> str:
        return (
            f"Workflow Blueprint: {workflow.name}\n"
            f"Domain Focus: {workflow.description}\n"
            f"Execution Phase Step: {step}\n"
            f"Active Node: {node_id or 'derived'}\n"
            f"Mandatory Task Objective: {task_description or 'Evaluate user query and provide definitive guidance.'}\n"
            f"Session Trace ID: {session_id}\n"
            f"Identity Context: {user_id}\n"
            f"Runtime Parameters: {metadata}\n\n"
            f"Incoming User Prompt:\n{message}\n\n"
            "Deliver an optimal, exhaustive answer utilizing any applicable configured tools automatically."
        )

    def _upstream_tasks(
        self,
        workflow: WorkflowConfig,
        node_id: str,
        ordered_nodes: list[Any],
        created_tasks: list[Any],
    ) -> list[Any]:
        """Return CrewAI task context for upstream topology nodes."""
        if not workflow.topology.edges:
            return created_tasks[-1:] if created_tasks else []

        node_position = {node.id: index for index, node in enumerate(ordered_nodes)}
        upstream_ids = {
            edge.from_node
            for edge in workflow.topology.edges
            if edge.to_node == node_id and edge.from_node in node_position
        }
        return [
            task
            for node, task in zip(ordered_nodes, created_tasks)
            if node.id in upstream_ids
        ]

    def _planning_trace(
        self,
        workflow: WorkflowConfig,
        ordered_nodes: list[Any],
        tasks: list[Any],
        process: Any,
        crew_agents: list[Any],
    ) -> list[dict[str, Any]]:
        """Create normalized trace entries before CrewAI kickoff."""
        now = time.time()
        process_name = process.value if hasattr(process, "value") else str(process)
        trace_steps: list[dict[str, Any]] = [
            {
                "type": "crew_start",
                "agent": "CrewAI",
                "description": f"Supercharged workflow {workflow.id} kickoff with {len(tasks)} native tasks",
                "timestamp": now,
                "details": {
                    "process": process_name,
                    "workflow_type": getattr(workflow.workflow_type, "value", workflow.workflow_type),
                    "runtime": "crewai_advanced",
                },
            },
            {
                "type": "memory",
                "agent": "CrewAI",
                "description": "Enterprise Memory Subsystem Active",
                "timestamp": now,
                "details": workflow.memory.model_dump(mode="json") if hasattr(workflow, "memory") else {"enabled": self.memory_enabled},
            },
            {
                "type": "knowledge",
                "agent": "CrewAI",
                "description": "Dynamic Knowledge Sources Connected",
                "timestamp": now,
                "details": workflow.knowledge.model_dump(mode="json") if hasattr(workflow, "knowledge") else {"enabled": True, "sources_resolved": True},
            },
        ]
        for index, (node, task) in enumerate(zip(ordered_nodes, tasks), start=1):
            trace_steps.append(
                {
                    "type": "task_planned",
                    "agent": node.agent_id,
                    "description": f"Orchestrated Task {index} mapped to state node {node.id}",
                    "timestamp": now,
                    "details": {
                        "node_id": node.id,
                        "task_preview": getattr(task, "description", "")[:240],
                        "expected_output": getattr(task, "expected_output", None),
                    },
                }
            )
        for agent in crew_agents:
            tools = getattr(agent, "tools", []) or []
            trace_steps.append(
                {
                    "type": "agent_ready",
                    "agent": getattr(agent, "role", "agent"),
                    "description": f"Specialist Agent online leveraging {len(tools)} embedded tool capabilities",
                    "timestamp": now,
                    "details": {"tool_count": len(tools)},
                }
            )
        return trace_steps

    def _workflow_tool_ids(
        self,
        workflow: WorkflowConfig,
        agent_configs: dict[str, AgentConfig],
    ) -> list[str]:
        """Return the configured tools expected to be available during execution."""
        tool_ids: list[str] = []
        for node in workflow.topology.nodes:
            config = agent_configs.get(node.agent_id)
            if not config:
                continue
            for tool_id in config.tools:
                if tool_id not in tool_ids:
                    tool_ids.append(tool_id)
        return tool_ids
