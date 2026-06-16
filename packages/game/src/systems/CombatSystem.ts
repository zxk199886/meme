import Phaser from "phaser";
import { FEEDBACK } from "../config/constants";

/**
 * 打击感辅助：命中顿帧（hit-stop）、屏震、击退。
 * 伤害的具体扣血由各实体的 takeDamage 处理；本系统只负责"手感"层。
 */
export class CombatSystem {
  private scene: Phaser.Scene;
  private hitStopActive = false;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
  }

  /** 全局短暂顿帧：暂停物理 + 慢放计时，real-time 后恢复。 */
  hitStop(ms = FEEDBACK.hitStopMs): void {
    if (this.hitStopActive) return;
    this.hitStopActive = true;
    const world = this.scene.physics.world;
    world.pause();
    // 用 real-time 计时恢复（不受 timeScale / 物理暂停影响）
    window.setTimeout(() => {
      world.resume();
      this.hitStopActive = false;
    }, ms);
  }

  shake(duration = FEEDBACK.shakeDurationMs, intensity = FEEDBACK.shakeIntensity): void {
    this.scene.cameras.main.shake(duration, intensity);
  }

  /** 命中反馈组合：顿帧 + 屏震 + 火花。 */
  impact(x: number, y: number, heavy = false): void {
    this.hitStop(heavy ? FEEDBACK.heavyHitStopMs : FEEDBACK.hitStopMs);
    this.shake(
      FEEDBACK.shakeDurationMs,
      heavy ? FEEDBACK.heavyShakeIntensity : FEEDBACK.shakeIntensity,
    );
    this.spark(x, y, heavy);
  }

  /** 命中火花（程序化粒子）。 */
  spark(x: number, y: number, heavy = false): void {
    const n = heavy ? 8 : 5;
    for (let i = 0; i < n; i++) {
      const p = this.scene.add.image(x, y, "tex_spark").setDepth(50);
      const angle = Phaser.Math.FloatBetween(0, Math.PI * 2);
      const dist = Phaser.Math.Between(6, heavy ? 22 : 14);
      this.scene.tweens.add({
        targets: p,
        x: x + Math.cos(angle) * dist,
        y: y + Math.sin(angle) * dist,
        alpha: 0,
        scale: 0.2,
        duration: 220,
        onComplete: () => p.destroy(),
      });
    }
  }

  /** 把目标从 sourceX 方向推开。 */
  knockback(
    body: Phaser.Physics.Arcade.Body,
    sourceX: number,
    force: number,
    upward = 80,
  ): void {
    const dir = body.x < sourceX ? -1 : 1;
    body.setVelocity(dir * force, -upward);
  }
}
