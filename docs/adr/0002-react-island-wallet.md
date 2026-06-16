# ADR 0002 · 用 React 外壳 + Phaser canvas 岛屿集成钱包

- 状态：已接受
- 日期：2026-06-16

## 背景
Phaser 渲染到 `<canvas>` 且不感知 React；而 Solana 钱包生态
（`@solana/wallet-adapter-react-ui`）是 React 优先、自带成熟的连接按钮与弹窗。
需要在不与任一方对抗的前提下集成钱包。

## 决策
**React 外壳渲染页面框架与钱包/链 UI，Phaser 只占一个 `<div>` 画 canvas。**
两者通过单一强类型事件总线 `Web3Bridge` 通信；Phaser 不直接 import `@solana/web3.js`。

## 理由
- 直接复用 wallet-adapter 成熟组件（多钱包选择、重连 UX），不重造轮子。
- 链逻辑集中在 React/后端，游戏包保持干净、易测。
- 解耦：游戏只发"意图"事件，React 执行交易后回传结果。

## 备选与否决
- **纯 HTML、无 React、手搓 Phantom provider 连接**：失去成熟弹窗与多钱包 UX，
  自己重写连接/重连逻辑，不值。
- **把钱包 UI 放进 Phaser（DOM GameObject）**：脆弱，钱包弹窗期望在普通 DOM 中，避免。

## 影响
- MVP 可将 `web-shell` 与 `game` 合并为单个 Vite 应用（React 渲染页面、挂载 Phaser canvas）。
