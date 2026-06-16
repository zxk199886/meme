/**
 * Web3Bridge 事件契约（强类型）。
 *
 * 架构枢纽：Phaser 游戏只发"意图"事件，React 外壳执行链上交易后回传结果。
 * Phaser 永不直接 import @solana/web3.js。详见 docs/02-tech-architecture.md。
 *
 * Phase 1 占位：仅定义事件类型契约，实现于 Phase 2/3 填充。
 */

/** React 外壳 → Phaser 游戏 */
export interface ShellToGameEvents {
  WALLET_CONNECTED: { publicKey: string };
  WALLET_DISCONNECTED: void;
  /** 玩家选中已拥有的 NFT 皮肤，游戏据此切换 spritesheet */
  NFT_SKIN_SELECTED: { mint: string };
}

/** Phaser 游戏 → React 外壳 */
export interface GameToShellEvents {
  /** 通关：携带成绩，交由后端校验后再上链（见 docs/07） */
  LEVEL_CLEARED: {
    score: number;
    kills: number;
    durationMs: number;
    /** 紧凑输入/事件重放日志的哈希，用于服务端无头重放校验 */
    replayHash: string;
  };
  REQUEST_CLAIM_REWARD: { nonce: string };
  GAME_OVER: void;
}

export type Web3EventName = keyof ShellToGameEvents | keyof GameToShellEvents;
