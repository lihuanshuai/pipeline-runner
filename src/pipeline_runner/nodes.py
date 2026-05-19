"""Node executors used by the pipeline runner."""

from __future__ import annotations

import importlib
import json
import subprocess
from collections.abc import Callable
from typing import Any

from pipeline_runner.state import PipelineState, StepResult
from pipeline_runner.template import render


def execute_node(node: dict[str, Any], state: PipelineState) -> StepResult:
    """Dispatch a node to the matching executor."""
    node_type = node.get("type", "command")
    if node_type == "command":
        return _execute_command(node, state)
    if node_type == "shell":
        return _execute_shell(node, state)
    if node_type == "python":
        return _execute_python(node, state)
    if node_type == "set":
        return _execute_set(node, state)
    if node_type == "print":
        return _execute_print(node, state)
    raise ValueError(f"Unsupported node type: {node_type}")


def _execute_command(node: dict[str, Any], state: PipelineState) -> StepResult:
    context = state.as_context()
    executable = render(node.get("exec"), context)
    if not executable:
        raise ValueError(f"Node {node['name']} is missing exec.")
    args = render(node.get("args", []), context)
    if not isinstance(args, list):
        raise ValueError(f"Node {node['name']} args must be a list.")
    command = [str(executable), *[str(part) for part in args]]

    return _run_process(command, bool(node.get("shell", False)), int(node.get("timeout", 300)))


def _execute_shell(node: dict[str, Any], state: PipelineState) -> StepResult:
    command = render(node.get("command"), state.as_context())
    if not isinstance(command, str) or not command:
        raise ValueError(f"Node {node['name']} is missing command.")
    return _run_process(command, True, int(node.get("timeout", 300)))


def _run_process(command: str | list[str], shell: bool, timeout: int) -> StepResult:
    result = subprocess.run(
        command,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        shell=shell,
        timeout=timeout,
        check=False,
    )
    data = _parse_output(result.stdout)
    return StepResult(
        success=result.returncode == 0,
        data=data,
        error=(result.stderr.strip() or None) if result.returncode != 0 else None,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _execute_python(node: dict[str, Any], state: PipelineState) -> StepResult:
    function_path = node.get("function")
    if not function_path or "." not in function_path:
        raise ValueError(f"Node {node['name']} has invalid function path.")
    module_name, function_name = function_path.rsplit(".", 1)
    function: Callable[..., Any] = getattr(importlib.import_module(module_name), function_name)
    kwargs = render(node.get("args", {}), state.as_context())
    if not isinstance(kwargs, dict):
        raise ValueError(f"Node {node['name']} args must be a mapping.")
    result = function(**kwargs)
    data = result if isinstance(result, dict) else {"result": result}
    return StepResult(data=data)


def _execute_set(node: dict[str, Any], state: PipelineState) -> StepResult:
    return StepResult(data=render(node.get("values", {}), state.as_context()))


def _execute_print(node: dict[str, Any], state: PipelineState) -> StepResult:
    keys = node.get("keys")
    if keys:
        for key in keys:
            print(f"{key}: {render('{' + key + '}', state.as_context())}")
    else:
        print(json.dumps(state.results, ensure_ascii=False, indent=2))
    return StepResult()


def _parse_output(stdout: str) -> dict[str, Any]:
    text = stdout.strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"output": text}
    return data if isinstance(data, dict) else {"output": data}
