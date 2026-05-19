"""Runtime state and step result models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StepResult:
    """Result returned by every node executor."""

    success: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    stdout: str = ""
    stderr: str = ""


@dataclass(slots=True)
class PipelineState:
    """Mutable state shared by all pipeline nodes."""

    vars: dict[str, Any] = field(default_factory=dict)
    results: dict[str, dict[str, Any]] = field(default_factory=dict)
    completed_steps: list[str] = field(default_factory=list)
    skipped_steps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def as_context(self) -> dict[str, Any]:
        """Return the context exposed to templates and conditions."""
        return {
            **self.vars,
            "vars": self.vars,
            "results": self.results,
            "completed_steps": self.completed_steps,
            "skipped_steps": self.skipped_steps,
            "errors": self.errors,
        }
