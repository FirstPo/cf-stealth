# Cloudflare 隐身术 🥷

> 用 Python + Playwright 绕过 Cloudflare Turnstile 验证的完整教学项目

## 项目简介

本项目通过四个递进阶段，演示如何使用 Python 和 Playwright 对抗 Cloudflare 的反爬虫保护机制，包括指纹识别、Turnstile 验证和行为分析。**仅供学习研究使用。**

## 环境要求

- Python 3.11+
- conda（推荐使用 [Miniconda](https://docs.conda.io/en/latest/miniconda.html)）

## 快速开始

```bash
# 1. 创建 conda 环境（清华源）
conda create -n cf_stealth python=3.11 -y --channel https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
conda activate cf_stealth

# 2. 配置 pip 清华源
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 安装依赖
pip install playwright playwright-stealth fake-useragent beautifulsoup4 requests

# 4. 安装 Chromium 内核
playwright install chromium
```

## 项目结构

```
.
├── quest1_1_observe.py       # 阶段1: 观察 CF 拦截现象
├── quest1_2_stealth.py       # 阶段1: 引入 Stealth 驱动
├── quest2_1_useragent.py     # 阶段2: 真实 UA + 视口配置
├── quest3_1_shadowdom.py     # 阶段3: 穿透 Shadow DOM 点击 Turnstile
├── quest3_2_random_delay.py  # 阶段3: 随机延时 + 鼠标轨迹模拟
├── quest4_1_extract.py       # 阶段4: 通过验证后提取业务数据
├── quest_final_demo.py       # 成果验收: 对 CF 官方 Turnstile Demo 完整测试
└── README.md
```

## 四个阶段

### 阶段 1：破除「简易爬虫」的偏见

| 脚本 | 目标 | 验收标准 |
|------|------|----------|
| `quest1_1_observe.py` | 用标准 Playwright 观察被拦截现象 | 页面标题含 "Just a moment..." |
| `quest1_2_stealth.py` | 引入 playwright-stealth 隐藏自动化特征 | `navigator.webdriver = false` |

### 阶段 2：调教浏览器环境

| 脚本 | 目标 | 验收标准 |
|------|------|----------|
| `quest2_1_useragent.py` | 配置真实 UA、视口、时区 | bot.sannysoft.com 全绿 |

### 阶段 3：攻克 Turnstile

| 脚本 | 目标 | 验收标准 |
|------|------|----------|
| `quest3_1_shadowdom.py` | 穿透 Shadow DOM 定位并点击 Turnstile | 验证框消失，出现绿色勾 |
| `quest3_2_random_delay.py` | 随机延时 + 鼠标轨迹模拟 | 5次中≥4次通过 |

### 阶段 4：成果验收

| 脚本 | 目标 | 验收标准 |
|------|------|----------|
| `quest4_1_extract.py` | 提取受保护页面的真实业务数据 | 生成 result.json，含真实内容 |
| `quest_final_demo.py` | 对 CF 官方 Turnstile Demo 完整验收 | token 存在，数据保存成功 |

## 核心技术点

### 1. playwright-stealth
隐藏浏览器自动化特征，包括：
- `navigator.webdriver` → `false`
- Chrome 运行时对象伪造
- 插件、语言、平台信息标准化

### 2. Shadow DOM 穿透
Turnstile widget 嵌套在 iframe 内，通过 `page.frames` 遍历 + `getBoundingClientRect()` 精确定位点击坐标。

### 3. 人类行为模拟
```python
# 随机区间 sleep，绝不硬编码
await asyncio.sleep(random.uniform(0.5, 2.0))

# 随机鼠标轨迹
for _ in range(steps):
    await page.mouse.move(tx + random.randint(-120, 120), ty + random.randint(-80, 80))
```

## 依赖版本

| 包 | 版本 |
|----|------|
| playwright | 1.58.0 |
| playwright-stealth | 2.0.2 |
| fake-useragent | 2.2.0 |
| beautifulsoup4 | 4.14.3 |
| requests | 2.32.5 |

## 免责声明

本项目**仅供学习和安全研究使用**。请勿将本项目用于任何违反目标网站服务条款的行为。使用本项目造成的任何法律或经济后果由使用者自行承担。

## License

MIT
