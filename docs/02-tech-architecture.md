# 02 · 技术架构（Technical Architecture）

## 1. 技术栈
### 游戏客户端
| 关注点 | 选型 | 版本 | 说明 |
|---|---|---|---|
| 游戏引擎 | Phaser 3（Arcade Physics） | `^3.80` | 成熟 2D 引擎，AABB 物理适合横版 |
| 语言 | TypeScript（strict） | `^5.4` | — |
| 构建 / dev server | Vite | `^5` | 快速 HMR、原生 TS、静态资源 |
| 关卡工具 | Tiled → JSON tilemap | 最新 | Phaser 原生加载 |
| 美术工具 | Aseprite → spritesheet + atlas | — | Phaser 支持 Aseprite atlas |

### Solana / Web3（前端）
| 关注点 | 选型 | 版本 |
|---|---|---|
| RPC / 交易 | `@solana/web3.js` | `^1.95`（v1 线，生态兼容性最好） |
| 钱包连接 | `@solana/wallet-adapter-base/-react/-wallets/-react-ui` | `^0.9 / ^0.15 / ^0.19 / ^0.9` |
| Anchor 客户端 | `@coral-xyz/anchor` | `^0.30`（与链上版本一致） |
| SPL 代币 | `@solana/spl-token` | `^0.4` |
| NFT | `@metaplex-foundation/umi` + `mpl-core` | umi `^0.9`，core `^0.x` |

### 链上程序
| 关注点 | 选型 | 版本 |
|---|---|---|
| 程序框架 | Anchor（Rust） | `^0.30` |
| 工具链 | stable Rust + Solana CLI（Agave） | `^1.18` |
| 代币 | SPL Token（如需转账费/元数据扩展再用 Token-2022） | — |
| 本地链 | `solana-test-validator` / Anchor localnet | — |

### 后端（授权签名方 + API，Phase 3 起）
| 关注点 | 选型 | 说明 |
|---|---|---|
| 运行时 | Node 20 + TypeScript | 与客户端共享类型 |
| 框架 | Fastify | 轻量；Express 亦可 |
| 数据库 | Postgres（MVP 可用 SQLite） | 缓存排行榜、会话 nonce、重放日志 |
| 部署 | 后端 Railway/Fly.io；前端 Vercel/Netlify/Cloudflare Pages（静态） | — |

> **版本 pin 纪律**：链上 Anchor 版本、TS 端 `@coral-xyz/anchor`、Solana CLID
> 三者必须一致，否则 IDL/序列化会出错。任何升级都更新本文件并记录。

## 2. 架构：Phaser 如何与 Solana 通信
### 推荐方案：React 外壳 + Phaser canvas 岛屿
Phaser 渲染到 `<canvas>`、不感知 React；而 `@solana/wallet-adapter-react-ui` 是
React 优先且自带成熟组件（`WalletMultiButton`、连接弹窗）。最省事的做法是两者并存：

```
┌─────────────────────────────────────────────────────┐
│ React App (web-shell)                                │
│ <ConnectionProvider><WalletProvider><WalletModal…>  │
│   ┌────────────┐  ┌───────────────────────────────┐ │
│   │ WalletBtn  │  │ Leaderboard / MintPanel (DOM) │ │
│   └────────────┘  └───────────────────────────────┘ │
│   ┌───────────────────────────────────────────────┐ │
│   │ <div id="game-root">  Phaser canvas           │ │
│   └───────────────────────────────────────────────┘ │
│         Web3Bridge (typed EventEmitter)             │
│   React: 钱包/连接状态  ⇄  Phaser: 游戏事件          │
└─────────────────────────────────────────────────────┘
```

- React 负责页面框架 + 钱包按钮 + 排行榜 + 铸造面板（普通 DOM，用 CSS 叠在 canvas 周围/上层）。
- `<GameContainer>` 在 `useEffect` 里 `new Phaser.Game({ parent: 'game-root', ... })`，卸载时销毁。
- 通信走**单一强类型事件总线 `Web3Bridge`**（小 EventEmitter / mitt）：
  - React → Phaser：`WALLET_CONNECTED({publicKey})`、`WALLET_DISCONNECTED`、`NFT_SKIN_SELECTED({mint})`
  - Phaser → React：`LEVEL_CLEARED({score,kills,durationMs,replayHash})`、`REQUEST_CLAIM_REWARD`、`GAME_OVER`
- **Phaser 永不直接 import `@solana/web3.js`**；它只发"意图"事件，React 执行交易后回传结果。
  链逻辑集中在 React/后端，游戏包保持干净。

> 备选方案及取舍记录见 `adr/0002-react-island-wallet.md`。

## 3. 链下 vs 链上边界（反作弊核心）
浏览器是可被完全检视的敌对环境。铁律：**客户端永不直接铸币、永不写未校验分数上链。**

```
1. 开局   client GET /session-nonce        → 服务端发放绑定钱包、限时、一次性 nonce
2. 游玩   ScoreSystem 累积分数；可记录紧凑输入/事件重放日志
3. 通关   client POST /score {wallet,nonce,score,kills,durationMs,replayLog/hash}
4. 校验   服务端：nonce 有效未用未过期且绑定此钱包；分数在合理边界；
          （可选）无头重放重算分数；按钱包/IP 限流
5a 排行榜 服务端用 AUTHORITY 签名提交链上 leaderboard（server-submit）
5b 奖励   服务端（持 mint authority）铸/转 N 个 SPL 代币到玩家 ATA
```

两种链上写入模式（详见合约规范）：
- **server-submit（推荐 MVP）**：后端 authority 签名发交易；UX 干净、后端付 gas。
- **server-attest + client-submit**：后端返回 Ed25519 签名凭证，链上程序验签后记录；
  玩家钱包签名并付费、更去中心化但更复杂。

## 4. 环境
- **本地**：`solana-test-validator` + Anchor localnet，快速迭代。
- **测试**：**devnet**（所有阶段默认）；前端连 devnet，写操作走后端 + 付费 RPC。
- **生产**：mainnet-beta，**仅在 Phase 4 稳固 + 合约审计后**。

## 5. 关键文件（实现时）
- `packages/game/src/main.ts` — Phaser 启动与配置，整个客户端入口。
- `packages/game/src/web3/Web3Bridge.ts` — 解耦 Phaser 与 Solana 的强类型事件总线（架构枢纽）。
- `packages/web-shell/src/WalletProvider.tsx` — wallet-adapter Providers + 挂载 Phaser canvas 的 React 岛。
- `packages/backend/src/services/authoritySigner.ts` — 服务端独占的 mint/leaderboard 授权私钥（反作弊核心）。
- `programs/programs/reward-distributor/src/lib.rs` — 授权门控的链上代币发放（必须审计）。
