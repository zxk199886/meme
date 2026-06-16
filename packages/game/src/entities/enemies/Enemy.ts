import Phaser from "phaser";
import { COLORS } from "../../config/constants";
import type { GameScene } from "../../scenes/GameScene";

/**
 * 敌人基类：HP、受击、死亡、定身（frozen）。
 * 子类实现 updateAI()。GameScene 负责 overlap（玩家接触伤害、棍法命中）。
 */
export abstract class Enemy extends Phaser.Physics.Arcade.Sprite {
  declare body: Phaser.Physics.Arcade.Body;

  private static nextId = 1;
  /** 稳定数字 id：金箍棒一次挥击的命中去重用（见 Staff）。 */
  readonly id = Enemy.nextId++;

  hp: number;
  readonly maxHp: number;
  readonly contactDamage: number;
  readonly scoreValue: number;
  readonly lingyunValue: number;

  protected frozenUntil = 0;
  protected dead = false;
  protected knockbackResistant = false;

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    texture: string,
    opts: {
      maxHp: number;
      contactDamage: number;
      scoreValue: number;
      lingyunValue: number;
      width: number;
      height: number;
    },
  ) {
    super(scene, x, y, texture);
    scene.add.existing(this);
    scene.physics.add.existing(this);
    this.body.setSize(opts.width, opts.height);
    this.setCollideWorldBounds(true);
    this.setDepth(9);
    this.hp = opts.maxHp;
    this.maxHp = opts.maxHp;
    this.contactDamage = opts.contactDamage;
    this.scoreValue = opts.scoreValue;
    this.lingyunValue = opts.lingyunValue;
  }

  protected get gs(): GameScene {
    return this.scene as unknown as GameScene;
  }

  get isDead(): boolean {
    return this.dead;
  }

  isFrozen(now: number): boolean {
    return now <= this.frozenUntil;
  }

  /** 被定身法冻结。 */
  freeze(durationMs: number, now: number): void {
    if (this.dead) return;
    this.frozenUntil = now + durationMs;
    this.setVelocity(0, 0);
    this.setTint(COLORS.freeze);
  }

  /** 受到棍法伤害。 */
  takeDamage(dmg: number, fromX: number, heavy: boolean, now: number): void {
    if (this.dead) return;
    this.hp -= dmg;
    // 受击闪白
    this.setTintFill(0xffffff);
    this.scene.time.delayedCall(60, () => {
      if (this.dead) return;
      if (this.isFrozen(now)) this.setTint(COLORS.freeze);
      else this.clearTint();
    });
    if (heavy && !this.isFrozen(now) && !this.knockbackResistant) {
      this.gs.combat.knockback(this.body, fromX, 180, 90);
    }
    if (this.hp <= 0) this.die();
  }

  protected die(): void {
    this.dead = true;
    this.body.enable = false;
    this.gs.onEnemyKilled(this);
    // 死亡消散
    this.scene.tweens.add({
      targets: this,
      alpha: 0,
      angle: this.flipX ? -90 : 90,
      y: this.y + 6,
      duration: 260,
      onComplete: () => this.destroy(),
    });
  }

  /** 每帧 AI（GameScene 调用）；frozen 时跳过。 */
  tick(now: number, dt: number, playerX: number, playerY: number): void {
    if (this.dead) return;
    if (this.isFrozen(now)) {
      this.setVelocityX(0);
      return;
    }
    if (this.tintTopLeft === COLORS.freeze) this.clearTint();
    this.updateAI(now, dt, playerX, playerY);
  }

  protected abstract updateAI(
    now: number,
    dt: number,
    playerX: number,
    playerY: number,
  ): void;
}
