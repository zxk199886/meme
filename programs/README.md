# programs — Anchor 工作区（链上程序）

独立的 Rust/Cargo + Anchor 工作区，**不**并入 pnpm workspace。构建后将 `target/idl/*.json`
与类型拷入 `packages/shared/src/idl/`，供 TS 端使用。Phase 3 起实现。

## 程序
- `leaderboard` — 固定大小 top-N 链上排行榜（授权写入）。Phase 3。
- `reward-distributor` — P2E 代币发放，授权门控 + 每钱包窗口上限（**价值程序，必审计**）。Phase 4。
- `pvp-betting` — PVP 下注托管/结算/退款（**价值程序，必审计**）。Phase 5。

详见 `docs/06-smart-contract-spec.md` 与 `docs/07-security-anticheat.md`。

## 工具链（版本须 pin 一致）
- Anchor `^0.30`、Solana CLI（Agave）`^1.18`、stable Rust。
- 本地用 `solana-test-validator`；测试网用 devnet（先）；主网仅审计后。

## 常用命令（实现后）
```bash
anchor build
anchor test            # 含失败路径：越权/重复/超额
anchor deploy --provider.cluster devnet
```
