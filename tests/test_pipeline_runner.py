from __future__ import annotations

from pathlib import Path

from pipeline_runner import run_pipeline


def test_run_set_and_condition_pipeline(tmp_path: Path) -> None:
    config_path = tmp_path / "pipeline.yaml"
    config_path.write_text(
        """
name: test
vars:
  enabled: true
workflow:
  entry: start
  nodes:
    - name: start
      type: set
      values:
        value: "ok"
      outputs: [value]
    - name: "yes"
      type: set
      values:
        branch: "yes"
      outputs: [branch]
    - name: nope
      type: set
      values:
        branch: "nope"
      outputs: [branch]
  edges:
    - from: start
      to: "yes"
      condition: "{enabled}"
    - from: start
      to: nope
""".lstrip(),
        encoding="utf-8",
        newline="\n",
    )

    state = run_pipeline(config_path)

    assert state.vars["value"] == "ok"
    assert state.vars["branch"] == "yes"
    assert state.completed_steps == ["start", "yes"]


def test_render_preserves_native_values(tmp_path: Path) -> None:
    config_path = tmp_path / "pipeline.yaml"
    config_path.write_text(
        """
name: native
vars:
  count: 3
workflow:
  entry: start
  nodes:
    - name: start
      type: set
      values:
        copied: "{count}"
      outputs: [copied]
  edges: []
""".lstrip(),
        encoding="utf-8",
        newline="\n",
    )

    state = run_pipeline(config_path)

    assert state.vars["copied"] == 3
