import Phaser from "phaser";

/** 分数 / 灵蕴文本（HUD 右上）。 */
export class ScoreLabel {
  private text: Phaser.GameObjects.Text;

  constructor(scene: Phaser.Scene, x: number, y: number) {
    this.text = scene.add
      .text(x, y, "", {
        fontFamily: "monospace",
        fontSize: "10px",
        color: "#f0c84a",
      })
      .setOrigin(1, 0)
      .setScrollFactor(0)
      .setDepth(102);
  }

  set(score: number, lingyun: number): void {
    this.text.setText(`分数 ${score}   灵蕴 ${lingyun}`);
  }
}
