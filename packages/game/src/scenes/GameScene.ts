import Phaser from "phaser";
import { COLORS, IMMOBILIZE, SCORE } from "../config/constants";
import { TEX } from "../config/textures";
import { LEVEL_1, type Level } from "../config/level1";
import { Player } from "../entities/Player";
import { Enemy } from "../entities/enemies/Enemy";
import { GruntEnemy } from "../entities/enemies/GruntEnemy";
import { Boss } from "../entities/enemies/Boss";
import { CombatSystem } from "../systems/CombatSystem";
import { ScoreSystem } from "../systems/ScoreSystem";
import { InputManager } from "../systems/InputManager";
import { AudioManager } from "../systems/AudioManager";
import { Rng } from "../systems/Rng";
import type { GameOverData } from "./GameOverScene";

/** HUD 快照（UIScene 每帧读取）。 */
export interface HudState {
  hp: number;
  stamina: number;
  mana: number;
  focus: number;
  score: number;
  lingyun: number;
  bossActive: boolean;
  bossRatio: number;
  bossPhase: 1 | 2;
}

export class GameScene extends Phaser.Scene {
  // 系统（供实体访问）
  combat!: CombatSystem;
  rng!: Rng;
  private score!: ScoreSystem;
  private controls!: InputManager;
  private audio!: AudioManager;

  private level: Level = LEVEL_1;
  private player!: Player;
  private enemies!: Phaser.Physics.Arcade.Group;
  private solids: Phaser.GameObjects.Rectangle[] = [];

  private boss?: Boss;
  private bossActive = false;
  private bossTriggered = false;
  private ended = false;
  private shrines: { x: number; y: number }[] = [];

  constructor() {
    super("Game");
  }

  create(): void {
    this.ended = false;
    this.bossActive = false;
    this.bossTriggered = false;
    this.boss = undefined;
    this.solids = [];

    this.rng = new Rng(0x1234abcd);
    this.combat = new CombatSystem(this);
    this.score = new ScoreSystem(this.time.now);
    this.controls = new InputManager(this);
    this.audio = new AudioManager(this);
    this.audio.loadSounds();

    this.buildBackground();
    this.buildLevel();

    // 玩家
    this.player = new Player(this, this.level.playerSpawn.x, this.level.playerSpawn.y);
    this.physics.add.collider(this.player, this.solids);

    // 敌人组
    this.enemies = this.physics.add.group({ runChildUpdate: false });
    this.physics.add.collider(this.enemies, this.solids);
    for (const g of this.level.grunts) {
      this.addEnemy(new GruntEnemy(this, g.x, g.y, g.patrolMin, g.patrolMax));
    }

    // Boss（休眠，进入触发区才激活）
    this.boss = new Boss(this, this.level.boss.x, this.level.boss.y);
    this.addEnemy(this.boss);

    // 碰撞 / 重叠
    this.physics.add.overlap(this.player.staff.hitbox, this.enemies, (_hb, e) =>
      this.onStaffHit(e as unknown as Enemy),
    );
    this.physics.add.overlap(this.player, this.enemies, (_p, e) =>
      this.onPlayerTouchEnemy(e as unknown as Enemy),
    );

    // 世界 / 相机
    this.physics.world.setBounds(0, -60, this.level.worldWidth, this.level.worldHeight + 260);
    this.cameras.main.setBounds(0, 0, this.level.worldWidth, this.level.worldHeight);
    this.cameras.main.startFollow(this.player, true, 0.12, 0.12);
    this.cameras.main.setBackgroundColor(COLORS.bg);

    // 神龛
    this.shrines = this.level.shrines.map((s) => ({ x: s.x, y: s.y }));

    // 并行 HUD 场景
    this.scene.launch("UI");
  }

  private buildBackground(): void {
    // 远景视差色块
    for (let x = 0; x < this.level.worldWidth; x += 64) {
      this.add
        .image(x, 120, TEX.bgFar)
        .setOrigin(0, 0.5)
        .setAlpha(0.25)
        .setScrollFactor(0.3)
        .setDepth(-10);
    }
  }

  private buildLevel(): void {
    for (const p of this.level.platforms) {
      const isGround = p.height >= 20;
      const rect = this.add
        .rectangle(
          p.x + p.width / 2,
          p.y + p.height / 2,
          p.width,
          p.height,
          isGround ? COLORS.ground : COLORS.platform,
        )
        .setDepth(1);
      this.physics.add.existing(rect, true);
      this.solids.push(rect);
    }
    // 神龛贴图
    for (const s of this.level.shrines) {
      this.add.image(s.x, s.y - 4, TEX.shrine).setOrigin(0.5, 1).setDepth(2);
    }
  }

  private addEnemy(e: Enemy): void {
    this.enemies.add(e);
  }

  // --- 实体回调 / 供实体调用的 API ---

  private onStaffHit(enemy: Enemy): void {
    const staff = this.player.staff;
    if (!staff.active || enemy.isDead || staff.alreadyHit(enemy.id)) return;
    staff.markHit(enemy.id);
    enemy.takeDamage(staff.damage, this.player.x, staff.heavy, this.time.now);
    this.combat.impact(enemy.x, enemy.y, staff.heavy);
    this.player.onDealtHit();
    this.audio.play(staff.heavy ? "heavyHit" : "hit");
  }

  private onPlayerTouchEnemy(enemy: Enemy): void {
    const now = this.time.now;
    if (enemy.isDead || enemy.isFrozen(now) || this.player.isDead) return;
    if (this.player.takeDamage(enemy.contactDamage, enemy.x, now)) {
      this.audio.play("hurt");
    }
  }

  /** Boss/AOE 范围伤害：玩家在范围内则受伤。 */
  damagePlayerInArea(x: number, y: number, radius: number, dmg: number): void {
    const now = this.time.now;
    if (this.player.isDead) return;
    if (Phaser.Math.Distance.Between(x, y, this.player.x, this.player.y) <= radius) {
      this.player.takeDamage(dmg, x, now);
    }
  }

  /** 定身法：冻结范围内所有敌人。 */
  immobilizeEnemies(x: number, y: number, radius: number): void {
    const now = this.time.now;
    this.audio.play("freeze");
    for (const child of this.enemies.getChildren()) {
      const e = child as Enemy;
      if (e.isDead) continue;
      if (Phaser.Math.Distance.Between(x, y, e.x, e.y) <= radius) {
        e.freeze(IMMOBILIZE.durationMs, now);
        const crystal = this.add
          .image(e.x, e.y - 12, TEX.freeze)
          .setDepth(15)
          .setAlpha(0.9);
        this.time.delayedCall(IMMOBILIZE.durationMs, () => crystal.destroy());
      }
    }
  }

  spawnGrunt(x: number, y: number): void {
    this.addEnemy(new GruntEnemy(this, x, y, x - 60, x + 60));
  }

  gruntCount(): number {
    return this.enemies.getChildren().filter((c) => c instanceof GruntEnemy && !(c as Enemy).isDead).length;
  }

  onEnemyKilled(enemy: Enemy): void {
    this.score.addKill(enemy.scoreValue, enemy.lingyunValue);
    if (enemy === this.boss) {
      this.win();
    }
  }

  onBossPhase2(): void {
    this.cameras.main.flash(200, 120, 40, 160);
    this.audio.play("bossRoar");
  }

  /** 完美闪避：短暂全局减速奖励。 */
  triggerPerfectDodge(): void {
    this.cameras.main.flash(120, 160, 220, 255);
    this.time.timeScale = 0.4;
    this.physics.world.timeScale = 2.5; // world.timeScale 是除数，>1 = 变慢
    window.setTimeout(() => {
      this.time.timeScale = 1;
      this.physics.world.timeScale = 1;
    }, 260);
  }

  // --- 主循环 ---

  update(time: number, delta: number): void {
    if (this.ended) return;

    this.controls.update(time);
    this.player.tick(time, delta, this.controls);

    const px = this.player.x;
    const py = this.player.y;

    for (const child of this.enemies.getChildren()) {
      const e = child as Enemy;
      if (e === this.boss && !this.bossActive) continue;
      e.tick(time, delta, px, py);
    }

    this.handleBossTrigger(px);
    this.handleShrines();
    this.handlePit(time);

    // Boss 战时把玩家锁在擂台内
    if (this.bossActive) {
      const { min, max } = this.level.bossArena;
      this.player.x = Phaser.Math.Clamp(this.player.x, min + 10, max - 10);
    }

    if (this.player.isDead && !this.ended) {
      this.lose();
    }
  }

  private handleBossTrigger(px: number): void {
    if (this.bossTriggered || !this.boss) return;
    const t = this.level.bossTrigger;
    if (px >= t.x && px <= t.x + t.width + 20) {
      this.bossTriggered = true;
      this.bossActive = true;
      // 锁定相机到擂台范围
      this.cameras.main.setBounds(
        this.level.bossArena.min,
        0,
        this.level.bossArena.max - this.level.bossArena.min,
        this.level.worldHeight,
      );
      this.onBossPhase2Banner();
      this.audio.play("bossRoar");
    }
  }

  private onBossPhase2Banner(): void {
    const cam = this.cameras.main;
    const txt = this.add
      .text(cam.width / 2, 60, "白 衣 判 官", {
        fontFamily: "monospace",
        fontSize: "22px",
        color: "#e8e4f0",
        stroke: "#cf5fd0",
        strokeThickness: 3,
      })
      .setOrigin(0.5)
      .setScrollFactor(0)
      .setDepth(200);
    this.tweens.add({
      targets: txt,
      alpha: 0,
      delay: 1200,
      duration: 600,
      onComplete: () => txt.destroy(),
    });
  }

  private handleShrines(): void {
    if (!this.controls.justInteract()) return;
    for (const s of this.shrines) {
      if (Phaser.Math.Distance.Between(s.x, s.y, this.player.x, this.player.y) <= 28) {
        this.player.restAtShrine(s.x, s.y);
        this.audio.play("shrine");
        const glow = this.add
          .circle(s.x, s.y - 10, 6, COLORS.shrine, 0.5)
          .setDepth(8);
        this.tweens.add({
          targets: glow,
          radius: 30,
          alpha: 0,
          duration: 500,
          onComplete: () => glow.destroy(),
        });
        break;
      }
    }
  }

  private handlePit(now: number): void {
    if (this.player.y > this.level.worldHeight + 60) {
      this.player.respawnFromPit(now);
    }
  }

  /** UIScene 每帧读取的 HUD 快照。 */
  hudState(): HudState {
    return {
      hp: this.player.hpRatio,
      stamina: this.player.staminaRatio,
      mana: this.player.manaRatio,
      focus: this.player.focusRatio,
      score: this.score.score,
      lingyun: this.score.lingyun,
      bossActive: this.bossActive,
      bossRatio: this.boss && !this.boss.isDead ? this.boss.hpRatio : 0,
      bossPhase: this.boss ? this.boss.phaseNumber : 1,
    };
  }

  private win(): void {
    if (this.ended) return;
    this.ended = true;
    this.score.addScore(SCORE.clearBonus);
    this.audio.play("victory");
    this.time.delayedCall(900, () => this.finish(true));
  }

  private lose(): void {
    if (this.ended) return;
    this.ended = true;
    this.audio.play("death");
    this.time.delayedCall(1100, () => this.finish(false));
  }

  private finish(victory: boolean): void {
    const data: GameOverData = {
      victory,
      score: this.score.score,
      kills: this.score.kills,
      durationMs: this.score.durationMs(this.time.now),
    };
    this.scene.stop("UI");
    this.scene.start("GameOver", data);
  }
}
