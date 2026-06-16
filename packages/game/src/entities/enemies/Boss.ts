import Phaser from "phaser";
import { BOSS, COLORS } from "../../config/constants";
import { TEX } from "../../config/textures";
import { Enemy } from "./Enemy";

type BossAction = "approach" | "sweep" | "slam" | "summon" | "aoe";

/**
 * 白衣判官（Boss）：
 *  一阶段：横扫 + 跳劈。
 *  血量过半进二阶段：换紫色、加速、增加召唤小怪与范围 AOE。
 * 攻击伤害通过 gs.damagePlayerInArea 结算（确定性、无需动态 overlap）。
 */
export class Boss extends Enemy {
  private phase: 1 | 2 = 1;
  private nextActionAt = 0;
  private busyUntil = 0;
  private facing: 1 | -1 = -1;

  constructor(scene: Phaser.Scene, x: number, y: number) {
    super(scene, x, y, TEX.boss, {
      maxHp: BOSS.maxHp,
      contactDamage: BOSS.contactDamage,
      scoreValue: BOSS.scoreValue,
      lingyunValue: BOSS.lingyunValue,
      width: BOSS.width,
      height: BOSS.height,
    });
    this.knockbackResistant = true;
    this.setDepth(9);
  }

  get phaseNumber(): 1 | 2 {
    return this.phase;
  }
  get hpRatio(): number {
    return Math.max(0, this.hp) / this.maxHp;
  }

  private speedMul(): number {
    return this.phase === 2 ? BOSS.phase2SpeedMul : 1;
  }

  protected updateAI(now: number, _dt: number, playerX: number, playerY: number): void {
    // 阶段切换
    if (this.phase === 1 && this.hp <= this.maxHp * BOSS.phase2HpRatio) {
      this.enterPhase2(now);
    }

    this.facing = playerX < this.x ? -1 : 1;
    this.setFlipX(this.facing < 0);

    if (now < this.busyUntil) return; // 出招中

    if (now < this.nextActionAt) {
      // 冷却期：靠近玩家
      const dist = Math.abs(playerX - this.x);
      if (dist > 70) this.setVelocityX(this.facing * BOSS.walkSpeed);
      else this.setVelocityX(0);
      return;
    }

    this.chooseAction(now, playerX, playerY);
  }

  private chooseAction(now: number, playerX: number, _playerY: number): void {
    const dist = Math.abs(playerX - this.x);
    let action: BossAction;
    const rng = this.gs.rng;
    if (dist > 130) {
      action = "approach";
    } else if (this.phase === 2 && this.gs.gruntCount() < 3 && rng.next() < 0.35) {
      action = "summon";
    } else if (this.phase === 2 && rng.next() < 0.35) {
      action = "aoe";
    } else {
      action = rng.next() < 0.5 ? "sweep" : "slam";
    }
    this.perform(action, now);
  }

  private perform(action: BossAction, now: number): void {
    const cd = BOSS.actionCooldownMs * this.speedMul();
    switch (action) {
      case "approach":
        this.setVelocityX(this.facing * BOSS.chaseSpeed);
        this.busyUntil = now + 500 * this.speedMul();
        this.nextActionAt = now + 500 * this.speedMul();
        break;

      case "sweep": {
        // 横扫：原地蓄力 → 向前突进，前方扇形伤害
        this.telegraph(0xffe08a);
        const windup = 420 * this.speedMul();
        this.busyUntil = now + windup + 260 * this.speedMul();
        this.scene.time.delayedCall(windup, () => {
          if (this.isDead) return;
          this.setVelocityX(this.facing * 260);
          this.gs.damagePlayerInArea(
            this.x + this.facing * 30,
            this.y,
            40,
            BOSS.sweepDamage,
          );
          this.clearTint();
        });
        this.nextActionAt = now + windup + cd;
        break;
      }

      case "slam": {
        // 跳劈：跃起 → 落地范围震击
        this.telegraph(0xff9a6a);
        const windup = 360 * this.speedMul();
        this.busyUntil = now + windup + 400 * this.speedMul();
        this.scene.time.delayedCall(windup, () => {
          if (this.isDead) return;
          this.setVelocityY(-260);
          this.setVelocityX(this.facing * 120);
        });
        this.scene.time.delayedCall(windup + 360 * this.speedMul(), () => {
          if (this.isDead) return;
          this.gs.damagePlayerInArea(this.x, this.y + 10, 55, BOSS.slamDamage);
          this.gs.combat.impact(this.x, this.y + 20, true);
          this.clearTint();
        });
        this.nextActionAt = now + windup + cd;
        break;
      }

      case "summon": {
        this.telegraph(COLORS.bossPhase2);
        const windup = 500 * this.speedMul();
        this.busyUntil = now + windup;
        this.scene.time.delayedCall(windup, () => {
          if (this.isDead) return;
          for (let i = 0; i < BOSS.summonCount; i++) {
            this.gs.spawnGrunt(this.x + (i === 0 ? -40 : 40), this.y - 10);
          }
          this.clearTint();
        });
        this.nextActionAt = now + windup + cd;
        break;
      }

      case "aoe": {
        // 范围爆发：以自身为中心
        this.telegraph(COLORS.bossPhase2);
        const windup = 520 * this.speedMul();
        this.busyUntil = now + windup + 200;
        const ring = this.scene.add
          .circle(this.x, this.y, 10, COLORS.bossPhase2, 0.25)
          .setDepth(6);
        this.scene.tweens.add({
          targets: ring,
          radius: 90,
          alpha: 0,
          duration: windup,
          onComplete: () => ring.destroy(),
        });
        this.scene.time.delayedCall(windup, () => {
          if (this.isDead) return;
          this.gs.damagePlayerInArea(this.x, this.y, 90, BOSS.aoeDamage);
          this.gs.combat.impact(this.x, this.y, true);
          this.clearTint();
        });
        this.nextActionAt = now + windup + cd;
        break;
      }
    }
  }

  private telegraph(color: number): void {
    this.setVelocityX(0);
    this.setTint(color);
  }

  private enterPhase2(now: number): void {
    this.phase = 2;
    this.setTexture(TEX.bossPhase2);
    this.gs.onBossPhase2();
    // 进阶闪光
    this.setTintFill(0xffffff);
    this.scene.time.delayedCall(120, () => {
      if (!this.isDead) this.clearTint();
    });
    this.nextActionAt = now + 400;
  }
}
