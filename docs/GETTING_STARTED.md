# 快速开始

> 5 分钟内让一个模块跑起来。

---

## 1. 选择一个引擎

目前 Artic Protocol 的参考实现：

| 引擎 | 语言 | 状态 |
|------|------|------|
| [透闪石 (Tremolite)](https://github.com/spicysugar/tremolite) | Rust | ✅ 已实现核心协议 |

计划中的实现：欢迎提交 PR。

---

## 2. 编写你的第一个模块

以透闪石的 Rust SDK 为例。

### 2.1 创建一个新的模块 crate

```bash
cd tremolite/crates/
cargo new --lib my-module
```

### 2.2 添加依赖

在 `Cargo.toml` 中添加：

```toml
[dependencies]
tremolite-core = { path = "../tremolite-core" }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

### 2.3 实现 Module trait

```rust
use std::any::Any;
use tremolite_core::protocol::types::*;
use tremolite_core::module::*;

pub struct HelloModule {
    coupling: Option<PowerCoupling>,
}

impl HelloModule {
    pub fn new() -> Self {
        Self { coupling: None }
    }
}

impl Module for HelloModule {
    fn id(&self) -> &str { "hello" }
    fn name(&self) -> &str { "你好模块" }
    fn version(&self) -> &str { "0.1.0" }

    fn provides(&self) -> Vec<Capability> {
        vec!["hello.greet".into()]
    }

    fn requires(&self) -> Vec<Capability> {
        vec![]  // 不需要任何服务
    }

    // ── 声明能力（新协议） ──

    fn declaration(&self) -> Option<ModuleDeclaration> {
        Some(ModuleDeclaration {
            module_id: self.id().to_string(),
            name: self.name().to_string(),
            version: self.version().to_string(),
            author: ModuleAuthor {
                name: "你的名字".into(),
                contact: "你的联系方式".into(),
                description: "一个示例模块，展示 Artic Protocol 的基本用法".into(),
                license: Some("MIT".into()),
                signature: None,
            },
            provides: vec![
                ServiceDefinition {
                    name: "hello.greet".into(),
                    description: "向用户打招呼".into(),
                },
            ],
            requires: vec![],
            required_modules: vec![],
            handlers: vec!["startup".into()],
        })
    }

    fn set_coupling(&mut self, coupling: PowerCoupling) {
        self.coupling = Some(coupling);
    }

    fn on_message(&mut self, event: MessageEvent) -> Result<Vec<ModuleMessage>, ModuleError> {
        match event {
            MessageEvent::Request(msg) => {
                // 收到 "hello.greet" 请求
                let name = msg.payload.get("name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("世界");
                let reply = format!("你好，{}！欢迎使用 Artic Protocol。", name);

                if let Some(ref coupling) = self.coupling {
                    let _ = coupling.reply(&msg, serde_json::json!({
                        "greeting": reply
                    }));
                }
                Ok(vec![])
            }
            _ => Ok(vec![]),
        }
    }

    fn as_any(&self) -> Option<&dyn Any> { Some(self) }
    fn as_any_mut(&mut self) -> Option<&mut dyn Any> { Some(self) }
}
```

### 2.4 注册模块

在引擎的 `main.rs` 中找到模块注册部分，加入你的模块：

```rust
let _ = engine.register_module(Box::new(HelloModule::new()));
```

### 2.5 运行

```bash
cargo run -- run
```

你的模块已经接入引擎了。

---

## 3. 模块与服务交互

你的模块可以通过耦合器调用其他模块的服务。例如在你的 `on_message` 中获取历史记忆：

```rust
fn on_message(&mut self, event: MessageEvent) -> Result<Vec<ModuleMessage>, ModuleError> {
    match event {
        MessageEvent::Event(msg) if msg.to == "startup" => {
            // 启动时记录一个问候到记忆
            if let Some(ref coupling) = self.coupling {
                let _ = coupling.fire("memory.store", serde_json::json!({
                    "content": "你好模块已启动",
                    "tags": ["system", "hello"]
                }));
            }
        }
        _ => {}
    }
    Ok(vec![])
}
```

---

## 4. 发布你的模块

1. 你的模块代码不一定要合入引擎项目——它可以是一个独立仓库
2. 开发者使用你的模块时拷贝 `HelloModule` 的模式即可
3. 如果你的模块需要特殊配置，可以在引擎的 `[modules.<id>]` 配置段中添加
