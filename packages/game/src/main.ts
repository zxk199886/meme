import Phaser from "phaser";
import { gameConfig } from "./config/gameConfig";

/**
 * Monkey Saga — Phase 2 离线 MVP 入口。
 * 纯 Phaser 游戏；Phase 3 起由 React 外壳挂载并叠加钱包/排行榜 UI（见 docs/02）。
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const game = new Phaser.Game(gameConfig);

// 暴露到 window 便于调试（仅开发）
if (import.meta.env.DEV) {
  (window as unknown as { game: Phaser.Game }).game = game;
}
