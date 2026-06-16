//! reward-distributor — P2E 代币发放（**价值程序，上主网前必须审计**）。
//!
//! Phase 1 占位：仅记录意图，实现于 Phase 4。
//! 账户/指令/错误规范见 docs/06-smart-contract-spec.md 与 docs/07-security-anticheat.md。
//!
//! 规划要点：
//! - Config PDA（authority, reward_mint, treasury, per_wallet_window_cap, window_secs）。
//! - ClaimReceipt PDA（seeds ["claim", nonce]）幂等防重复领取。
//! - WalletQuota PDA（seeds ["quota", wallet]）滚动窗口产出上限，兜底防掏空。
//! - claim_reward 要求 signer == AUTHORITY_PUBKEY；客户端永不铸币（见 docs/07）。

// use anchor_lang::prelude::*;
// declare_id!("RewardDistr1111111111111111111111111111111");
//
// #[program]
// pub mod reward_distributor { /* init_config, claim_reward */ }
