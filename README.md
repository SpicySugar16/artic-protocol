# Artic Protocol

> **Artic Protocol** — A standard communication protocol for agent modules

**English** · <a href="#chinese-version">中文</a>

Any engine and modules that implement Artic Protocol, regardless of language or framework, can be plugged in, discover each other, and collaborate at runtime.

---

## 1. Why This Protocol

### The Current Situation

Each framework in the agent ecosystem defines its own module interface:

| Framework | Module Interface | Inter-Module Communication |
|-----------|-----------------|----------------------------|
| LangChain | `Runnable` chaining | Output of one feeds directly into the next |
| AutoGPT | Plugin + command registry | Loop invokes commands; modules don't know each other |
| Semantic Kernel | `Plugin` + `Function` | Routed through Kernel, but strongly typed binding |
| General agent frameworks | Custom interfaces + hardcoded registration | Framework-private mechanisms, no cross-framework reuse |

**Common problem:** Modules and engines are tightly coupled. A plugin written for LangChain cannot run on Semantic Kernel — their connector shapes don't match.

### What Artic Solves

- One standard protocol between engine and modules, not tied to any language
- Modules declare "what I can do"; the engine routes by capability, not by name
- Modules can come from different authors, repos, and languages — as long as they follow the protocol, they collaborate
- Upgrading, replacing, or hot-swapping a module requires no changes to the engine or other modules

---

## 2. In One Sentence

**Modules declare their capabilities and dependencies using standard message envelopes; the engine routes requests to the module that provides the named service.**

- Modules interact using service names, not module names
- The engine does not care about internal implementation
- Replacing a module = pull out the old one, plug in the new one

---

## 3. Protocol Roles

The protocol defines three roles:

![Protocol Three Roles](./docs/assets/three-roles-en.svg?t=1)

### Engine (Runtime)
- Supplies core power: LLM calls, session scheduling, tool execution
- Maintains a **Service Registry** — routes requests between modules by capability name
- Manages module lifecycle and reliable message delivery

### Module
- Declares capabilities and service dependencies on startup
- Connects to the engine through a standard coupling interface
- Calls other modules' services through the coupling interface (the engine handles routing)
- Does not need to know the implementation language, version, or author of other modules

### Developer
- Implements the `Module` interface and declaration file per the protocol spec
- Modules can be written in any language (Rust, Python, TypeScript, Go, ...)
- The engine provides SDKs or reference implementations

---

## 4. Core Concepts

### 4.1 Service

A service is a first-class citizen in the protocol. What a module provides = what services it registers.

```
Service naming convention: <domain>.<operation>
Examples:
  emotion.detect     — Detect emotion from text
  memory.recall      — Retrieve history from memory
  memory.store       — Store a message to memory
  llm.chat           — Generate a reply via LLM
  schedule.dispatch  — Dispatch a message to the scheduler
```

Service names are defined by module authors. The engine does not validate naming conventions (it only routes).

### 4.2 Declaration

An "identity card" sent by the module on startup:

| Field | Description | Required |
|-------|-------------|----------|
| `module_id` | Unique module identifier | Yes |
| `name` | Human-readable name | Yes |
| `version` | Semantic version | Yes |
| `author.name` | Author name | Yes |
| `author.contact` | Contact information | Yes |
| `author.description` | Module purpose description | Yes |
| `author.license` | License | No |
| `provides[]` | List of provided services | Yes |
| `requires[]` | List of required services | No |
| `required_modules[]` | List of required module IDs | No |
| `handlers[]` | Events the module is interested in | No |

### 4.3 Coupling

The connector between a module and the engine. Modules use the coupling to invoke services:

```
Call patterns:
  Synchronous (wait for reply): coupling.call("memory.recall", payload, timeout=5)
  Fire-and-forget:              coupling.fire("schedule.dispatch", payload)
  Broadcast:                    coupling.broadcast("system.alert", payload)
  Register identity:            coupling.declare(declaration)
```

Internally, the coupling wraps calls into standard message envelopes and routes them through the engine.

### 4.4 Message Envelope

All inter-module communication uses a standard envelope:

```json
{
  "id": "a1b2c3d4-e5f6-...",
  "from": "emotion",
  "to": "memory.recall",
  "kind": "request",
  "payload": { "session_id": "...", "limit": 20 },
  "reply_to": null,
  "timestamp": 1718000000000
}
```

The engine reads only the `to` field for routing and never inspects the `payload` content.

### 4.5 Dependency Check

After collecting all declarations, the engine:

1. Aggregates all modules' `provides` → builds the service registry
2. For each module's `requires`, checks whether a provider exists
3. If dependencies are missing, the engine refuses to start under-provisioned modules and returns an error list

This ensures modules know their dependencies are satisfied at startup, rather than crashing at runtime when a service is unavailable.

---

## 5. Protocol Flow

### 5.1 Startup Flow

![Startup Flow](./docs/assets/startup-flow-en.svg?t=1)

### 5.2 Runtime Message Flow

![Runtime Message Flow](./docs/assets/runtime-flow-en.svg?t=1)

Module A does not know who provides `foo.bar`. The engine looks up the service registry → finds Module B → forwards → returns the result.

---

## 6. What the Protocol Does Not Do

| Not covered | Reason |
|-------------|--------|
| Define message payload schema | Engine inspects envelopes only, not payloads |
| Specify serialization format | JSON recommended, but only key-value readability is required |
| Provide language SDKs | Protocol defines interfaces; implementations are language-specific |
| Mandate clustering / distribution | Single-process multi-module setups work too |
| Manage inter-module security | Trust model is up to the engine implementation |
| Define error handling strategies | Retry, backoff, and circuit-breaking are module-level decisions |

---

## 7. Existing Implementations

| Implementation | Language | Status | Repository |
|---------------|----------|--------|------------|
| Tremolite | Rust | ⚡ Core protocol implemented | https://github.com/spicysugar/tremolite |
| Your name | - | ✍️ Waiting for you | - |

---

## 8. Quick Start

See [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

---

## 9. Protocol Version

Current version: **draft-01**

The protocol is a draft. Systems implementing Artic Protocol should mark the version they support.

Version format: `draft-NN` or `vMAJOR.MINOR` (after stabilization).

---

## 10. Module Packaging

See [SPEC.md Section 10](SPEC.md#10-%E6%A8%A1%E5%9D%97%E6%89%93%E5%8C%85%E6%A0%BC%E5%BC%8Fmodule-package-format) for the **Module Package Format (`.amod`)** specification.

A `.amod` package bundles a module's code, manifest, and assets into a single distributable archive — like an APK for agent modules. Install it with:

```bash
tremolite module install emotion-detect-v1.0.0.amod
```

An example package is at [`examples/packaging/`](examples/packaging/).

---

<div id="chinese-version"></div>

<details>
<summary><strong>🌐 中文版本</strong> (点击展开)</summary>

<br>

# Artic Protocol

> **关 节 协 议** —— 智能体模块间的标准通讯协议

<a href="#">English</a> · **中文**

任何实现了 Artic Protocol 的引擎和模块，无论用什么语言、什么框架，都可以即插即用、互相发现、协作运行。

---

## 一、为什么要有这个协议

### 现状的混乱

目前的智能体生态里，每个框架自己定义一套模块接口：

| 框架 | 模块接口 | 模块间怎么通信 |
|------|---------|--------------|
| LangChain | `Runnable` 链式调用 | 前一个的输出直接传给后一个 |
| AutoGPT | 插件 + 命令注册表 | 循环调用命令，模块之间不认识 |
| Semantic Kernel | `Plugin` + `Function` | 通过 Kernel 路由，但强类型绑定 |
| 通用智能体框架 | 自研模块接口 + 硬编码注册 | 模块间通过框架私有的机制通信，无法跨框架复用 |

**共同问题：** 模块和引擎绑死了。用 LangChain 写的插件不能在 Semantic Kernel 上跑，因为它们的「接头」形状不一样。

### Artic 要解决的

- 引擎和模块之间只有一条标准协议，不绑定编程语言
- 模块声明「我能做什么」，引擎按能力路由，不靠名字硬编码
- 模块可以来自不同作者、不同仓库、不同语言，只要遵守协议就能协同
- 模块升级、替换、热插拔不需要修改引擎或其他模块

---

## 二、一句话概括

**模块通过标准消息信封向引擎声明自己的能力和需求，引擎根据能力名称将请求路由到提供该能力的模块。**

- 模块之间的交互不写模块名，只写服务名
- 引擎不关心模块的内部实现
- 替换模块 = 拔掉旧铲斗、插上新铲斗

---

## 三、协议角色

协议定义了三种角色：

![协议三角色](./docs/assets/three-roles.svg?t=2)

### 引擎（Runtime）
- 提供基础动力：LLM 调用、会话调度、Prompt 构建、工具执行等基础动力
- 维护**服务注册表**（谁提供什么服务）
- 接收模块的请求，按服务名称路由到正确的模块
- 将回复返回给请求方
- 不解析消息负载的内容——只按信封地址转发

### 模块（Module）
- 启动时向引擎声明自己的能力和需求
- 通过标准耦合器接入引擎，获取引擎提供的各项服务
- 通过耦合器调用其他模块的服务（引擎负责路由）
- 不需要知道对方模块的实现语言、版本、作者

### 开发者（Developer）
- 按照协议实现 `Module` 接口 + 声明文件
- 模块可以写在任何语言中（Rust、Python、TypeScript……）
- 引擎提供 SDK 或参考实现

---

## 四、核心概念

### 4.1 服务（Service）

服务是协议中的一等公民。模块提供什么能力 = 模块注册了哪些服务。

```
服务命名规范：<领域>.<操作>
示例：
  emotion.detect     — 从文本检测情绪
  memory.recall      — 从记忆中检索历史
  memory.store       — 存储消息到记忆
  llm.chat           — 调用 LLM 生成回复
  schedule.dispatch  — 向调度器投递消息
```

服务名由模块开发者自行定义，引擎不校验命名规范（只做路由）。

### 4.2 声明（Declaration）

模块启动时发送的「身份卡」，包含：

| 字段 | 说明 | 必填 |
|------|------|------|
| `module_id` | 模块唯一标识 | 是 |
| `name` | 人类可读名称 | 是 |
| `version` | 语义版本号 | 是 |
| `author.name` | 作者名 | 是 |
| `author.contact` | 联系方式 | 是 |
| `author.description` | 模块用途描述 | 是 |
| `author.license` | 许可证 | 否 |
| `provides[]` | 提供的服务列表 | 是 |
| `requires[]` | 依赖的服务列表 | 否 |
| `required_modules[]` | 依赖的模块 ID 列表 | 否 |
| `handlers[]` | 感兴趣的事件列表 | 否 |

### 4.3 耦合器（Coupling）

模块与引擎之间的连接器。模块通过耦合器调用服务：

```
调用方式：
  同步调用（等回复）：coupling.call("memory.recall", payload, timeout=5)
  异步触发（不等回复）：coupling.fire("schedule.dispatch", payload)
  广播：coupling.broadcast("system.alert", payload)
  声明身份：coupling.declare(declaration)
```

耦合器内部将调用包装为标准消息信封，通过引擎路由。

### 4.4 消息信封（Message Envelope）

所有模块间交互以标准信封传输：

```json
{
  "id": "a1b2c3d4-e5f6-...",
  "from": "emotion",
  "to": "memory.recall",
  "kind": "request",
  "payload": { "session_id": "...", "limit": 20 },
  "reply_to": null,
  "timestamp": 1718000000000
}
```

引擎只读 `to` 字段做路由，不检查 `payload` 内容。

### 4.5 依赖检查

引擎在收到所有声明后执行：

1. 汇总所有模块声明的 `provides` → 建立服务注册表
2. 对每个模块的 `requires`，检查是否已有模块提供了该服务
3. 如有缺失，引擎拒绝启动缺失依赖的模块，返回错误列表

这样，模块启动时就知道自己的依赖是否齐全，不会在运行时因找不到服务而崩溃。

---

## 五、协议流程

### 5.1 启动流程

![启动流程](./docs/assets/startup-flow.svg?t=1)

### 5.2 运行时消息流

![运行时消息流](./docs/assets/runtime-flow.svg?t=2)

模块 A 不知道 `foo.bar` 由谁提供。引擎查服务注册表→找到模块 B→转发→返回结果。

---

## 六、协议不做什么

| 不做的事 | 原因 |
|---------|------|
| 定义消息负载的 schema | 引擎不解析负载，只做信封路由 |
| 规定序列化格式 | 建议 JSON，但协议层只要求 key-value 可读结构 |
| 提供语言级 SDK | 协议定义接口，各语言自行实现 |
| 强制集群/分布式 | 单进程多模块也适用 |
| 管理模块间安全 | 信任模式由引擎实现决定，协议不规定 |
| 规定错误处理策略 | 重试、退避、熔断由模块自行决定 |

---

## 七、现有实现

| 实现 | 语言 | 状态 | 仓库 |
|------|------|------|------|
| 透闪石（Tremolite） | Rust | ⚡ 已实现核心协议 | https://github.com/spicysugar/tremolite |
| 你的名字 | - | ✍️ 等你来写 | - |

---

## 八、快速开始

见 [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)。

---

## 九、协议版本

当前版本：**draft-01**

协议处于草案阶段。任何实现 Artic Protocol 的系统，请标记其支持的协议版本。

版本号格式：`draft-NN` 或 `vMAJOR.MINOR`（定稿后）。

---

## 十、模块打包

详见 [SPEC.md 第 10 节](SPEC.md#10-%E6%A8%A1%E5%9D%97%E6%89%93%E5%8C%85%E6%A0%BC%E5%BC%8Fmodule-package-format) 的 **模块包格式（`.amod`）** 规范。

`.amod` 包将模块的代码、清单和资源打包为一个可分发的归档文件——就像智能体模块的 APK。安装方式：

```bash
tremolite module install emotion-detect-v1.0.0.amod
```

示例包在 [`examples/packaging/`](examples/packaging/) 目录下。

</details>
