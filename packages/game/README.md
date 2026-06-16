# @monkey-saga/game

Phaser 3 + TypeScript 游戏本体（主交付物）。Phase 2 起填充实际玩法代码。

## 计划目录
```
src/
  main.ts            Phaser 启动 + 配置（入口）
  config/            gameConfig.ts（物理/缩放/渲染）、constants.ts（速度/重力/伤害等可调）
  scenes/            Boot / Preload / MainMenu / Game / UI / GameOver
  entities/          Player.ts、Staff.ts、enemies/（Enemy/Grunt/Boss）
  systems/           Combat / Score / Input / Audio
  ui/                HealthBar、ScoreLabel
  web3/              Web3Bridge.ts（与 React/钱包的事件总线）、events.ts
  types/             类型声明
```

## 运行（Phase 2 起）
```bash
pnpm --filter @monkey-saga/game dev
```

详见 `docs/01-game-design-doc.md` 与 `docs/02-tech-architecture.md`。
