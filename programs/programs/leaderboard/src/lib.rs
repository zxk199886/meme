//! leaderboard — 固定大小 top-N 链上排行榜（授权写入）。
//!
//! Phase 1 占位：仅记录意图，实现于 Phase 3。
//! 账户/指令/错误规范见 docs/06-smart-contract-spec.md。
//!
//! 规划要点：
//! - Leaderboard 单 PDA（seeds ["leaderboard", season]），entries 固定大小 [Entry; 100]。
//! - submit_score 要求 signer == AUTHORITY_PUBKEY（server-submit，见 docs/adr/0004）。
//! - 可选 ScoreReceipt PDA（seeds ["receipt", nonce]）实现幂等防重复提交。

// use anchor_lang::prelude::*;
// declare_id!("Leaderboard1111111111111111111111111111111");
//
// #[program]
// pub mod leaderboard { /* initialize, submit_score */ }
