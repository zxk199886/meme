//! pvp-betting — PVP 下注托管/结算/退款（**价值程序，上主网前必须审计**）。
//!
//! Phase 1 占位：仅记录意图，实现于 Phase 5（延伸目标）。
//! 账户/指令/错误规范见 docs/06-smart-contract-spec.md 与 docs/07-security-anticheat.md。
//!
//! 规划要点：
//! - Match PDA（creator, opponent, stake, vault, state, deadline, result_authority）。
//! - create_match / join_match / settle（require signer == result_authority）/ refund（超时退款）。
//! - 结果由 result_authority（服务端/oracle）上报；考虑 commit-reveal/服务端仲裁防篡改。

// use anchor_lang::prelude::*;
// declare_id!("PvpBetting11111111111111111111111111111111");
//
// #[program]
// pub mod pvp_betting { /* create_match, join_match, settle, refund */ }
