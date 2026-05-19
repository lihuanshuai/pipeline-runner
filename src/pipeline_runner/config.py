"""Pipeline configuration loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, get_args

import yaml

NodeType = Literal["command", "shell", "python", "set", "print"]

_NODE_TYPES: frozenset[str] = frozenset(get_args(NodeType))


def load_pipeline(path: str | Path) -> dict[str, Any]:
    """Load and validate a pipeline YAML file."""
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8", newline="\n") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError("Pipeline config must be a mapping.")
    validate_pipeline(data)
    return data


def validate_pipeline(config: dict[str, Any]) -> None:
    """Validate the minimal schema needed to run a pipeline."""
    workflow = config.get("workflow")
    if not isinstance(workflow, dict):
        raise ValueError("Missing workflow section.")
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("workflow.nodes must be a non-empty list.")

    node_names: set[str] = set()
    for index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            raise ValueError(f"Node #{index} must be a mapping.")
        name = node.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError(f"Node #{index} name must be a non-empty string.")
        node_type = node.get("type", "command")
        if node_type not in _NODE_TYPES:
            raise ValueError(f"Node {name} has unsupported type: {node_type}")
        if name in node_names:
            raise ValueError(f"Duplicate node name: {name}")
        node_names.add(name)

    entry = workflow.get("entry")
    if entry not in node_names:
        raise ValueError(f"workflow.entry must reference a node, got: {entry}")

    for edge in workflow.get("edges", []):
        from_node = edge.get("from")
        to_node = edge.get("to")
        if from_node not in node_names:
            raise ValueError(f"Edge references unknown from node: {from_node}")
        if to_node not in node_names:
            raise ValueError(f"Edge references unknown to node: {to_node}")
