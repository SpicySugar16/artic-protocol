# 如何加入 Artic Protocol

Artic Protocol 是一个开放协议。任何人都可以实现它、扩展它、在它的基础上构建新的引擎或模块。

---

## 角色

### 🏭 引擎开发者

如果你在写一个新的智能体引擎，想让第三方模块接入：

1. 实现 **消息路由**：收到 module_message 后按 `to` 字段查找服务注册表，转发到对应的模块
2. 实现 **服务注册表**：接收模块的 declaration，建立服务名 → 模块 ID 的映射
3. 实现 **耦合器**：创建 `PowerCoupling`，给模块一个可以 `call()` / `fire()` 的接口
4. 实现 **内建服务**：至少实现 `engine.module.list` 和 `engine.system.ping`
5. 实现 **生命周期管理**：触发 startup、shutdown 等事件

参考实现：[透闪石的引擎代码](https://github.com/spicysugar/tremolite/tree/main/crates/tremolite-core/src)

### 🔧 模块开发者

如果你想写一个能在 Artic 兼容引擎上跑的模块：

1. 实现 **Module 接口**：`id()`、`name()`、`version()`、`provides()`、`requires()`
2. 实现 **声明方法**：`declaration()` 返回模块的能力和作者信息
3. 实现 **消息处理**：`on_message()` 处理收到的请求和事件
4. 用 **耦合器** 获取引擎动力：`coupling.call("memory.recall", ...)`
5. 发布你的模块代码（独立仓库或合入某个引擎项目均可）

### 📝 协议贡献者

如果你想改进协议本身：

1. 提交 Issue 说明你的改进建议
2. 提交 Pull Request 修改 SPEC.md
3. 协议版本号在所有实现中同步更新

---

## 协议演进的规则

1. **只做加法**：新版本只能加字段，不能删或改已有字段
2. **服务名称是合约**：一旦某个服务名被多个模块使用，改变其接口需要主版本号变更
3. **实现先行**：新特性需要至少一个参考实现（不限语言）再合入 SPEC
4. **互操作性测试**：不同语言的实现应定期测试互相通信

---

## 社区

- 透闪石（参考实现）：https://github.com/spicysugar/tremolite
- 本协议仓库：https://github.com/spicysugar/artic-protocol

---

## 许可证

协议规范文档采用 **CC BY 4.0** 许可证。参考实现代码采用 **MIT** 许可证。
