# Monkey Saga（工作名）— 像素风西游动作游戏 + Solana

> 一款受《西游记》/悟空题材启发的 **2D 像素横版动作过关** 游戏，结合 **Solana 链**
> （钱包登录、链上排行榜、代币奖励 P2E、NFT 角色/装备、PVP 下注）。
>
> ⚠️ **原创声明**：本项目灵感来自公有领域的《西游记》及悟空、金箍棒等经典题材，
> **不使用**《黑神话：悟空 / Black Myth: Wukong》的名称、Logo 或任何美术资产。
> 所有美术、音频、游戏名均为原创或经授权。"Monkey Saga" 为开发工作名，最终名待定。

## 这是什么

| 维度 | 内容 |
|---|---|
| 平台 | 网页浏览器 |
| 引擎 | Phaser 3 + TypeScript + Vite |
| 玩法 | 横版动作过关：金箍棒近战、闪避、定身法、Boss 两阶段 |
| 链 | Solana（钱包/排行榜/代币/NFT/PVP），devnet 优先 |
| 链上程序 | Anchor（Rust）：leaderboard / reward-distributor / pvp-betting |

## 仓库结构

```
docs/        设计文档（GDD、技术架构、tokenomics、路线图、美术、合约规范、安全）
packages/
  game/      Phaser 3 游戏本体（主交付物）
  web-shell/ React 外壳：钱包 UI + 排行榜 + NFT 铸造面板
  shared/    共享 TS 类型 / program IDs / IDL
  backend/   授权签名方 + API（反作弊核心，私钥只在此处）
programs/    Anchor 工作区（独立 Cargo 世界）
assets-src/  原创美术/音频源文件（.aseprite/.tmx，不打包进发布）
legacy/      旧的、与本项目无关的 Python 自动化脚本（已弃用，仅留档）
```

## 开发路线（详见 `docs/04-roadmap.md`）

1. **Phase 1**：设计文档 + 仓库骨架（当前）
2. **Phase 2**：可玩离线像素横版（无链）
3. **Phase 3**：钱包登录 + 链上排行榜（devnet）
4. **Phase 4**：代币奖励(P2E) + NFT 角色/装备（devnet）
5. **Phase 5**：PVP 下注（需先审计）

## 快速开始（骨架阶段）

```bash
pnpm install
pnpm --filter game dev      # Phase 2 起可启动游戏开发服务器
```

> 当前处于 Phase 1：文档与骨架已就绪，游戏代码将于 Phase 2 开始填充。

## 安全与合规要点

- 客户端**永不**直接铸币或写未校验分数上链；mint authority 私钥**只存在于后端**。
- 链上程序与代币**先在 devnet**，审计通过后才考虑主网。
- P2E/PVP 涉及真实价值，主网前需法律审查（见 `docs/07-security-anticheat.md`）。

详见 `docs/` 下各设计文档。
