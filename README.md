# 游戏自动化脚本

PC 桌面游戏自动刷图/挂机工具，基于截图识别 + 键鼠模拟。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 制作模板图像（可选，用于图像识别）

```bash
# 实时查看鼠标坐标
python capture_tool.py coords

# 交互式截取按钮/图标区域保存为模板
python capture_tool.py crop
```

模板图像保存在 `templates/` 目录，在 `config.yaml` 中引用路径。

### 3. 编辑配置文件

修改 `config.yaml`：

- **actions**：填写你游戏的操作序列（按键、点击等）
- **conditions**：配置条件触发（如血量低时喝药）
- **automation.loop_count**：循环次数，`0` 为无限

### 4. 运行

```bash
python automator.py
# 或指定配置文件
python automator.py --config my_game.yaml
```

启动后：
- 按 **F5** 开始/暂停
- 按 **F6** 停止
- 将鼠标快速移到**屏幕左上角**紧急停止

## 动作类型说明

| 类型 | 说明 | 必填参数 |
|------|------|----------|
| `press_key` | 按键盘键 | `key` |
| `click_pos` | 点击固定坐标 | `x`, `y` |
| `click_image` | 找到图像后点击 | `image` |
| `wait` | 等待指定时间 | `seconds` |
| `wait_image` | 等待图像出现 | `image` |
| `drag` | 拖拽 | `from_x`, `from_y`, `to_x`, `to_y` |

## 示例：配置一个刷怪循环

```yaml
actions:
  - type: press_key
    key: "f"
    description: "攻击"
  - type: wait
    seconds: 1.5
  - type: press_key
    key: "r"
    description: "拾取"
  - type: wait
    seconds: 0.5

conditions:
  - name: "血量过低"
    image: "templates/low_hp.png"
    action_group:
      - type: press_key
        key: "h"
        description: "使用药水"
```

## 注意事项

- 本工具仅用于合法的个人游戏体验，请遵守游戏服务条款
- 部分游戏有反作弊系统，使用前请了解风险
- `failsafe: true` 时鼠标移到左上角可立即停止，建议保持开启
