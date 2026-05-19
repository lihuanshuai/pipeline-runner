"""Sequential graph runner for YAML pipelines."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline_runner.config import load_pipeline
from pipeline_runner.nodes import execute_node
from pipeline_runner.state import PipelineState, StepResult
from pipeline_runner.template import ConditionEvaluator


class PipelineRunner:
    """Run a configured pipeline one node at a time."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.workflow = config["workflow"]
        self.nodes = {node["name"]: node for node in self.workflow["nodes"]}
        self.edges = self.workflow.get("edges", [])
        self.conditions = ConditionEvaluator()

    def run(self, variables: dict[str, Any] | None = None) -> PipelineState:
        """Run the pipeline and return final state."""
        state = PipelineState(vars={**self.config.get("vars", {}), **(variables or {})})
        current = self.workflow["entry"]
        visited = 0
        max_steps = int(self.config.get("max_steps", max(len(self.nodes) * 4, 20)))

        while current:
            visited += 1
            if visited > max_steps:
                raise RuntimeError(f"Pipeline exceeded max_steps={max_steps}; possible cycle.")
            node = self.nodes[current]
            result = self._run_node(node, state)
            if not result.success and not node.get("continue_on_error", False):
                break
            current = self._next_node(current, state)

        return state

    def _run_node(self, node: dict[str, Any], state: PipelineState) -> StepResult:
        name = node["name"]
        if not self.conditions.evaluate(node.get("condition"), state.as_context()):
            state.skipped_steps.append(name)
            return StepResult()

        print(f"-> {name}")
        try:
            result = execute_node(node, state)
        except Exception as exc:
            result = StepResult(success=False, error=str(exc))

        state.completed_steps.append(name)
        state.results[name] = result.data
        self._copy_outputs(node, result, state)
        if not result.success and result.error:
            state.errors.append(f"{name}: {result.error}")
        return result

    def _copy_outputs(
        self,
        node: dict[str, Any],
        result: StepResult,
        state: PipelineState,
    ) -> None:
        output_map = node.get("output_map") or {}
        for var_name, result_key in output_map.items():
            if result_key in result.data:
                state.vars[var_name] = result.data[result_key]
        for key in node.get("outputs", []):
            if key in result.data:
                state.vars[key] = result.data[key]

    def _next_node(self, current: str, state: PipelineState) -> str | None:
        outgoing = [edge for edge in self.edges if edge.get("from") == current]
        conditional = [edge for edge in outgoing if edge.get("condition")]
        unconditional = [edge for edge in outgoing if not edge.get("condition")]
        for edge in conditional + unconditional:
            if self.conditions.evaluate(edge.get("condition"), state.as_context()):
                return edge["to"]
        return None


def run_pipeline(path: str | Path, variables: dict[str, Any] | None = None) -> PipelineState:
    """Load and run a pipeline config."""
    return PipelineRunner(load_pipeline(path)).run(variables)
