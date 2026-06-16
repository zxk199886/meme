/**
 * 第一关布局数据（数据驱动，暂不用 Tiled 编辑器）。
 * GameScene 据此构建静态平台、生成实体。后续可平滑迁移到 Tiled JSON。
 * 坐标为世界像素坐标，原点左上。关卡比视口宽，相机横向跟随。
 */

export interface RectDef {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Level {
  worldWidth: number;
  worldHeight: number;
  /** 平台 / 地面（静态碰撞体），x/y 为左上角 */
  platforms: RectDef[];
  playerSpawn: { x: number; y: number };
  /** 小怪出生点 */
  grunts: { x: number; y: number; patrolMin: number; patrolMax: number }[];
  /** 神龛检查点（交互回血+复活点） */
  shrines: { x: number; y: number }[];
  /** 进入此区域触发 Boss 战 */
  bossTrigger: RectDef;
  boss: { x: number; y: number };
  /** Boss 战左右边界（Boss 房），玩家被锁在此区间 */
  bossArena: { min: number; max: number };
}

const GROUND_Y = 248;

export const LEVEL_1: Level = {
  worldWidth: 2400,
  worldHeight: 270,
  platforms: [
    // 连续地面（留一处小坑制造闪避/跳跃压力）
    { x: 0, y: GROUND_Y, width: 760, height: 22 },
    { x: 820, y: GROUND_Y, width: 1580, height: 22 },
    // 悬浮平台
    { x: 220, y: 200, width: 90, height: 12 },
    { x: 380, y: 160, width: 90, height: 12 },
    { x: 560, y: 195, width: 80, height: 12 },
    { x: 980, y: 190, width: 110, height: 12 },
    { x: 1180, y: 150, width: 90, height: 12 },
    { x: 1420, y: 195, width: 120, height: 12 },
    // Boss 房入口前的台阶
    { x: 1640, y: 205, width: 80, height: 12 },
  ],
  playerSpawn: { x: 60, y: 210 },
  grunts: [
    { x: 320, y: 226, patrolMin: 250, patrolMax: 470 },
    { x: 620, y: 226, patrolMin: 520, patrolMax: 740 },
    { x: 1020, y: 226, patrolMin: 900, patrolMax: 1140 },
    { x: 1340, y: 226, patrolMin: 1240, patrolMax: 1480 },
  ],
  shrines: [{ x: 700, y: 226 }, { x: 1560, y: 226 }],
  bossTrigger: { x: 1820, y: 120, width: 40, height: 130 },
  boss: { x: 2180, y: 200 },
  bossArena: { min: 1860, max: 2400 },
};
