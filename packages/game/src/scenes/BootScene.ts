import Phaser from "phaser";
import { generatePlaceholderTextures } from "../config/textures";

/** 生成程序化占位纹理，然后进入 Preload。 */
export class BootScene extends Phaser.Scene {
  constructor() {
    super("Boot");
  }

  create(): void {
    generatePlaceholderTextures(this);
    this.scene.start("Preload");
  }
}
