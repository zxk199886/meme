/**
 * 击杀 / 灵蕴 / 分数累计。
 * 为 Phase 3 成绩提交准备字段（score/kills/durationMs，见 packages/game/src/web3/events.ts）。
 */
export class ScoreSystem {
  private _score = 0;
  private _kills = 0;
  private _lingyun = 0; // 灵蕴（经验，Phase 后续接技能树）
  private startedAt: number;

  constructor(now: number) {
    this.startedAt = now;
  }

  addKill(scoreValue: number, lingyunValue: number): void {
    this._kills += 1;
    this._score += scoreValue;
    this._lingyun += lingyunValue;
  }

  addScore(v: number): void {
    this._score += v;
  }

  get score(): number {
    return this._score;
  }
  get kills(): number {
    return this._kills;
  }
  get lingyun(): number {
    return this._lingyun;
  }

  durationMs(now: number): number {
    return Math.max(0, now - this.startedAt);
  }
}
