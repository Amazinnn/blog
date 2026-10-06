# Amazinnn

## 结构

```
posts/     文章（markdown）
build.py   生成器
docs/      构建产物，GitHub Pages 从这里发布
```

## 加文章

写一个 `.md` 丢进 `posts/`：

```markdown
---
title: 文章标题
date: 2026-10-06
tags: [标签1, 标签2]
---

正文。markdown 语法。
```

## 发布

```bash
./deploy.sh "说明"
```

构建 + 提交 + 推送，约 1 分钟后上线。

线上：https://amazinnn.github.io/blog/

## 改站点配置

`build.py` 顶部的 `SITE` 字典：标题、副标题、页脚。
`build.py` 中 `CSS` 字符串：配色和排版。