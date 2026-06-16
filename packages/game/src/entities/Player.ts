import Phaser from "phaser";
import { PLAYER, IMMOBILIZE, COLORS } from "../config/constants";
import { TEX } from "../config/textures";
import type { InputManager } from "../systems/InputManager";
import { Staff } from "./Staff";
import type { GameScene } from "../scenes/GameScene";

type PlayerState = "normal" | "attacking" | "dodging" | "casting" | "hurt" | "dead";

export class Player extends Phaser.Physics.Arcade.Sprite {
  declare body: Phaser.Physics.Arcade.Body;

  hp = PLAYER.maxHp;
  stamina = PLAYER.maxStamina;
  mana = PLAYER.maxMana;
  focus = 0;

  facing: 1 | -1 = 1;
  state: PlayerState = "normal";
  readonly staff: Staff;

  private busyUntil = 0; // 锁定状态（attack/cast/hurt）结束时间
  private dodgeUntil = 0;
  private iFrameUntil = 0;
  private coyoteUntil = 0;
  private perfectWindowUntil = 0; // 完美闪避减速窗口
  private lightComboStep = 0;
  private lastLightAt = -99999;
  private respawnPoint: { x: number; y: number };

  constructor(scene: Phaser.Scene, x: number, y: number) {
    super(scene, x, y, TEX.player);
    scene.add.existing(this);
    scene.physics.add.existing(this);
    this.setCollideWorldBounds(true);
    this.body.setSize(PLAYER.width, PLAYER.height);
    this.setDepth(10);
    this.staff = new Staff(scene);
    this.respawnPoint = { x, y };
  }

  private get gs(): GameScene {
    return this.scene as unknown as GameScene;
  }

  /** 主更新（GameScene 每帧调用）。 */
  tick(now: number, dt: number, input: InputManager): void {
    if (this.state === "dead") return;

    const onGround = this.body.blocked.down || this.body.touching.down;
    if (onGround) this.coyoteUntil = now + PLAYER.coyoteMs;

    // 资源回复
    this.stamina = Math.min(
      PLAYER.maxStamina,
      this.stamina + (PLAYER.staminaRegenPerSec * dt) / 1000,
    );
    this.mana = Math.min(PLAYER.maxMana, this.mana + (PLAYER.manaRegenPerSec * dt) / 1000);

    // 锁定状态到期 → 回 normal
    if (
      (this.state === "attacking" || this.state === "casting" || this.state === "hurt") &&
      now >= this.busyUntil
    ) {
      this.setState("normal");
      this.clearTint();
    }
    if (this.state === "dodging" && now >= this.dodgeUntil) {
      this.setState("normal");
      this.clearTint();
    }

    // 攻击期间棍体跟随
    if (this.staff.active) this.staff.reposition(this.facing, this.x, this.y);

    const canAct = this.state === "normal" || this.state === "attacking";

    // 朝向 + 水平移动（直接控速，手感紧致）
    if (this.state === "normal") {
      const h = input.horizontal();
      if (h !== 0) this.facing = h > 0 ? 1 : -1;
      this.setVelocityX(h * PLAYER.moveSpeed);
    } else if (
      this.state === "attacking" ||
      this.state === "casting" ||
      this.state === "hurt"
    ) {
      // 出招/受击：水平快速衰减（不覆盖闪避冲刺）
      this.setVelocityX(this.body.velocity.x * 0.8);
    }
    // dodging 状态保持 startDodge 设定的冲刺速度，不在此覆盖

    this.setFlipX(this.facing < 0);

    // 跳跃（jump buffer + coyote）
    if (
      this.state === "normal" &&
      now <= this.coyoteUntil &&
      input.consumeBufferedJump(now)
    ) {
      this.setVelocityY(PLAYER.jumpVelocity);
      this.coyoteUntil = 0;
    }

    // 动作输入
    if (canAct && input.justLight()) this.startLight(now);
    if (this.state === "normal" && input.justHeavy()) this.startHeavy(now);
    if (this.state === "normal" && input.justDodge()) this.startDodge(now, input);
    if (this.state === "normal" && input.justImmobilize()) this.castImmobilize(now);
  }

  // --- 攻击 ---
  private startLight(now: number): void {
    // 连段：在窗口内递增 step（MVP 仅用于轻微变化）
    this.lightComboStep =
      now - this.lastLightAt <= PLAYER.lightComboWindowMs
        ? (this.lightComboStep + 1) % 3
        : 0;
    this.lastLightAt = now;

    this.setState("attacking");
    this.busyUntil =
      now + PLAYER.lightWindupMs + PLAYER.lightActiveMs + PLAYER.lightRecoverMs;

    this.scene.time.delayedCall(PLAYER.lightWindupMs, () => {
      if (this.state === "dead") return;
      this.staff.activate(PLAYER.lightDamage, false, this.facing, this.x, this.y);
    });
    this.scene.time.delayedCall(PLAYER.lightWindupMs + PLAYER.lightActiveMs, () =>
      this.staff.deactivate(),
    );
  }

  private startHeavy(now: number): void {
    if (this.stamina < PLAYER.heavyStaminaCost) return;
    this.stamina -= PLAYER.heavyStaminaCost;
    this.setState("attacking");
    this.setTint(0xffd27f);
    this.busyUntil =
      now + PLAYER.heavyWindupMs + PLAYER.heavyActiveMs + PLAYER.heavyRecoverMs;

    this.scene.time.delayedCall(PLAYER.heavyWindupMs, () => {
      if (this.state === "dead") return;
      this.staff.activate(PLAYER.heavyDamage, true, this.facing, this.x, this.y);
    });
    this.scene.time.delayedCall(PLAYER.heavyWindupMs + PLAYER.heavyActiveMs, () =>
      this.staff.deactivate(),
    );
  }

  // --- 闪避 ---
  private startDodge(now: number, input: InputManager): void {
    if (this.stamina < PLAYER.dodgeStaminaCost) return;
    this.stamina -= PLAYER.dodgeStaminaCost;
    const h = input.horizontal();
    const dir = h !== 0 ? Math.sign(h) : this.facing;
    this.setState("dodging");
    this.dodgeUntil = now + PLAYER.dodgeDurationMs;
    this.iFrameUntil = now + PLAYER.dodgeIFrameMs;
    this.perfectWindowUntil = now + PLAYER.perfectDodgeWindowMs;
    this.setVelocityX(dir * PLAYER.dodgeSpeed);
    this.setAlpha(0.6);
    this.setTint(0x9fd6ff);
    this.scene.time.delayedCall(PLAYER.dodgeDurationMs, () => {
      this.setAlpha(1);
      if (this.state !== "dead") this.clearTint();
    });
  }

  // --- 定身法 ---
  private castImmobilize(now: number): void {
    if (this.mana < PLAYER.immobilizeManaCost) return;
    this.mana -= PLAYER.immobilizeManaCost;
    this.setState("casting");
    this.busyUntil = now + 260;
    this.setVelocityX(0);
    this.setTint(0x7fd6ff);
    this.gs.immobilizeEnemies(this.x, this.y, IMMOBILIZE.radius);
    // 施法光环
    const ring = this.scene.add
      .circle(this.x, this.y, 10, COLORS.freeze, 0.25)
      .setDepth(5);
    this.scene.tweens.add({
      targets: ring,
      radius: IMMOBILIZE.radius,
      alpha: 0,
      duration: 300,
      onComplete: () => ring.destroy(),
    });
  }

  /** 命中敌人后由 GameScene 调用：积攒专注 + 回法力。 */
  onDealtHit(): void {
    this.focus = Math.min(PLAYER.maxFocus, this.focus + PLAYER.focusPerHit);
    this.mana = Math.min(PLAYER.maxMana, this.mana + PLAYER.manaOnHit);
  }

  isInvulnerable(now: number): boolean {
    return now <= this.iFrameUntil;
  }

  /** 受击。返回是否真的受伤（用于完美闪避判定提示）。 */
  takeDamage(dmg: number, fromX: number, now: number): boolean {
    if (this.state === "dead") return false;
    // 完美闪避：在窗口内被攻击 → 免伤 + 触发减速奖励窗口
    if (now <= this.perfectWindowUntil) {
      this.gs.triggerPerfectDodge();
      return false;
    }
    if (this.isInvulnerable(now)) return false;

    this.hp = Math.max(0, this.hp - dmg);
    this.iFrameUntil = now + PLAYER.hurtIFrameMs;
    this.gs.combat.knockback(this.body, fromX, 140, 120);

    if (this.hp <= 0) {
      this.die();
      return true;
    }
    this.setState("hurt");
    this.busyUntil = now + 220;
    this.setTint(0xff5a5a);
    this.scene.time.delayedCall(PLAYER.hurtIFrameMs, () => {
      if (this.state !== "dead") this.clearTint();
    });
    // 受击闪烁
    this.scene.tweens.add({
      targets: this,
      alpha: 0.3,
      duration: 80,
      yoyo: true,
      repeat: 3,
      onComplete: () => this.setAlpha(1),
    });
    return true;
  }

  private die(): void {
    this.setState("dead");
    this.staff.deactivate();
    this.setVelocity(0, -120);
    this.setTint(0x884444);
    this.setAngle(90);
  }

  /** 神龛回血并设为复活点。 */
  restAtShrine(x: number, y: number): void {
    this.hp = PLAYER.maxHp;
    this.mana = PLAYER.maxMana;
    this.stamina = PLAYER.maxStamina;
    this.respawnPoint = { x, y };
  }

  /** 跌落深坑后传回复活点并扣少量血。 */
  respawnFromPit(now: number): void {
    if (this.state === "dead") return;
    this.setPosition(this.respawnPoint.x, this.respawnPoint.y);
    this.setVelocity(0, 0);
    this.hp = Math.max(0, this.hp - 10);
    this.iFrameUntil = now + PLAYER.hurtIFrameMs;
    if (this.hp <= 0) this.die();
  }

  get hpRatio(): number {
    return this.hp / PLAYER.maxHp;
  }
  get staminaRatio(): number {
    return this.stamina / PLAYER.maxStamina;
  }
  get manaRatio(): number {
    return this.mana / PLAYER.maxMana;
  }
  get focusRatio(): number {
    return this.focus / PLAYER.maxFocus;
  }
  get isDead(): boolean {
    return this.state === "dead";
  }
}
