# ADR 0003 · NFT 用 Metaplex Core（而非经典 Token Metadata）

- 状态：已接受（可在 Phase 4 复核）
- 日期：2026-06-16

## 背景
角色皮肤/武器变体需要 NFT。Solana 上主要有两条路：经典 **Token Metadata**
（Token + Metadata + 可选 Token-2022）与较新的 **Metaplex Core**（单账户 NFT）。

## 决策
新项目默认采用 **Metaplex Core**（`umi` + `mpl-core`）。

## 理由
- 单账户模型：更便宜（rent 更低）、铸造/管理更简单。
- 对全新、自己控制前后端的项目，无历史包袱，适合规模化铸造游戏资产。

## 备选与否决
- **经典 Token Metadata**：市场/钱包兼容性最广，但账户更多、成本更高、样板更繁。
  若后期需要最大化第三方市场兼容性，可在 Phase 4 复核切换或并行支持。

## 风险
- Core 生态/市场支持比经典路线薄一些；Phase 4 接入前确认目标市场/钱包对 Core 的支持。
