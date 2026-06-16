# 04 · 分阶段路线图（Roadmap）

> 原则：**先 devnet、先安全**；链不进入"好玩"的关键路径——Phase 2 离线必须先好玩。

## Phase 1 — 设计文档 + 仓库骨架（无玩法代码）✅ 当前
**交付物**：本 `docs/*` 全部文档 + pnpm 单仓库骨架（目录、配置、占位）。
**退出标准**：GDD + tokenomics + 合约规范评审通过；`pnpm install` 根目录成功。

## Phase 2 — 可玩离线像素横版（无链）
**交付物**：浏览器里完整可玩的一关。
- Vite + Phaser + TS 跑起来（HMR）。
- 场景流：`Boot → Preload → MainMenu → Game → GameOver` + 并行 `UIScene`。
- 玩家：移动、跳跃（coyote/jump buffer）、金箍棒轻/重击 + 连招、翻滚闪避（完美闪避窗口）、
  定身法；专注/气力/法力资源条。
- 一张 Tiled 关卡：平台、陷阱、神龛检查点、跟随相机。
- 1–2 种小怪（巡逻+追击+接触伤害）+ 1 个两阶段 Boss。
- HP/法力条、计分、胜负条件；基础打击感（顿帧/震屏/受击闪白）+ 基础音效。
- **退出标准**：离线就好玩且完整，无任何钱包代码。

## Phase 3 — 钱包登录 + 链上排行榜（devnet）
**交付物**：连钱包、提交校验过的分数到 devnet、看排行榜。
- React 外壳包住游戏；`WalletMultiButton` 接 Phantom（devnet）。
- `Web3Bridge` 接通：`LEVEL_CLEARED → React → 后端`。
- 后端 `/session-nonce`、`/score`、`/leaderboard` 上线 + 基础分数校验器（边界检查）。
- Anchor `leaderboard` 程序部署 devnet（固定大小 top-N 单 PDA，授权写入）。
- React `Leaderboard` 面板读取（链上或后端缓存）。
- **退出标准**：真实钱包可登录、通关、上 devnet 排行榜；作弊分数被校验器拒绝。

## Phase 4 — 代币奖励(P2E) + NFT 角色/装备（devnet）
**交付物**：赚 SPL 代币 + 铸造/装备 NFT 皮肤。
- 创建 SPL 奖励代币（devnet），mint authority 在后端。
- `reward-distributor`（或后端直接 SPL mint）按校验通过的通关发放；客户端永不铸币。
- `/claim` 幂等接口（每 nonce 一次），authority 签名。
- Metaplex Core 铸造皮肤/金箍棒变体；`MintPanel` 让用户花代币/SOL 铸造并选中已拥有 NFT，
  经 `NFT_SKIN_SELECTED` 让 Phaser 切换玩家 spritesheet。
- 按 tokenomics 定义代币 sink（铸造消耗销毁/进 treasury）。
- **退出标准**：devnet 完整 P2E 闭环——打怪赚币 → 花币铸皮肤 → 换皮肤继续玩。

## Phase 5 — PVP 下注（延伸目标，需先审计）
**交付物**：两名玩家质押代币，胜者拿池（扣 rake）。
- Anchor `pvp-betting`：建局（PDA 托管）→ 双方质押 → 结算（authority/oracle 报结果、
  payout、rake 进 treasury）→ 超时退款。
- 先做异步刷分对战（最简），再考虑实时网络同步。
- 结果上报沿用 authority-signer 模式；考虑 commit-reveal/服务端仲裁防篡改。
- **退出标准**：两个 devnet 钱包可下注、对战、胜者链上拿池。
- **本阶段上任何主网真实金钱前，必须通过专业合约审计。**

## 跨阶段约束
- devnet 优先；mainnet 仅在 Phase 4 稳固 + 审计后。
- 游戏核心做成确定性（固定步长 + 种子 RNG），支撑重放反作弊与可复现测试。
- `programs/` 不并入 pnpm workspace，由 Anchor 独占；IDL 管道拷入 `packages/shared`。
