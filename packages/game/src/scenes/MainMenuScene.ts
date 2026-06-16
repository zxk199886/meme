import Phaser from "phaser";
import { LOGICAL_WIDTH, COLORS } from "../config/constants";

export class MainMenuScene extends Phaser.Scene {
  constructor() {
    super("MainMenu");
  }

  create(): void {
    const cx = LOGICAL_WIDTH / 2;

    this.cameras.main.setBackgroundColor(COLORS.bg);

    this.add
      .text(cx, 70, "齐 天 大 圣", {
        fontFamily: "monospace",
        fontSize: "34px",
        color: "#ffcf6b",
        stroke: "#d94f2a",
        strokeThickness: 4,
      })
      .setOrigin(0.5);
    this.add
      .text(cx, 108, "Monkey Saga · 像素西游", {
        fontFamily: "monospace",
        fontSize: "11px",
        color: "#e8d8a0",
      })
      .setOrigin(0.5);

    const start = this.add
      .text(cx, 168, "▶ 开始游戏（Enter / 点击）", {
        fontFamily: "monospace",
        fontSize: "13px",
        color: "#f0c84a",
      })
      .setOrigin(0.5)
      .setInteractive({ useHandCursor: true });

    this.tweens.add({
      targets: start,
      alpha: 0.4,
      duration: 700,
      yoyo: true,
      repeat: -1,
    });

    this.add
      .text(
        cx,
        220,
        "移动 ←→/AD　跳跃 空格/W　轻击 J　重击 K\n闪避 Shift　定身法 U　神龛交互 E",
        {
          fontFamily: "monospace",
          fontSize: "9px",
          color: "#9b8fb0",
          align: "center",
          lineSpacing: 4,
        },
      )
      .setOrigin(0.5);

    const begin = () => this.scene.start("Game");
    start.on("pointerdown", begin);
    this.input.keyboard?.once("keydown-ENTER", begin);
    this.input.keyboard?.once("keydown-SPACE", begin);
  }
}
