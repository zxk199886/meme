import Phaser from "phaser";

/**
 * 通用条组件（复用于 HP / 气力 / 法力 / Boss 血条）。
 * 用两个矩形：底框 + 填充；setRatio(0..1) 更新。
 */
export class HealthBar {
  private bg: Phaser.GameObjects.Rectangle;
  private fill: Phaser.GameObjects.Rectangle;
  private label?: Phaser.GameObjects.Text;
  private width: number;

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    width: number,
    height: number,
    color: number,
    label?: string,
  ) {
    this.width = width;
    this.bg = scene.add
      .rectangle(x, y, width, height, 0x000000, 0.6)
      .setOrigin(0, 0)
      .setStrokeStyle(1, 0x000000, 0.8)
      .setScrollFactor(0)
      .setDepth(100);
    this.fill = scene.add
      .rectangle(x + 1, y + 1, width - 2, height - 2, color)
      .setOrigin(0, 0)
      .setScrollFactor(0)
      .setDepth(101);
    if (label) {
      this.label = scene.add
        .text(x + 3, y + height / 2, label, {
          fontFamily: "monospace",
          fontSize: "8px",
          color: "#0d0b16",
        })
        .setOrigin(0, 0.5)
        .setScrollFactor(0)
        .setDepth(102);
    }
  }

  setRatio(ratio: number): void {
    const r = Phaser.Math.Clamp(ratio, 0, 1);
    this.fill.width = (this.width - 2) * r;
  }

  setVisible(v: boolean): void {
    this.bg.setVisible(v);
    this.fill.setVisible(v);
    this.label?.setVisible(v);
  }

  setPosition(x: number, y: number): void {
    this.bg.setPosition(x, y);
    this.fill.setPosition(x + 1, y + 1);
  }
}
