"""Command line interface."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pipeline_runner.config import load_pipeline
from pipeline_runner.runner import PipelineRunner


def main(argv: list[str] | None = None) -> None:
    """Run the command line program."""
    args = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="pipeline-runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="run a pipeline YAML file")
    run_parser.add_argument("config", type=Path)
    run_parser.add_argument("--var", action="append", default=[], help="set a variable: name=value")

    info_parser = subparsers.add_parser("info", help="show pipeline summary")
    info_parser.add_argument("config", type=Path)

    validate_parser = subparsers.add_parser("validate", help="validate a pipeline YAML file")
    validate_parser.add_argument("config", type=Path)

    if len(args) >= 2 and args[0] == "run" and "--help" not in args and "-h" not in args:
        _run_with_dynamic_args(args)
        return

    parsed = parser.parse_args(args)
    if parsed.command == "info":
        _show_info(parsed.config)
    elif parsed.command == "validate":
        load_pipeline(parsed.config)
        print("OK")
    elif parsed.command == "run":
        _run(parsed.config, _parse_vars(parsed.var))


def _run_with_dynamic_args(args: list[str]) -> None:
    config = load_pipeline(args[1])
    run_parser = argparse.ArgumentParser(prog="pipeline-runner run")
    run_parser.add_argument("command")
    run_parser.add_argument("config", type=Path)
    run_parser.add_argument("--var", action="append", default=[], help="set a variable: name=value")
    for item in config.get("cli", {}).get("arguments", []):
        name = item["name"]
        arg_type = _arg_type(item.get("type", "str"))
        default = item.get("default")
        required = bool(item.get("required", False)) and default is None
        run_parser.add_argument(
            f"--{name}",
            default=default,
            required=required,
            type=arg_type,
            help=item.get("help", ""),
        )
    parsed = run_parser.parse_args(args)
    variables = _parse_vars(parsed.var)
    variables.update(
        {
            key: value
            for key, value in vars(parsed).items()
            if key not in {"command", "config", "var"} and value is not None
        }
    )
    _run(parsed.config, variables, config)


def _run(config_path: Path, variables: dict[str, Any], config: dict[str, Any] | None = None) -> None:
    config = config or load_pipeline(config_path)
    state = PipelineRunner(config).run(variables)
    if state.errors:
        for error in state.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)


def _show_info(config_path: Path) -> None:
    config = load_pipeline(config_path)
    workflow = config["workflow"]
    print(config.get("name", config_path.stem))
    if config.get("description"):
        print(config["description"])
    print(f"entry: {workflow['entry']}")
    print(f"nodes: {len(workflow['nodes'])}")
    print(f"edges: {len(workflow.get('edges', []))}")
    arguments = config.get("cli", {}).get("arguments", [])
    if arguments:
        print("arguments:")
        for item in arguments:
            default = f" default={item['default']!r}" if "default" in item else ""
            print(f"  --{item['name']} ({item.get('type', 'str')}){default}")


def _parse_vars(items: list[str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--var must use name=value, got: {item}")
        key, value = item.split("=", 1)
        values[key] = value
    return values


def _arg_type(name: str) -> type[Any] | Callable[[str], bool]:
    if name == "int":
        return int
    if name == "float":
        return float
    if name == "bool":
        return _bool_arg
    return str


def _bool_arg(value: str) -> bool:
    normalized = value.lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


if __name__ == "__main__":
    main()
