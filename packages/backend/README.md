# @monkey-saga/backend

授权签名方 + API（Phase 3 起）。**反作弊核心**：mint/leaderboard authority 私钥
**只存在于此**，客户端永不铸币、永不写未校验分数上链。详见 `docs/07-security-anticheat.md`。

## 计划目录
```
src/
  server.ts
  routes/      score.ts（校验+签名）、reward.ts（发币）、leaderboard.ts、nonce.ts
  services/    authoritySigner.ts（私钥托管）、scoreValidator.ts（反作弊）、solanaClient.ts
  db/          排行榜缓存、会话 nonce、重放日志
  config.ts
```

## API（草案）
- `GET /session-nonce` — 发放绑定钱包、限时、一次性 nonce
- `POST /score` — 校验成绩（边界/nonce/重放/限流）→ 通过则 authority 上分
- `POST /claim` — 幂等领取代币（每 nonce 一次）→ authority 铸/转
- `GET /leaderboard` — 读取（链上或缓存）

> 私钥用 KMS，绝不进客户端包、绝不明文入库。
