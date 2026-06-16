import Phaser from "phaser";
import { LOGICAL_WIDTH, COLORS } from "../config/constants";
import type { GameToShellEvents } from "../web3/events";

export interface GameOverData {
  victory: boolean;
  score: number;
  kills: number;
  durationMs: number;
}

/**
 * 胜利 / 失败结算 + 重开。
 * 通关时预留 LEVEL_CLEARED 事件钩子：Phase 3 接 Web3Bridge 提交成绩上链，
 * MVP 仅 console 打印 + 本地展示（见 docs/02、docs/07）。
 */
export class GameOverScene extends Phaser.Scene {
  constructor() {
    super("GameOver");
  }

  create(data: GameOverData): void {
    const cx = LOGICAL_WIDTH / 2;
    this.cameras.main.setBackgroundColor(COLORS.bg);

    const title = data.victory ? "通 关 !" : "天命未竟…";
    const titleColor = data.victory ? "#f0c84a" : "#cf5fd0";

    this.add
      .text(cx, 70, title, {
        fontFamily: "monospace",
        fontSize: "30px",
        color: titleColor,
        stroke: "#000000",
        strokeThickness: 3,
      })
      .setOrigin(0.5);

    this.add
      .text(
        cx,
        130,
        `分数 ${data.score}　击杀 ${data.kills}　用时 ${(data.durationMs / 1000).toFixed(1)}s`,
        { fontFamily: "monospace", fontSize: "11px", color: "#e8d8a0" },
      )
      .setOrigin(0.5);

    if (data.victory) {
      // Phase 3 衔接点：此处将通过 Web3Bridge 发出 LEVEL_CLEARED 给 React 外壳。
      const payload: GameToShellEvents["LEVEL_CLEARED"] = {
        score: data.score,
        kills: data.kills,
        durationMs: data.durationMs,
        replayHash: "offline-mvp", // Phase 3 用真实重放哈希替换
      };
      // eslint-disable-next-line no-console
      console.info("[LEVEL_CLEARED] (Phase 3 将上链)", payload);
      this.add
        .text(cx, 158, "（链上奖励将在 Phase 3 接入）", {
          fontFamily: "monospace",
          fontSize: "9px",
          color: "#9b8fb0",
        })
        .setOrigin(0.5);
    }

    const restart = this.add
      .text(cx, 200, "↻ 再来一次（Enter / 点击）", {
        fontFamily: "monospace",
        fontSize: "13px",
        color: "#ffcf6b",
      })
      .setOrigin(0.5)
      .setInteractive({ useHandCursor: true });

    this.tweens.add({
      targets: restart,
      alpha: 0.4,
      duration: 700,
      yoyo: true,
      repeat: -1,
    });

    const again = () => this.scene.start("Game");
    restart.on("pointerdown", again);
    this.input.keyboard?.once("keydown-ENTER", again);
  }
}
