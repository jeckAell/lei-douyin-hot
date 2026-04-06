# 抖音热点中心自动爬取

## 功能说明

自动爬取抖音热点中心（douhot.douyin.com/square/hotspot）AI原生影像分类下的视频榜单数据，获取前10条视频的完整信息，通过 `analyze_video.py` 分析后保存到 `scripts.json` 作为视频脚本素材库。

## 技术架构

- **浏览器控制**: Chrome Debug 模式（CDP 协议）+ agent-browser
- **Chrome 路径**: `~/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome`
- **独立 Chrome**: 端口 9223，用户数据 `~/.config/chromium-hot`
- **数据存储**: `~/.openclaw/workspace/doubao/sheet/scripts/data/scripts.json`
- **登录保持**: 通过独立的 Chrome Profile 自动维持登录状态
- **目标分类**: AI原生影像（first_tag=643, second_tag=64301x64302）

## 脚本说明

| 脚本 | 功能 |
|------|------|
| `start_douyin.sh` | 启动专属 Chrome（9223） |
| `hot_trending.py` | 主爬取流程（循环处理10条视频，调用 analyze_video.py） |
| `check_douyin_hot.py` | 登录状态检测 + 二维码截图（端口9222） |
| `analyze_video.py` | 视频详情分析（需配合 hot_trending.py 使用） |
| `cleanup_old_data.py` | 清理3天前的旧数据 |

## 使用前提

1. Chrome 能正常启动（ms-playwright 版本）
2. 已完成一次扫码登录（登录状态保存在 `~/.config/chromium-hot`）

## 目标 URL

```
https://douhot.douyin.com/square/hotspot?active_tab=hotspot_video&date_window=1&first_tag=643&second_tag=64301x64302&sub_type=1002
```

**参数说明**：
| 参数 | 值 | 说明 |
|------|-----|------|
| active_tab | hotspot_video | 视频榜 |
| date_window | 1 | 近1小时 |
| first_tag | 643 | AI原生影像大类 |
| second_tag | 64301x64302 | AI原生影像子分类 |
| sub_type | 1002 | 视频内容类型 |

## 数据字段说明

| 字段 | 说明 |
|------|------|
| title | 视频标题 |
| category | 分类（固定：AI原生影像） |
| tags | 话题标签列表 |
| author | 账号名称 |
| author_fans | 粉丝数 |
| publish_time | 发布时间 |
| heat | 热度值/排名 |
| likes | 点赞数 |
| shares | 分享数 |
| comments | 评论数 |
| video_url | 抖音视频直链 |
| source | 来源（固定：抖音热点中心） |
| date | 数据采集日期 |

## 定时任务

建议配合 cron 设置每日自动执行：

```bash
# 每天早上8点自动爬取
0 8 * * * /bin/bash -c 'bash ~/.openclaw/workspace/skills/lei-douyin-hot/scripts/start_douyin.sh && sleep 5 && python3 ~/.openclaw/workspace/skills/lei-douyin-hot/scripts/hot_trending.py' >> ~/.openclaw/workspace/douyin_hot/cron.log 2>&1
```
