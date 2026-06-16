import Phaser from "phaser";
import { LOGICAL_WIDTH, LOGICAL_HEIGHT, COLORS } from "../config/constants";

/**
 * 资源加载 + 进度条骨架。
 * Phase 2 占位阶段几乎无外部资源（纹理已程序化生成），进度条保留为美术接入做准备。
 */
export class PreloadScene extends Phaser.Scene {
  constructor() {
    super("Preload");
  }

  preload(): void {
    const cx = LOGICAL_WIDTH / 2;
    const cy = LOGICAL_HEIGHT / 2;

    const barBg = this.add
      .rectangle(cx, cy, 200, 10, 0x000000, 0.5)
      .setStrokeStyle(1, COLORS.shrine);
    const bar = this.add.rectangle(cx - 98, cy, 2, 6, COLORS.shrine).setOrigin(0, 0.5);
    this.add
      .text(cx, cy - 24, "Monkey Saga", {
        fontFamily: "monospace",
        fontSize: "16px",
        color: "#f0c84a",
      })
      .setOrigin(0.5);

    this.load.on("progress", (p: number) => {
      bar.width = 196 * p;
    });
    this.load.on("complete", () => {
      barBg.destroy();
      bar.destroy();
    });

    // 真实美术/音频将在此 this.load.aseprite / this.load.audio 等接入。
  }

  create(): void {
    this.scene.start("MainMenu");
  }
}
