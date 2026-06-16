# 06 · 链上程序规范（Smart Contract Spec）

> 全部用 **Anchor `^0.30`**。先 devnet，涉及价值的程序上主网前**必须审计**。
> 以下为账户/指令草案，实现时以 IDL 为准并拷入 `packages/shared/src/idl/`。

## 通用约定
- **authority 模式**：写入价值/分数的指令 `require!(ctx.accounts.authority.key() == AUTHORITY_PUBKEY)`，
  AUTHORITY 私钥**只在后端**（server-submit 模式）。
- **幂等**：每次写入以 `nonce`（或 session id）为种子的 PDA / 记录去重，防重复领取。
- **PDA seeds** 文档化，避免碰撞；账户**固定大小**，避免 rent 膨胀。
- 所有可失败处用 `require!` + 自定义 `#[error_code]`。

---

## 1. `leaderboard` — 链上排行榜
**目标**：维护固定大小 top-N 高分榜（如 N=100），授权写入。

**账户**
- `Leaderboard`（单 PDA，seeds `["leaderboard", season_id]`）：
  - `authority: Pubkey`
  - `season: u16`
  - `entries: [Entry; 100]`（固定大小，`Entry { player: Pubkey, score: u64, ts: i64 }`）
  - `min_score: u64`（当前入榜门槛，便于快速拒绝）

**指令**
- `initialize(season)` — 创建榜（authority）。
- `submit_score(player, score, nonce)` —
  - `require!(authority == AUTHORITY_PUBKEY)`
  - 校验 `score > min_score` 才尝试插入；插入后维持有序、更新 `min_score`。
  - 幂等：可选 `ScoreReceipt` PDA（seeds `["receipt", nonce]`）防重复提交。

**错误**：`Unauthorized`、`ScoreTooLow`、`AlreadySubmitted`。

> 全量榜单存 Postgres 缓存；链上只放 top-N 固定大小，控制 compute/rent。

---

## 2. `reward-distributor` — P2E 代币发放（**价值程序，必审计**）
**目标**：按服务端校验通过的成绩，发放 SPL 奖励代币给玩家 ATA；客户端永不铸币。

**账户**
- `Config`（PDA `["config"]`）：`authority`、`reward_mint`、`treasury`、
  `per_wallet_window_cap: u64`、`window_secs: i64`。
- `ClaimReceipt`（PDA `["claim", nonce]`）：防重复领取（幂等）。
- `WalletQuota`（PDA `["quota", wallet]`）：`window_start: i64`、`minted_in_window: u64`。

**指令**
- `init_config(reward_mint, treasury, cap, window)` — authority。
- `claim_reward(player, amount, nonce)` —
  - `require!(authority == AUTHORITY_PUBKEY)`
  - 创建/检查 `ClaimReceipt[nonce]` 不存在（幂等）。
  - 更新 `WalletQuota`：滚动窗口内 `minted_in_window + amount <= cap`，否则报错（兜底防掏空）。
  - CPI 到 SPL Token：mint（或从金库 transfer）`amount` 到玩家 ATA。

**错误**：`Unauthorized`、`AlreadyClaimed`、`WindowCapExceeded`。

> 备选：MVP 可先不写此程序，由后端直接用 `@solana/spl-token` 以 mint authority 发放；
> 但用程序能把"每钱包窗口上限"等不变量固化在链上，更安全。

---

## 3. `pvp-betting` — PVP 下注托管（Phase 5，**必审计**）
**目标**：两名玩家质押代币，胜者拿池（扣 rake），含超时退款。

**账户**
- `Match`（PDA `["match", match_id]`）：
  `creator`、`opponent: Option<Pubkey>`、`stake: u64`、`vault: Pubkey(ATA/PDA)`、
  `state: enum{Open,Locked,Settled,Refunded}`、`deadline: i64`、`result_authority: Pubkey`。

**指令**
- `create_match(match_id, stake)` — creator 质押进 vault。
- `join_match(match_id)` — opponent 质押；状态 → Locked。
- `settle(match_id, winner)` — `require!(signer == result_authority)`；
  payout 给 winner，rake 进 treasury；状态 → Settled。
- `refund(match_id)` — 超时未对上/未结算，退还质押；状态 → Refunded。

**防作弊**：结果由 `result_authority`（服务端/oracle）上报；考虑 commit-reveal 或服务端
仲裁，避免任一方篡改结果。

**错误**：`MatchNotOpen`、`Unauthorized`、`AlreadySettled`、`DeadlineNotPassed`。

---

## 测试与部署
- `programs/tests/*.ts`：每个程序的 Anchor mocha/ts 测试（含失败路径：越权、重复、超额）。
- `migrations/deploy.ts`：部署 + 初始化 Config/Leaderboard。
- 构建后将 `target/idl/*.json` 与类型拷入 `packages/shared/src/idl/`。
- devnet airdrop 脚本需重试退避（faucet 不稳）。
