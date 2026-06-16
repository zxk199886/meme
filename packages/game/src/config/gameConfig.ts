import Phaser from "phaser";
import { LOGICAL_WIDTH, LOGICAL_HEIGHT, PHYSICS, COLORS } from "./constants";
import { BootScene } from "../scenes/BootScene";
import { PreloadScene } from "../scenes/PreloadScene";
import { MainMenuScene } from "../scenes/MainMenuScene";
import { GameScene } from "../scenes/GameScene";
import { UIScene } from "../scenes/UIScene";
import { GameOverScene } from "../scenes/GameOverScene";

export const gameConfig: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  parent: "game-root",
  backgroundColor: COLORS.bg,
  pixelArt: true, // 关闭抗锯齿，保持像素锐利
  roundPixels: true,
  scale: {
    mode: Phaser.Scale.FIT, // 整体等比缩放到窗口
    autoCenter: Phaser.Scale.CENTER_BOTH,
    width: LOGICAL_WIDTH,
    height: LOGICAL_HEIGHT,
  },
  physics: {
    default: "arcade",
    arcade: {
      gravity: { x: 0, y: PHYSICS.gravityY },
      debug: false,
    },
  },
  // 场景注册顺序即默认启动顺序（Boot 自动 start 下一个）
  scene: [
    BootScene,
    PreloadScene,
    MainMenuScene,
    GameScene,
    UIScene,
    GameOverScene,
  ],
};
