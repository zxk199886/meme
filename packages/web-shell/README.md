# @monkey-saga/web-shell

React 岛：页面框架 + Solana 钱包 UI + 排行榜 / NFT 铸造面板，并挂载 Phaser canvas。
Phase 3 起填充实现。

## 计划目录
```
src/
  App.tsx
  WalletProvider.tsx      ConnectionProvider + WalletProvider + WalletModalProvider
  components/             WalletButton、Leaderboard、MintPanel
  hooks/                  useRewardClaim、useLeaderboard
  bridge/phaserBridge.ts  实例化 Phaser.Game 并接通 Web3Bridge 事件
```

> MVP 可与 `@monkey-saga/game` 合并为单个 Vite 应用（React 渲染页面、挂载 Phaser canvas）。
> 详见 `docs/adr/0002-react-island-wallet.md`。
