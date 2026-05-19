# pipeline-runner

`pipeline-runner` 是一个轻量的 YAML Pipeline 运行器，用「声明节点、声明边、用变量串起步骤」的方式编排通用脚本、工具和 Python 函数。

## 特性

- 使用 YAML 描述 pipeline，适合脚本编排、数据处理、媒体处理、批任务串联。
- 内置 `command`、`tool`、`python`、`set`、`print` 节点。
- 支持 `{var}` 模板、条件边、节点跳过、JSON stdout 自动解析。
- 提供命令行脚本：`pipeline-runner`。
- 代码小、依赖少，核心只有 `pyyaml`。

## 安装

开发模式安装：

```powershell
uv pip install -e .
```

或直接运行：

```powershell
uv run pipeline-runner validate examples/pipelines/hello.yaml
uv run pipeline-runner run examples/pipelines/hello.yaml --name Jerry
```

## 快速开始

```yaml
name: hello
description: minimal example

cli:
  arguments:
    - name: name
      type: str
      required: true
      help: name to greet

workflow:
  entry: greet
  nodes:
    - name: greet
      type: command
      command: "python -c \"import json; print(json.dumps(dict(message='hello {name}')))\""
      outputs: [message]
    - name: show
      type: print
      keys: [message]
  edges:
    - from: greet
      to: show
```

运行：

```powershell
uv run pipeline-runner run examples/pipelines/hello.yaml --name Jerry
```

## YAML 结构

顶层字段：

- `name` / `description`：用于文档和 `info` 输出。
- `vars`：默认变量，会与 CLI 参数合并。
- `cli.arguments`：声明 `run` 子命令的动态参数。
- `workflow.entry`：入口节点名。
- `workflow.nodes`：节点列表。
- `workflow.edges`：有向边列表；条件边优先于无条件边。

提示：YAML 会把未加引号的 `yes`、`no`、`on`、`off` 解析成布尔值；如果它们是节点名或普通字符串，请写成 `"yes"`、`"no"`。

### 节点类型

`command`：执行一条命令。stdout 如果是 JSON object，会自动作为节点结果。

```yaml
- name: list
  type: command
  command: ["python", "-c", "print('{\"ok\": true}')"]
  shell: false
  outputs: [ok]
```

`tool`：调用外部工具，会把 `inputs` 转为 `--key value` 参数。

```yaml
- name: parse
  type: tool
  tool: parse-media
  inputs:
    input: "{input_path}"
  outputs: [duration, codec]
```

`python`：调用 Python 函数，函数返回 dict 时会作为结果。

```yaml
- name: prepare
  type: python
  function: "my_project.pipeline.prepare_output"
  inputs:
    output_dir: "{output_dir}"
    uid: "{uid}"
  outputs: [output_path]
```

`set`：设置变量，适合拼装中间值。

```yaml
- name: defaults
  type: set
  values:
    output_path: "{output_dir}/{uid}.mp4"
  outputs: [output_path]
```

`print`：打印结果或指定变量。

```yaml
- name: show
  type: print
  keys: [output_path]
```

### 条件

条件中使用 `{var}` 引用变量，表达式支持常见比较和布尔运算：

```yaml
edges:
  - from: extract_uid
    to: convert
    condition: "{skip_meta} or {uid} == ''"
  - from: extract_uid
    to: fetch_meta
```

节点也可以设置 `condition`。当条件为 false 时节点会被跳过。

## Python API

```python
from pipeline_runner import run_pipeline

state = run_pipeline("examples/pipelines/hello.yaml", {"name": "Jerry"})
print(state.vars["message"])
```

## 命令

```powershell
pipeline-runner info path/to/pipeline.yaml
pipeline-runner validate path/to/pipeline.yaml
pipeline-runner run path/to/pipeline.yaml --var name=value
```

如果 YAML 声明了 `cli.arguments`，也可以直接使用动态参数：

```powershell
pipeline-runner run path/to/pipeline.yaml --input_path input.mp4 --skip_meta false
```
