/**
 * 客户端 / 后端 / 链上共享的 TS 类型契约（Phase 1 占位）。
 * 详见 docs/02-tech-architecture.md、docs/06-smart-contract-spec.md、docs/07。
 */

/** 开局向后端申请的会话凭证 */
export interface SessionNonce {
  nonce: string;
  wallet: string;
  /** 过期时间戳（ms） */
  expiresAt: number;
}

/** 通关时客户端提交给后端校验的成绩 */
export interface ScoreSubmission {
  wallet: string;
  nonce: string;
  score: number;
  kills: number;
  durationMs: number;
  /** 紧凑重放日志或其哈希，用于服务端无头重放校验 */
  replayHash: string;
}

/** 排行榜单条 */
export interface LeaderboardEntry {
  player: string;
  score: number;
  ts: number;
}

/** 领取代币奖励请求（每 nonce 幂等） */
export interface RewardClaim {
  wallet: string;
  nonce: string;
  amount: number;
}
