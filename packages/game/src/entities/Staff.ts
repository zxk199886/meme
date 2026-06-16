import Phaser from "phaser";
import { PLAYER } from "../config/constants";
import { TEX } from "../config/textures";

/**
 * 金箍棒攻击命中区。一个不可见的矩形物理体，仅在攻击 active 帧启用。
 * GameScene 注册 staff.hitbox 与敌人组的 overlap；每次挥击用 hitSet 去重，避免一次挥击多次结算。
 */
export class Staff {
  readonly hitbox: Phaser.GameObjects.Rectangle;
  private body: Phaser.Physics.Arcade.Body;
  private hitSet = new Set<number>();

  active = false;
  damage = 0;
  heavy = false;

  /** 可见的棍体（纯表现，攻击时短暂显示）。 */
  private visual: Phaser.GameObjects.Image;

  constructor(scene: Phaser.Scene) {
    this.hitbox = scene.add
      .rectangle(0, 0, PLAYER.attackReach, PLAYER.attackHeight, 0xff0000, 0)
      .setDepth(20);
    scene.physics.add.existing(this.hitbox);
    this.body = this.hitbox.body as Phaser.Physics.Arcade.Body;
    this.body.setAllowGravity(false);
    this.body.enable = false;

    this.visual = scene.add.image(0, 0, TEX.staff).setDepth(11).setVisible(false);
  }

  activate(damage: number, heavy: boolean, facing: number, x: number, y: number): void {
    this.damage = damage;
    this.heavy = heavy;
    this.active = true;
    this.hitSet.clear();
    this.body.enable = true;
    this.reposition(facing, x, y);
    this.visual.setVisible(true).setFlipX(facing < 0);
  }

  deactivate(): void {
    this.active = false;
    this.body.enable = false;
    this.visual.setVisible(false);
  }

  /** 跟随玩家朝向定位（攻击期间每帧调用）。 */
  reposition(facing: number, x: number, y: number): void {
    const offset = facing * (PLAYER.attackReach / 2 + 6);
    this.hitbox.setPosition(x + offset, y);
    this.body.reset(x + offset, y);
    this.visual.setPosition(x + offset, y).setFlipX(facing < 0);
  }

  /** 该目标本次挥击是否已结算过。 */
  alreadyHit(id: number): boolean {
    return this.hitSet.has(id);
  }
  markHit(id: number): void {
    this.hitSet.add(id);
  }
}
