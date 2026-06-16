import Phaser from "phaser";
import { GRUNT } from "../../config/constants";
import { TEX } from "../../config/textures";
import { Enemy } from "./Enemy";

/**
 * 狼妖：地面巡逻 → 玩家进入视野则追击。接触伤害由 GameScene overlap 结算。
 */
export class GruntEnemy extends Enemy {
  private patrolMin: number;
  private patrolMax: number;
  private dir: 1 | -1 = 1;

  constructor(
    scene: Phaser.Scene,
    x: number,
    y: number,
    patrolMin: number,
    patrolMax: number,
  ) {
    super(scene, x, y, TEX.grunt, {
      maxHp: GRUNT.maxHp,
      contactDamage: GRUNT.contactDamage,
      scoreValue: GRUNT.scoreValue,
      lingyunValue: GRUNT.lingyunValue,
      width: GRUNT.width,
      height: GRUNT.height,
    });
    this.patrolMin = patrolMin;
    this.patrolMax = patrolMax;
  }

  protected updateAI(_now: number, _dt: number, playerX: number, playerY: number): void {
    const dist = Math.abs(playerX - this.x);
    const sameLevel = Math.abs(playerY - this.y) < 60;

    if (dist <= GRUNT.visionRange && sameLevel) {
      // 追击
      this.dir = playerX < this.x ? -1 : 1;
      this.setVelocityX(this.dir * GRUNT.chaseSpeed);
    } else {
      // 巡逻：到边界折返
      if (this.x <= this.patrolMin) this.dir = 1;
      else if (this.x >= this.patrolMax) this.dir = -1;
      this.setVelocityX(this.dir * GRUNT.patrolSpeed);
    }
    this.setFlipX(this.dir < 0);
  }
}
