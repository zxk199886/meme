# ADR 0004 · 链上写入用 server-submit（而非 client-submit + attest）

- 状态：已接受（MVP）
- 日期：2026-06-16

## 背景
排行榜上分与代币发放需要一种"经服务端校验后才生效"的链上写入方式。两种模式：
- **server-submit**：后端 authority 直接签名并发交易。
- **server-attest + client-submit**：后端返回 Ed25519 签名凭证，链上验签后由玩家钱包提交。

## 决策
MVP 采用 **server-submit**：后端持 authority、签名并发交易，玩家只看到结果。

## 理由
- UX 最干净：玩家无需为每次上分/领奖额外签名。
- 链上 gas 由后端控制，便于补贴与限流。
- 反作弊边界清晰：所有写入都经服务端校验后由 authority 执行。

## 备选与否决
- **server-attest + client-submit**：更去中心化、玩家自付费，但更复杂（链上需验 Ed25519、
  客户端需提交并处理失败）。可在更追求去中心化时复核。

## 影响
- 链上程序以 `require!(signer == AUTHORITY_PUBKEY)` 门控写入指令。
- authority 私钥成为高价值秘密，仅在后端（KMS），见 `07-security-anticheat.md`。
