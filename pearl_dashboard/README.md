# Pearl (PRL) 自动租卡挖矿

在你自己电脑上运行的小程序 + 网页面板：

- 实时读取 **SafeTrade** 的 PRL 价格、**Vast.ai** 上现在能租的卡和价格（RunPod / Salad / HyperAI 仅比价）。
- 算出每张卡每天的成本、收入、利润和保本币价。
- 有利润时**自动在 Vast.ai 租卡**，开机自动下载 SRBMiner 挖到 **Kryptex 矿池**；
  亏钱、卡坏了、拿不到币价、余额不足时**自动退租**。
- 网页上看余额还能撑几天、每台机器的算力、花费、挖到多少币和盈亏。

你要做的：给 Vast.ai 充值，第一次填好配置。

> ⚠️ 这是用真钱做的高风险操作。币价一天能跌 10%+，难度会随币价上涨而上升，
> 所有收益数字都是估算。最大损失 = 你 Vast 账户里的余额。我不是理财顾问。

## 桌面版（Windows，推荐）

第一次：打开**普通的 PowerShell（不要用管理员）**，代码要放在自己的用户文件夹里，
不要放在 `C:\Windows\System32`（管理员 PowerShell 默认在那里，双击运行时没权限写文件）：

```powershell
cd $HOME
git clone https://github.com/zxk199886/meme.git
cd meme
git checkout claude/eager-keller-wp51iz
pip install -r pearl_dashboard\requirements.txt
python -m pearl_dashboard.desktop --install-shortcut
```

之后双击桌面上的 **「Pearl 挖矿」** 就会打开一个独立窗口，没有黑色命令行窗口。关掉窗口程序就退出。

> 更新代码后、或换了 Python / 移动了 `meme` 文件夹后，请**重新运行一次** `--install-shortcut`。
> 快捷方式会用你运行这条命令时的那个 Python 和环境（Anaconda 也可以）。

- 想先看效果：`python -m pearl_dashboard.desktop --mock`（假数据演示）。
- 打不开或闪退：会弹窗显示报错，完整日志在 `pearl_dashboard\desktop.log`，把弹窗文字或日志发给 Claude。
  在 PowerShell 里运行 `python -m pearl_dashboard.desktop` 也能直接看到报错。
- 如果桌面窗口组件装不上，会自动改用 Edge 的应用窗口打开，并多一个带「退出」按钮的小窗口。
- 已经开着时再双击，不会启动第二份，只是再打开一个窗口。
- 更新代码：关掉窗口 → `git pull` → 再双击。
- 运行期间会阻止电脑休眠，笔记本请插电、别合盖。

## 模拟一天（不需要任何账号，不花钱）

需要 Python 3.9+ 和 Git。

### Windows（PowerShell）

开始菜单搜 “PowerShell” 打开，依次输入：

```powershell
# 下载代码（只需第一次）
git clone https://github.com/zxk199886/meme.git
cd meme
git checkout claude/eager-keller-wp51iz
pip install -r pearl_dashboard\requirements.txt

# 1. 自检：几秒钟，看币价和 Vast 报价能不能拿到
python -m pearl_dashboard.check

# 2. 都是 ✅ 就开始跑，浏览器打开 http://127.0.0.1:8080 ，这个窗口别关
python -m pearl_dashboard.server

# 3. 第二天另开一个 PowerShell 看报告，把输出贴给 Claude
cd meme
python -m pearl_dashboard.report
```

- 提示找不到 `python` 时，把命令里的 `python` 换成 `py`。
- 面板运行期间会自动阻止 Windows 休眠（关掉窗口即恢复）。但**笔记本合盖仍会休眠**：插上电源、别合盖，
  或在 控制面板 → 电源选项 → “选择关闭笔记本计算机盖的功能” 里改成“不采取任何操作”。
- 以后更新代码：在 `meme` 文件夹里运行 `git pull`。

### Mac / Linux

```bash
pip install -r pearl_dashboard/requirements.txt
python -m pearl_dashboard.check
caffeinate -i python -m pearl_dashboard.server   # Mac 防休眠；Linux 直接 python -m pearl_dashboard.server
python -m pearl_dashboard.report
```

- 不填配置也能模拟：没有 `config.yaml` 时用 `config.example.yaml` 的默认值，Vast 报价先尝试不登录查询。
  如果自检提示“Vast 要求 API key”，去 Vast.ai 注册拿个 key 填进 `config.yaml`（查报价不花钱）。
- 自检有 ❌：把整段输出贴给 Claude，通常只要改配置里的一个地址。
- 面板 http://127.0.0.1:8080 的“过去 24 小时”一栏会实时显示价格曲线、保本线、值得租的时间段和模拟盈亏。
- 模拟没有算开机等待、坏机器这些损耗，所以**模拟盈亏是上限**，真租会差一些。
- 电脑休眠的时间不计入报告；中途重启面板没关系，历史保存在 `pearl_dashboard/pearl.sqlite3`。

## 一、安装

```bash
pip install -r pearl_dashboard/requirements.txt
cp pearl_dashboard/config.example.yaml pearl_dashboard/config.yaml
```

## 二、填配置 `pearl_dashboard/config.yaml`

真租时必填三项（只模拟的话都可以不填）：

| 配置 | 去哪拿 |
|---|---|
| `vast.api_key` | Vast.ai 登录 → Account → API Keys（也可以用环境变量 `VAST_API_KEY`） |
| `pool.wallet` | 你的 PRL 钱包地址 |
| `gpus` | 每张卡的算力（TH/s）。默认只租 RTX 5090（340 TH/s）。 |

建议填：

- `instance.miner_sha256`：SRBMiner 压缩包的 SHA256。去
  [SRBMiner 发布页](https://github.com/doktor83/SRBMiner-Multi/releases) 下载同一个文件，
  `sha256sum` 算出来填上。填了之后文件被篡改就会拒绝运行。不填的话会把算出来的值写进机器上的日志。
- `pool.stats_url`：Kryptex 矿池统计 API（文档 https://pool.kryptex.com/en/api ），
  填了面板才能显示**矿池实际**算力和收益，也能发现“开着但没在挖”的机器。
- `price.coingecko_id`：SafeTrade 挂了时的备用价格源（注意别填成同名的 Perle）。
- `prl_per_th_day`：每 TH/s 每天产出多少 PRL。默认 0.01554 来自 WhatToMine，**会随难度变**，定期更新。

`limits` 里是硬性上限，默认很保守：最多 2 张卡、单卡 ≤ $0.45/h、预期利润率 ≥ 20% 才租。

## 三、运行

```bash
python -m pearl_dashboard.server
```

打开 http://127.0.0.1:8080 。

想先看看面板长什么样（假数据，不连任何网站）：

```bash
MOCK=1 python -m pearl_dashboard.server            # Mac / Linux
$env:MOCK=1; python -m pearl_dashboard.server      # Windows PowerShell
```

## 四、建议的上手顺序

1. **模拟一天**（见最上面）：程序会用虚拟机器跑完整策略，面板上显示模拟盈亏，日志里写“会租哪张、会退哪张”。不花钱。
2. **小额真租**：把 `limits.max_gpus` 改成 1，`dry_run: false`，重启，在网页上点“确认开始真租”。
   跑几个小时后看“矿池实际盈亏”是否和预估一致，以及 Kryptex 网站上是否能看到 `vast<实例号>` 这个矿工。
3. 确认实际收益靠谱再慢慢调大上限。

## 安全机制

| 情况 | 动作 |
|---|---|
| 某台机器连续 5 次（5 分钟）按当前币价算是亏的 | 退租这台 |
| 开机 20 分钟后 GPU 利用率 < 50%、状态不是 running、或矿池看不到它的算力，连续 5 次 | 退租这台（坏机器） |
| 30 分钟拿不到实时币价 | 退掉所有机器 |
| Vast 余额 < `min_balance_reserve` | 退掉所有机器，不再租 |
| 机器活满 12 小时 | 机器**自己**调用 Vast API 销毁（电脑关机/面板没开也会执行）；面板开着时会提前租好替换机 |
| 网页“紧急停止” 或 `python -m pearl_dashboard.stop_all` | 立即退掉所有 `pearl-` 开头的实例 |

- 只管理名字以 `pearl-` 开头的实例，你在 Vast 上的其它机器不会被动。
- 每次启动程序都回到“模拟”模式，必须在网页上再次确认才会真租。
- 面板只监听 127.0.0.1，网页上的按钮需要启动时随机生成的口令，其它网站无法替你点。
- **关掉面板不会停掉已经租的机器**，它们会在 12 小时寿命到时自毁。要马上停请用“紧急停止”。
- 替换机提前 30 分钟租，所以这段时间里卡数和每小时花费可能短暂超过上限。

## 已知限制（需要你在自己电脑上确认）

开发环境连不上 Vast / SafeTrade / Kryptex，以下内容是按官方文档和 vast-cli 源码写的，用假数据测试过，但**没有对真实接口跑过**：

- SafeTrade 价格接口地址（`price.safetrade_url`）。如果面板上提示 SafeTrade 出错，打开 https://safe.trade 找到 PRL/USDT 的行情接口改这一行即可。
- Kryptex 统计 API 的返回格式（解析是宽松的，能识别常见字段名）。
- Vast 机器内自毁用的是 Vast 自动注入的 `CONTAINER_API_KEY`。第一次真租后，
  建议在 Vast 网页上打开机器日志 `/root/pearl-miner.log` 看一眼矿机是否在跑。

## 文件

```
server.py        网页 + 控制循环入口
desktop.py       桌面窗口和桌面快捷方式
check.py         数据源自检
report.py        过去 N 小时的模拟报告
controller.py    每个循环：拉数据 → 决策 → 执行 → 记账
strategy.py      租/退的规则（纯函数，有单元测试）
calc.py          利润、保本价公式
sources/         SafeTrade、Vast、RunPod、Kryptex、WhatToMine
miner/onstart.sh 在租来的机器上运行：下载校验矿机、开挖、到点自毁
store.py         SQLite 记录（pearl.sqlite3）
stop_all.py      紧急退租命令
tests/           单元测试：python -m unittest discover -s pearl_dashboard/tests -t .
```
