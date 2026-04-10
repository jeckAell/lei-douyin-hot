---
name: lei-douyin-hot
description: 抖音热点中心自动爬取 - 通过 Chrome Debug 模式自动抓取抖音热点视频榜前10条视频，提取视频数据保存到 scripts.json，支持每日定时任务。
version: 1.5.1
required_permissions:
  - shell
---

# 抖音热点中心自动爬取

## 核心功能

自动爬取抖音热点中心（douhot.douyin.com/square/hotspot）的视频榜单数据，包括：
- 视频标题、话题标签
- 账号信息、粉丝数
- 发布时间、热度值
- 点赞/分享/评论数据

## 目录结构

```
lei-douyin-hot/
├── SKILL.md              # 本文件
├── README.md             # 详细文档
└── scripts/
    ├── start_douyin.sh     # 启动 Chrome（端口 9223）
    ├── hot_trending.py     # 主爬取脚本
    ├── check_douyin_hot.py # 登录状态检测（端口 9222）
    ├── analyze_video.py    # 视频详情分析
    └── cleanup_old_data.py # 数据清理
```

## 快速开始

### 第一次使用：启动 Chrome + 扫码登录

```bash
# 1. 启动专属 Chrome（端口 9223）
bash ~/.openclaw/workspace/skills/lei-douyin-hot/scripts/start_douyin.sh

# 2. 检测登录状态（未登录则弹出二维码）
python3 ~/.openclaw/workspace/skills/lei-douyin-hot/scripts/check_douyin_hot.py

# 3. 扫码登录后，之后启动 Chrome 会自动保持登录状态
```

### 运行爬取

```bash
# 启动 Chrome 后，直接运行爬取脚本
# 注意：hot_trending.py 会自动启动 Chrome，无需手动启动
python3 ~/.openclaw/workspace/skills/lei-douyin-hot/scripts/hot_trending.py
```

### 测试模式（调试用）

调试时可使用测试模式（有头浏览器），方便观察页面操作：

```bash
# 方式1：启动 Chrome 时指定 test 参数
bash ~/.openclaw/workspace/skills/lei-douyin-hot/scripts/start_douyin.sh test

# 方式2：运行爬取时指定 --headed 参数
python3 ~/.openclaw/workspace/skills/lei-douyin-hot/scripts/hot_trending.py --headed
```

正常运行时两个脚本都使用无头模式（xvfb-run），避免被检测。

## 工作流程

```
hot_trending.py 自动启动 Chrome（9223）
    │
    ▼
打开 douhot.douyin.com/square/hotspot
    │
    ├── 点击「视频榜」tab
    ├── 点击「近1小时」
    │
    ▼
[Step 7a] 检查表格是否加载
    │
    ├── 表格不存在 → 刷新最多5次
    │   └── 5次后仍不存在 → 退出脚本（sys.exit 1）
    │
    ▼
循环处理前10条视频
    │
    ├── 滚动到页面顶部（每次循环开始）
    ├── 定位第 i 个视频行的「查看」按钮
    ├── 验证排名是否匹配（DEBUG 输出）
    ├── CDP 鼠标点击打开详情页（新标签）
    ├── 从 URL 提取 video_id
    ├── 关闭详情页
    │
    ├── 调用 analyze_video.py 分析视频
    │
    ▼
保存到 scripts.json
    │
    ▼
清理3天前的旧数据
```

## 数据输出

**存储位置**: `~/.openclaw/workspace/doubao/sheet/scripts/data/scripts.json`

**目标 URL**（已包含分类参数）:
```
https://douhot.douyin.com/square/hotspot?active_tab=hotspot_video&date_window=24&first_tag=643&second_tag=64301x64302&sub_type=1002
```

**date_window 参数说明**:
- `24` = 近1天（默认）
- `1` = 近1小时（当1天无数据时自动切换）

**数据格式**:
```json
{
  "id": "视频ID",
  "title": "视频标题",
  "category": "AI原生影像",
  "tags": ["#标签1", "#标签2"],
  "author": "账号名",
  "author_fans": "粉丝数",
  "publish_time": "发布时间",
  "heat": "热度值",
  "likes": "点赞数",
  "shares": "分享数",
  "comments": "评论数",
  "video_url": "https://www.douyin.com/video/{video_id}",
  "source": "抖音热点中心",
  "date": "2026-04-05"
}
```

## Chrome 管理

| 项目 | 说明 |
|------|------|
| Chrome 路径 | `~/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome` |
| Chrome 端口 | 9223（专属） |
| 用户数据目录 | `~/.config/chromium-hot` |
| 登录状态 | 只需扫码一次，之后自动保持 |
| 启动脚本 | `start_douyin.sh`（或 hot_trending.py 自动调用） |

### 手动重启 Chrome

```bash
# 如果 Chrome 无响应
pkill -f "chrome.*9223"
bash ~/.openclaw/workspace/skills/lei-douyin-hot/scripts/start_douyin.sh
```

## 定时任务配置

配置每日自动爬取（使用 cron）：

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天早上8点执行）
0 8 * * * /bin/bash -c 'bash ~/.openclaw/workspace/skills/lei-douyin-hot/scripts/start_douyin.sh && sleep 5 && python3 ~/.openclaw/workspace/skills/lei-douyin-hot/scripts/hot_trending.py' >> ~/.openclaw/workspace/douyin_hot/cron.log 2>&1
```

## 故障排查

### Chrome 启动失败
```bash
# 检查 Chrome 进程
ps aux | grep chrome | grep 9223

# 手动启动
bash ~/.openclaw/workspace/skills/lei-douyin-hot/scripts/start_douyin.sh
```

### 登录状态失效
```bash
# 重新检测并扫码（使用端口 9222）
python3 ~/.openclaw/workspace/skills/lei-douyin-hot/scripts/check_douyin_hot.py
```

### 点击"查看"无效
- 可能是 headless 模式被检测
- 页面结构变化，需更新选择器

### 数据文件位置
```bash
cat ~/.openclaw/workspace/doubao/sheet/scripts/data/scripts.json | python3 -m json.tool | head -50
```

## 版本历史

- **v1.5.1**: 修复 Chrome 启动（改用 nohup + xvfb-run）
- **v1.5.0**: 默认 date_window=24（1天），无数据时自动切换到 date_window=1（1小时）
- **v1.4.0**: 修复 Rank 1/2/3 无法采集问题（排名列为空），修复 start.sh 启动阻塞导致 analyze 阶段超时
- **v1.2.0**: URL 参数化（AI原生影像分类 first_tag=643），新增 douhot_page.png 页面截图
- **v1.1.0**: 使用 ms-playwright Chromium，新增 analyze_video.py 视频分析
- **v1.0.0**: 初始版本，使用系统 Firefox
