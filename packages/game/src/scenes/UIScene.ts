import Phaser from "phaser";
import { LOGICAL_WIDTH, COLORS } from "../config/constants";
import { HealthBar } from "../ui/HealthBar";
import { ScoreLabel } from "../ui/ScoreLabel";
import type { GameScene } from "./GameScene";

/**
 * HUD 叠层（与 GameScene 并行运行）。每帧从 GameScene.hudState() 读取并刷新。
 */
export class UIScene extends Phaser.Scene {
  private gs!: GameScene;
  private hpBar!: HealthBar;
  private staminaBar!: HealthBar;
  private manaBar!: HealthBar;
  private focusBar!: HealthBar;
  private scoreLabel!: ScoreLabel;
  private bossBar!: HealthBar;
  private bossLabel!: Phaser.GameObjects.Text;

  constructor() {
    super("UI");
  }

  create(): void {
    this.gs = this.scene.get("Game") as unknown as GameScene;

    // 左上：玩家资源条
    this.hpBar = new HealthBar(this, 8, 8, 96, 9, 0xd64545, "HP");
    this.staminaBar = new HealthBar(this, 8, 20, 72, 6, 0x6fbf4f, "气");
    this.manaBar = new HealthBar(this, 8, 28, 72, 6, 0x4f8fd6, "法");
    this.focusBar = new HealthBar(this, 8, 36, 72, 5, COLORS.shrine, "专");

    // 右上：分数 / 灵蕴
    this.scoreLabel = new ScoreLabel(this, LOGICAL_WIDTH - 8, 8);

    // 顶部中：Boss 血条（初始隐藏）
    this.bossBar = new HealthBar(this, LOGICAL_WIDTH / 2 - 90, 20, 180, 9, 0xcf5fd0);
    this.bossLabel = this.add
      .text(LOGICAL_WIDTH / 2, 12, "白衣判官", {
        fontFamily: "monospace",
        fontSize: "8px",
        color: "#e8e4f0",
      })
      .setOrigin(0.5, 0)
      .setScrollFactor(0)
      .setDepth(102);
    this.bossBar.setVisible(false);
    this.bossLabel.setVisible(false);
  }

  update(): void {
    if (!this.gs || !this.gs.scene.isActive()) return;
    const s = this.gs.hudState();
    this.hpBar.setRatio(s.hp);
    this.staminaBar.setRatio(s.stamina);
    this.manaBar.setRatio(s.mana);
    this.focusBar.setRatio(s.focus);
    this.scoreLabel.set(s.score, s.lingyun);

    this.bossBar.setVisible(s.bossActive);
    this.bossLabel.setVisible(s.bossActive);
    if (s.bossActive) {
      this.bossBar.setRatio(s.bossRatio);
      this.bossLabel.setText(s.bossPhase === 2 ? "白衣判官 · 二阶段" : "白衣判官");
    }
  }
}
