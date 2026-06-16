import Phaser from "phaser";
import { COLORS } from "./constants";

/** 纹理 key 常量（真实美术替换时只需保持这些 key 不变）。 */
export const TEX = {
  player: "tex_player",
  staff: "tex_staff",
  grunt: "tex_grunt",
  boss: "tex_boss",
  bossPhase2: "tex_boss_p2",
  platform: "tex_platform",
  ground: "tex_ground",
  shrine: "tex_shrine",
  freeze: "tex_freeze",
  spark: "tex_spark",
  pixel: "tex_pixel", // 1x1 白，用于条/粒子着色
  bgFar: "tex_bg_far",
} as const;

function rect(
  scene: Phaser.Scene,
  key: string,
  w: number,
  h: number,
  color: number,
  alpha = 1,
): void {
  const g = scene.add.graphics();
  g.fillStyle(color, alpha);
  g.fillRect(0, 0, w, h);
  g.generateTexture(key, w, h);
  g.destroy();
}

/**
 * 生成全部程序化占位纹理（在 BootScene 调用一次）。
 * 这些是简单色块，真实像素美术按 docs/05-art-style-spec.md 后续替换。
 */
export function generatePlaceholderTextures(scene: Phaser.Scene): void {
  rect(scene, TEX.pixel, 1, 1, 0xffffff);
  rect(scene, TEX.player, 18, 28, COLORS.player);
  rect(scene, TEX.staff, 26, 6, COLORS.staff);
  rect(scene, TEX.grunt, 18, 22, COLORS.grunt);
  rect(scene, TEX.boss, 40, 52, COLORS.boss);
  rect(scene, TEX.bossPhase2, 40, 52, COLORS.bossPhase2);
  rect(scene, TEX.platform, 16, 12, COLORS.platform);
  rect(scene, TEX.ground, 16, 22, COLORS.ground);
  rect(scene, TEX.spark, 6, 6, COLORS.hitSpark);
  rect(scene, TEX.bgFar, 64, 64, COLORS.bgFar);

  // 神龛：底座 + 顶部小塔轮廓（用两段拼色块意思一下）
  {
    const g = scene.add.graphics();
    g.fillStyle(COLORS.shrine, 1);
    g.fillRect(0, 10, 22, 16);
    g.fillRect(4, 0, 14, 12);
    g.generateTexture(TEX.shrine, 22, 26);
    g.destroy();
  }

  // 定身结晶：菱形
  {
    const g = scene.add.graphics();
    g.fillStyle(COLORS.freeze, 0.85);
    g.beginPath();
    g.moveTo(8, 0);
    g.lineTo(16, 9);
    g.lineTo(8, 18);
    g.lineTo(0, 9);
    g.closePath();
    g.fillPath();
    g.generateTexture(TEX.freeze, 16, 18);
    g.destroy();
  }
}
