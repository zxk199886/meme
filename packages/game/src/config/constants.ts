/**
 * 全部可调数值集中于此（便于平衡 + 为确定性重放铺路）。
 * 详见 docs/01-game-design-doc.md。
 */

export const LOGICAL_WIDTH = 480;
export const LOGICAL_HEIGHT = 270;

export const COLORS = {
  player: 0xffcf6b, // 猴王：暖金
  staff: 0xd94f2a, // 金箍棒：朱红
  grunt: 0x6b8f4f, // 狼妖：青绿
  boss: 0xe8e4f0, // 白衣判官：白
  bossPhase2: 0xcf5fd0, // 二阶段紫
  platform: 0x4a3b2a, // 平台：土黄褐
  ground: 0x2e2418,
  shrine: 0xf0c84a, // 神龛：金
  freeze: 0x7fd6ff, // 定身结晶：冰蓝
  hitSpark: 0xfff2a0,
  bg: 0x141026,
  bgFar: 0x241b3a,
} as const;

export const PHYSICS = {
  gravityY: 900,
};

export const PLAYER = {
  width: 18,
  height: 28,
  maxHp: 100,
  // 移动
  moveSpeed: 160,
  accel: 1400,
  drag: 1200,
  // 跳跃
  jumpVelocity: -360,
  coyoteMs: 90, // 离开平台后仍可跳的宽限
  jumpBufferMs: 110, // 落地前提前按跳的缓冲
  // 资源
  maxStamina: 100,
  staminaRegenPerSec: 35,
  dodgeStaminaCost: 25,
  heavyStaminaCost: 20,
  maxMana: 100,
  manaRegenPerSec: 12,
  manaOnHit: 6,
  immobilizeManaCost: 40,
  maxFocus: 100,
  focusPerHit: 12,
  // 攻击
  lightDamage: 8,
  heavyDamage: 20,
  lightWindupMs: 60,
  lightActiveMs: 90,
  lightRecoverMs: 120,
  lightComboWindowMs: 360, // 连段衔接窗口
  heavyWindupMs: 180,
  heavyActiveMs: 110,
  heavyRecoverMs: 260,
  attackReach: 26, // 金箍棒命中区水平延伸
  attackHeight: 24,
  heavyKnockback: 220,
  // 闪避
  dodgeSpeed: 320,
  dodgeDurationMs: 240,
  dodgeIFrameMs: 220, // 翻滚无敌帧
  perfectDodgeWindowMs: 120, // 完美闪避判定窗口
  perfectDodgeSlowMs: 700, // 完美闪避后的减速窗口时长
  // 受击
  hurtIFrameMs: 600,
  contactDamage: 10, // 玩家碰到敌人受到的接触伤害（默认，敌人可覆盖）
};

export const IMMOBILIZE = {
  durationMs: 2500, // 定身冻结时长
  radius: 120, // 影响半径
};

export const GRUNT = {
  width: 18,
  height: 22,
  maxHp: 24,
  patrolSpeed: 40,
  chaseSpeed: 95,
  visionRange: 150, // 进入视野则追击
  attackRange: 22,
  contactDamage: 12,
  scoreValue: 100,
  lingyunValue: 10,
};

export const BOSS = {
  width: 40,
  height: 52,
  maxHp: 320,
  phase2HpRatio: 0.5, // 血量过半进二阶段
  walkSpeed: 60,
  chaseSpeed: 110,
  sweepDamage: 18,
  slamDamage: 24,
  aoeDamage: 16,
  contactDamage: 14,
  // 招式节奏（二阶段整体乘以 phase2SpeedMul 加速）
  actionCooldownMs: 1600,
  phase2SpeedMul: 0.62,
  summonCount: 2,
  scoreValue: 2000,
  lingyunValue: 200,
};

export const FEEDBACK = {
  hitStopMs: 70, // 命中顿帧
  heavyHitStopMs: 110,
  shakeDurationMs: 120,
  shakeIntensity: 0.006,
  heavyShakeIntensity: 0.012,
};

export const SCORE = {
  clearBonus: 5000, // 通关一次性加分
};
