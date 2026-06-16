import Phaser from "phaser";
import { PLAYER } from "../config/constants";

/**
 * 键位映射 + jump buffer / coyote 辅助。
 * 键位见 docs/01-game-design-doc.md。预留触屏映射接口（setVirtual*）。
 */
export class InputManager {
  private keys: Record<string, Phaser.Input.Keyboard.Key>;
  private lastJumpPressAt = -99999;

  // 触屏/外部虚拟输入覆盖（Phase 后续接入）
  private virtualLeft = false;
  private virtualRight = false;

  constructor(scene: Phaser.Scene) {
    const kb = scene.input.keyboard!;
    this.keys = {
      left: kb.addKey(Phaser.Input.Keyboard.KeyCodes.LEFT),
      right: kb.addKey(Phaser.Input.Keyboard.KeyCodes.RIGHT),
      a: kb.addKey(Phaser.Input.Keyboard.KeyCodes.A),
      d: kb.addKey(Phaser.Input.Keyboard.KeyCodes.D),
      up: kb.addKey(Phaser.Input.Keyboard.KeyCodes.UP),
      w: kb.addKey(Phaser.Input.Keyboard.KeyCodes.W),
      space: kb.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE),
      light: kb.addKey(Phaser.Input.Keyboard.KeyCodes.J),
      heavy: kb.addKey(Phaser.Input.Keyboard.KeyCodes.K),
      dodge: kb.addKey(Phaser.Input.Keyboard.KeyCodes.SHIFT),
      immobilize: kb.addKey(Phaser.Input.Keyboard.KeyCodes.U),
      interact: kb.addKey(Phaser.Input.Keyboard.KeyCodes.E),
    };
  }

  /** 每帧调用：记录跳跃按下时间用于 jump buffer。 */
  update(now: number): void {
    if (
      Phaser.Input.Keyboard.JustDown(this.keys.space) ||
      Phaser.Input.Keyboard.JustDown(this.keys.up) ||
      Phaser.Input.Keyboard.JustDown(this.keys.w)
    ) {
      this.lastJumpPressAt = now;
    }
  }

  /** -1 左 / 0 / 1 右 */
  horizontal(): number {
    const left = this.keys.left.isDown || this.keys.a.isDown || this.virtualLeft;
    const right = this.keys.right.isDown || this.keys.d.isDown || this.virtualRight;
    return (right ? 1 : 0) - (left ? 1 : 0);
  }

  /** jump buffer：最近 jumpBufferMs 内按过跳，且消费掉。 */
  consumeBufferedJump(now: number): boolean {
    if (now - this.lastJumpPressAt <= PLAYER.jumpBufferMs) {
      this.lastJumpPressAt = -99999;
      return true;
    }
    return false;
  }

  justLight(): boolean {
    return Phaser.Input.Keyboard.JustDown(this.keys.light);
  }
  justHeavy(): boolean {
    return Phaser.Input.Keyboard.JustDown(this.keys.heavy);
  }
  justDodge(): boolean {
    return Phaser.Input.Keyboard.JustDown(this.keys.dodge);
  }
  justImmobilize(): boolean {
    return Phaser.Input.Keyboard.JustDown(this.keys.immobilize);
  }
  justInteract(): boolean {
    return Phaser.Input.Keyboard.JustDown(this.keys.interact);
  }

  // 触屏接口预留
  setVirtualLeft(v: boolean): void {
    this.virtualLeft = v;
  }
  setVirtualRight(v: boolean): void {
    this.virtualRight = v;
  }
}
