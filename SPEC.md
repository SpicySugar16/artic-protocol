# Artic Protocol 规格说明书 v0.1 (draft-01)

> 本文档是 Artic Protocol 的精确技术规格。
> 任何实现此协议的引擎和模块应当以此为基准。

---

## 1. 消息格式

### 1.1 消息信封（Message Envelope）

引擎和模块之间的所有交互通过此结构传输。序列化格式推荐 JSON，但协议不强制（只要运行时双方协商一致）。

```
Field         | Type     | 必需 | 说明
--------------|----------|------|-----------------------
id            | String   | 是   | 消息唯一标识（UUID v4）
from          | String   | 是   | 发送方模块 ID
to            | String   | 是   | 路由目标（服务名 或 模块 ID 或 "engine"）
kind          | Enum     | 是   | 消息类型（见 1.2）
headers       | Map      | 否   | 消息头（元数据键值对）
payload       | Any      | 是   | 消息体（引擎不解析）
reply_to      | String   | 否   | 回复目标消息 ID（仅 response/error 类型使用）
timestamp     | Integer  | 是   | Unix 毫秒时间戳
```

### 1.2 消息类型（kind）

| 类型 | 使用场景 |
|------|---------|
| `request` | 请求服务——发送方期望收到回复 |
| `response` | 对 request 的回复——必须设置 reply_to |
| `broadcast` | 广播——不期望回复，引擎转发给所有订阅了该服务名的模块 |
| `event` | 引擎向模块推送生命周期事件 |
| `declaration` | 模块启动时向引擎声明身份和能力 |
| `error` | 错误回复——必须设置 reply_to |

### 1.3 消息 ID 生成

- 推荐 UUID v4
- 必须保证在单次会话内唯一
- 引擎可用任意生成策略，只要不碰撞

### 1.4 错误消息负载格式

```
{
  "code": "SERVICE_NOT_FOUND",
  "message": "No module provides 'memory.recall'"
}
```

引擎必须识别的错误码：

| 错误码 | 含义 |
|--------|------|
| `SERVICE_NOT_FOUND` | 目标服务未注册到任何模块 |
| `MODULE_NOT_FOUND` | 目标模块 ID 未注册 |
| `HANDLER_TIMEOUT` | 模块处理请求超时 |
| `HANDLER_PANIC` | 模块处理请求时崩溃 |
| `DEPENDENCY_MISSING` | 依赖的服务缺失 |
| `NOT_IMPLEMENTED` | 模块声明了该服务但尚未实现 |

---

## 2. 模块声明格式

模块启动后应立即向引擎发送 `declaration` 消息。引擎在收到后执行依赖检查，通过后注入耦合器并发送 `event: startup`。

### 2.1 声明负载

```json
{
  "module_id": "emotion",
  "name": "情绪引擎",
  "version": "0.3.0",
  "author": {
    "name": "墨水仙猫",
    "contact": "https://github.com/spicysugar",
    "description": "基于 openclaw 算法的 16 种复合情绪检测引擎",
    "license": "MIT"
  },
  "provides": [
    {"service": "emotion.detect", "description": "从文本检测复合情绪状态"},
    {"service": "emotion.style", "description": "返回当前风格注入文本"}
  ],
  "requires": [],
  "required_modules": [],
  "handlers": ["startup", "on_message"]
}
```

### 2.2 字段说明

**module_id**: 模块唯一标识，全小写字母+连字符。如 `memory`、`emotion`、`context-compress`。全局唯一，由模块作者保证不与其他模块冲突。

**name**: 人类可读的名称，不限格式。如 "上下文压缩引擎"、"情绪检测器"。

**version**: 语义化版本号 (SemVer)。当模块的服务接口不兼容时需要升主版本号。

**author**: 作者信息。引擎应记录此信息，在 `engine.module.list` 查询时返回。

**provides**: 本模块对外提供的服务列表。每个服务含 `service` 和 `description` 字段。`service` 是服务在消息路由时使用的目标名称。

**requires**: 本模块依赖的服务列表。空表示不依赖外部服务。

**required_modules**: 本模块依赖的其他模块 ID 列表（按模块名依赖，常用于进程级模块）。空表示无模块级依赖。

**handlers**: 模块感兴趣的引擎事件类型。引擎仅在列表中的事件发送给该模块。可选值：`startup`、`shutdown`、`on_message`、`on_response`。

### 2.3 依赖检查规则

引擎在收到 declaration 后：

1. 将所有 `provides` 条目加入服务注册表（**幂等**——同服务名第二次注册以最后注册的为准）
2. 检查 `requires`：对每个依赖的服务，查服务注册表是否存在
3. 检查 `required_modules`：对每个依赖的模块 ID，查是否已收到该模块的 declaration
4. 依赖满足 → 注入耦合器，发送 `event: startup`
5. 依赖不满足 → 发送 `error: DEPENDENCY_MISSING`，**模块继续等待**（而非拒绝注册——等依赖模块上线后自动重试）

**重试机制**：引擎在每次收到新模块的 declaration 后，对所有等待中的模块重新执行依赖检查。

---

## 3. 耦合器接口

耦合器是引擎提供给模块的编程接口。以下为接口定义（伪代码，不绑定语言）：

```
interface Coupling {
    // 调用服务并等待回复
    // timeout: 超时秒数
    // 返回: payload (JSON)
    // 可能抛出: TimeoutError, ServiceError, DisconnectedError
    fn call(service: String, payload: JSON, timeout: u64) -> JSON

    // 调用服务不等待回复 (fire-and-forget)
    fn fire(service: String, payload: JSON)

    // 广播消息——引擎转发给所有注册了该服务的模块
    fn broadcast(topic: String, payload: JSON)

    // 声明模块身份（模块启动时调用一次）
    fn declare(declaration: Declaration)

    // 发送事件（模块触发引擎事件）
    fn emit(event: String, payload: JSON)
}
```

### 3.1 call() 的同步语义

`call()` 是同步阻塞调用。引擎收到 request 后转发给服务提供模块，等待该模块回复后才返回。实现要点：

1. 生成消息 ID，注册 pending 表
2. 通过引擎通道发送 request 消息
3. 阻塞等待 reply_to 匹配的 response 消息（最多 timeout 秒）
4. 超时则清理 pending 表，抛 TimeoutError
5. 收到 response 后校验 reply_to 匹配当前消息 ID

### 3.2 fire() 的异步语义

`fire()` 不等待回复。引擎仅投递消息，不关心模块是否处理。适用于日志、触发等不需要结果的场景。

### 3.3 广播语义

`broadcast()` 发送的消息，引擎转发给所有在服务注册表中为 `topic` 的模块。每个模块独立接收、独立处理。引擎不聚合结果。

---

## 4. 事件系统

引擎通过向模块发送 `event` 类型的消息来驱动模块生命周期。

### 4.1 标准事件

| 事件名称 | 触发时机 | 负载示例 |
|---------|---------|---------|
| `startup` | 引擎完成初始化，模块注册完成 | `{}` |
| `shutdown` | 引擎收到退出信号 | `{}` |
| `on_message` | 收到用户消息 | `{"input": "...", "channel": "qqbot"}` |
| `on_response` | LLM 生成回复后 | `{"response": "..."}` |

### 4.2 自定义事件

模块可以通过 `coupling.emit("custom_event", payload)` 触发自定义事件。其他模块如果 `handlers` 中包含了 `"custom_event"`，将收到该事件。

引擎不校验事件名称——不识别的事件名称按广播处理。

---

## 5. 模块生命周期

```
         ┌────────────┐
         │  Declare   │  发送 declaration 消息
         └─────┬──────┘
               │ 依赖检查通过
         ┌─────▼──────┐
         │  Attached  │  获得耦合器，收到 startup 事件
         └─────┬──────┘
               │ 正常运行
         ┌─────▼──────┐
         │  Running   │  收发消息，处理服务请求
         └─────┬──────┘
               │ 收到 shutdown 事件
         ┌─────▼──────┐
         │  Detached  │  清理资源，耦合器失效
         └────────────┘
```

### 5.1 状态定义

| 状态 | 说明 |
|------|------|
| `Declare` | 模块已发送声明，等待引擎确认 |
| `Attached` | 引擎确认声明，注入耦合器，等待 startup |
| `Running` | 模块正常运行，可以处理消息 |
| `Degraded` | 模块部分功能不可用（如依赖的远端服务断开） |
| `Error` | 模块内部出错但未崩溃 |
| `Detached` | 模块已关闭，耦合器不再可用 |

---

## 6. 健康检查

### 6.1 标准健康消息

引擎发送 `request("health.check", {})` 给模块，模块应回复：

```json
{
  "status": "running",
  "message_count": 42,
  "error_count": 1,
  "last_error": "timeout on memory.recall at 1718000000123",
  "details": { "uptime_secs": 3600 }
}
```

### 6.2 允许的状态值

| 状态 | 含义 |
|------|------|
| `running` | 正常 |
| `degraded` | 部分降级 |
| `error` | 出错 |
| `stopped` | 已停止 |

---

## 7. 引擎内建服务

每个引擎必须实现以下内建服务（无需模块提供）：

| 服务名 | 功能 | 回复 |
|--------|------|------|
| `engine.module.list` | 列出所有已注册模块 | `{"modules": [{"id": "emotion", ...}]}` |
| `engine.module.health` | 查询所有模块健康状态 | `{"health": [{"id": "emotion", "status": "running"}]}` |
| `engine.service.lookup` | 查询某服务由谁提供 | `{"service": "emotion.detect", "module_id": "emotion"}` |
| `engine.system.ping` | 引擎存活检测 | `{"status": "ok", "version": "draft-01"}` |

---

## 8. 向后兼容规则

### 8.1 协议版本协商

引擎应在 `engine.system.ping` 的回复中声明自己的协议版本。模块在 startup 时可据此决定启用哪些特性。

### 8.2 新增字段

协议的新版本只能**添加**字段，不能修改或删除已有字段。旧实现须忽略不认识的字段。

### 8.3 声明兼容

- 新增服务不破坏兼容性
- 移除服务是主版本号变更
- 修改服务负载格式是主版本号变更

---

## 9. 安全建议（非强制）

1. 引擎应当记录每条消息的 `from` 和 `to`，用于审计
2. 引擎可选择校验模块声明中的 `author.signature`
3. 生产环境中，耦合器注入前应验证模块的来源
4. 消息负载的大小应有限制（建议引擎层面限制最大 10MB）

---

## 10. 模块打包格式（Module Package Format）

模块打包格式定义了如何将模块封装为可分发、可安装的标准包。旨在实现「一次打包，到处安装」——像 Android 的 APK 或 Docker 镜像一样。

### 10.1 包格式

| 属性 | 值 |
|------|----|
| 归档格式 | `.tar.gz`（gzip 压缩的 tar 包） |
| 扩展名 | `.amod`（Artic Module） |
| 最大体积 | 建议 50MB（引擎实现可自定义） |

### 10.2 目录结构

```
module-name-v1.0.0/
├── manifest.toml          # [必需] 模块清单
├── module/                # [必需] 模块实现代码
│   ├── main.py            # 入口文件（由 manifest.entry 指定）
│   └── ...
├── assets/                # [可选] 资源文件
│   ├── icons/
│   ├── templates/
│   └── ...
├── tests/                 # [可选] 测试
│   └── ...
└── README.md              # [推荐] 模块说明文档
```

打包后文件名：`module-name-v1.0.0.amod`

### 10.3 清单文件（manifest.toml）

```toml
[module]
id = "emotion.detect"              # 模块唯一标识（应与 declaration 一致）
name = "Emotion Detection"         # 人类可读名称
version = "1.0.0"                 # 语义版本号
language = "python"                # 实现语言
entry = "module/main.py"           # 入口文件路径（包内相对路径）
description = "Detect emotions from text input"

[module.author]
name = "SpicySugar16"
email = "spicysugar@example.com"
url = "https://github.com/SpicySugar16"

[module.declare]
provides = ["emotion.detect"]       # 提供的服务（对应 Artic Protocol Declaration）
requires = ["memory.recall"]        # 依赖的服务
handlers = ["system.startup"]       # 感兴趣的事件

[compatibility]
min_protocol_version = "draft-01"   # 最低协议版本
engines = ["tremolite", "*"]        # 兼容的引擎列表（"*" 表示通用）

[install]
entry_args = "--model light"        # 入口文件启动参数（可选）
env = { LOG_LEVEL = "info" }        # 注入的环境变量（可选）
post_install = "./scripts/setup.sh" # 安装后执行的脚本（可选，包内路径）
```

### 10.4 入口约定

引擎安装模块后，根据 `manifest.module.entry` 启动模块，向入口进程注入 `PowerCoupling`。

**进程式模块（推荐）：**

以独立进程运行，通过 stdin/stdout 或 TCP 与引擎通信，使用标准消息信封。

```python
# module/main.py
import sys, json

def main():
    # 引擎将耦合信息通过环境变量注入
    coupling_addr = os.environ["ARTIC_COUPLING"]
    module_id = os.environ["ARTIC_MODULE_ID"]
    
    for line in sys.stdin:
        envelope = json.loads(line)
        # 处理消息...
        response = {"id": envelope["id"], "kind": "response", "payload": {...}}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
```

**库式模块（内嵌）：**

模块作为动态库加载到引擎进程中，引擎直接调用模块的入口函数。

```rust
// module/main.rs
use artic_sdk::prelude::*;

struct EmotionModule;

impl Module for EmotionModule {
    fn handle(&self, ctx: &Context, msg: Message) -> Result<Reply> {
        // ...
    }
}

artic_export!(EmotionModule);
```

### 10.5 安装接口

引擎应暴露以下安装/卸载命令：

| 操作 | 说明 |
|------|------|
| `engine install ./emotion-v1.amod` | 从本地路径安装 |
| `engine install https://registry.example.com/emotion-v1.amod` | 从 URL 安装 |
| `engine uninstall emotion.detect` | 按模块 ID 卸载 |
| `engine list` | 列出已安装模块 |
| `engine info emotion.detect` | 查看模块详情 |

安装过程：

1. 校验包完整性（校验 manifest.toml 必需字段）
2. 解压到引擎的模块目录（如 `~/.artic/modules/emotion.detect/`）
3. 校验 `min_protocol_version` 与引擎兼容
4. 解析 `requires` 依赖，检查是否已满足
5. 如有 `post_install` 脚本，以模块目录为工作目录执行
6. 启动模块，注入耦合器，注册到服务注册表

### 10.6 分发规范（建议）

- **Registry（可选）**：社区可搭建模块注册中心，提供搜索、版本管理、下载
- **签名（可选）**：manifest.toml 可包含 `[module.signature]` 字段：
  ```toml
  [module.signature]
  algorithm = "ed25519"
  value = "base64_encoded_signature_here"
  ```
- **命名空间**：建议模块 ID 采用 `<作者>.<领域>.<操作>` 格式避免冲突

### 10.7 示例

一个完整的打包流程示例见 `examples/packaging/` 目录。
