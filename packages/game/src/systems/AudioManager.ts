import Phaser from "phaser";

type SfxName =
  | "swing"
  | "hit"
  | "heavyHit"
  | "dodge"
  | "freeze"
  | "hurt"
  | "shrine"
  | "bossRoar"
  | "victory"
  | "death";

/**
 * 音频封装（占位）。
 * Phase 2 暂无音频资源；此处提供统一接口，真实 SFX/BGM 按 docs/05 接入后只需在
 * loadSounds() 注册、play() 即可发声。当前 play() 为 no-op（避免缺资源报错）。
 */
export class AudioManager {
  private scene: Phaser.Scene;
  private muted = false;
  private loaded = false;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
  }

  /** 真实音频接入后在此 this.scene.sound.add(...)；MVP 占位。 */
  loadSounds(): void {
    this.loaded = true;
  }

  play(_name: SfxName, _volume = 1): void {
    if (this.muted || !this.loaded) return;
    // 占位：真实资源接入后替换为 this.scene.sound.play(_name, { volume: _volume })
  }

  setMuted(v: boolean): void {
    this.muted = v;
    this.scene.sound.mute = v;
  }
}
