/**
 * 种子化随机数（确定性留口）。
 * MVP 用它做敌人巡逻抖动/招式选择，未来支撑重放反作弊（docs/07）。
 * mulberry32：小巧、确定、足够游戏用。
 */
export class Rng {
  private state: number;

  constructor(seed = 0x9e3779b9) {
    this.state = seed >>> 0;
  }

  /** [0,1) */
  next(): number {
    this.state |= 0;
    this.state = (this.state + 0x6d2b79f5) | 0;
    let t = Math.imul(this.state ^ (this.state >>> 15), 1 | this.state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  /** [min,max) */
  between(min: number, max: number): number {
    return min + this.next() * (max - min);
  }

  /** [min,max] 整数 */
  intBetween(min: number, max: number): number {
    return Math.floor(this.between(min, max + 1));
  }

  pick<T>(arr: readonly T[]): T {
    return arr[this.intBetween(0, arr.length - 1)];
  }
}
