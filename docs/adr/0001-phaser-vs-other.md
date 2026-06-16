# ADR 0001 · 游戏引擎选 Phaser 3

- 状态：已接受
- 日期：2026-06-16

## 背景
需要一个网页可运行的 2D 横版动作游戏引擎，要求像素渲染、AABB 物理、tilemap、
精灵动画、活跃生态、TypeScript 友好。

## 决策
采用 **Phaser 3（`^3.80`，Arcade Physics）**。

## 理由
- 成熟稳定的 2D 引擎，Arcade Physics 对平台跳跃足够（无需 Matter 的斜坡/布娃娃）。
- 原生支持 Tiled JSON tilemap 与 Aseprite atlas，美术管线顺畅。
- TS 支持好、社区资料多、与 Vite HMR 配合佳。
- 避开 Phaser 4 beta（生产不用）。

## 备选与否决
- **PixiJS + 自写物理**：更底层，平台游戏要自造轮子，开发慢。
- **Godot/Unity（导出 WebGL）**：画面/工具更强，但包体大、与钱包/DOM 集成更别扭，
  对"浏览器秒开 + Web3"目标过重。
- **Phaser 4 beta**：不稳定，不用于生产。
