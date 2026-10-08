#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""极简博客生成器 —— 零依赖（只用 Python 标准库）。

设计风格：植物学 / 有机 / 浅黄浅绿 / 弥散 / 报刊分栏

用法：
    python3 build.py

做什么：
    读 posts/*.md（极简 frontmatter：title / date / tags）
    → 生成 dist/index.html（报纸式文章列表，分栏排版）
    → 生成 dist/<slug>.html（每篇文章，报刊分栏正文）
    → 生成 dist/style.css（样式）

为什么不用现成框架：
    博客就是几十个静态页面。引入 Astro/Tailwind 会带来 350MB node_modules、
    构建超时、以及一堆看不懂的配置。纯手写可控、瞬时构建、零依赖。
"""
from __future__ import annotations

import html
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS = ROOT / "posts"
DIST = ROOT / "docs"   # 输出到 docs/ —— GitHub Pages 可直接把这个目录当站点根

# ── 配置（改这里就改了站点）───────────────────────────────────────────────
SITE = {
    "title": "Amazinnn",
    "subtitle": "写点想写的",
    "footer": "",   # 不想显示就留空
}
# ─────────────────────────────────────────────────────────────────────────

DATE_FMT = "%Y-%m-%d"


def parse_post(path: Path) -> dict | None:
    """解析单个 .md：极简 frontmatter（--- 包裹）+ 正文。"""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None

    meta = {"title": path.stem, "date": "", "tags": []}
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm, body = parts[1], parts[2]
            for line in fm.strip().splitlines():
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                k, v = k.strip().lower(), v.strip()
                if k == "title":
                    meta["title"] = v
                elif k == "date":
                    meta["date"] = v.strip().strip("'\"")
                elif k == "display":
                    meta["display"] = v.strip().strip("'\"")
                elif k == "tags":
                    raw = v.strip().strip("[]")
                    meta["tags"] = [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]
            text = body.strip()

    try:
        d = datetime.strptime(meta["date"], DATE_FMT)
        meta["sort_key"] = d.timestamp()
    except (ValueError, KeyError):
        meta["sort_key"] = 0.0

    meta["slug"] = path.stem
    meta["body"] = text
    meta["date_display"] = meta["date"] or "—"
    # display: 列表里显示的短标题（默认用 title）
    meta["list_title"] = meta.get("display") or meta["title"]
    return meta


def md_to_html(md: str) -> str:
    """够用的 Markdown → HTML。不用第三方库。"""
    out, in_code, code_buf = [], False, []

    def inline(s: str) -> str:
        s = html.escape(s, quote=False)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^\*\n]+)\*(?!\*)", r"<em>\1</em>", s)
        # 图片: ![alt](src)
        s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1" style="max-width:100%;height:auto;display:block;margin:24px auto;border-radius:4px">', s)
        # 站点在 /blog/ 子目录, 把正文里的根绝对路径补上 /blog 前缀
        s = re.sub(r'src="/images/', 'src="/blog/images/', s)
        # 链接: [text](url)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', s)
        return s

    for line in md.splitlines():
        if line.strip().startswith("```"):
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code_buf), quote=False) + "</code></pre>")
                code_buf, in_code = [], False
            else:
                in_code = True
            continue
        if in_code:
            code_buf.append(line)
            continue

        s = line.strip()
        if not s:
            continue
        if s in ("---", "***", "___"):
            out.append("<hr>")
        elif s.startswith("### "):
            out.append(f"<h3>{inline(s[4:])}</h3>")
        elif s.startswith("## "):
            out.append(f"<h2>{inline(s[3:])}</h2>")
        elif s.startswith("# "):
            out.append(f"<h1>{inline(s[2:])}</h1>")
        elif s.startswith("> "):
            out.append(f"<blockquote>{inline(s[2:])}</blockquote>")
        elif re.match(r"^[-*]\s+", s):
            if out and out[-1].startswith("<li>"):
                out[-1] = out[-1][:-5] + inline(re.sub(r"^[-*]\s+", "", s)) + "</li>"
            else:
                out.append("<li>" + inline(re.sub(r"^[-*]\s+", "", s)) + "</li>")
        else:
            out.append(f"<p>{inline(s)}</p>")

    html_out, in_ul = [], False
    for o in out:
        if o.startswith("<li>"):
            if not in_ul:
                html_out.append("<ul>")
                in_ul = True
            html_out.append(o)
        else:
            if in_ul:
                html_out.append("</ul>")
                in_ul = False
            html_out.append(o)
    if in_ul:
        html_out.append("</ul>")
    return "\n".join(html_out)


# ── 样式：植物学 / 有机 / 弥散 / 报刊 ────────────────────────────────────
CSS = """
:root {
  /* 浅黄 + 浅绿，植物标本配色 */
  --paper:      #fbf8ee;   /* 纸底：暖米黄 */
  --paper-warm: #f5efdc;   /* 次级纸面 */
  --ink:        #33372a;   /* 主文字：深橄榄 */
  --ink-soft:   #6b7059;   /* 次级文字 */
  --ink-faint:  #9aa08a;   /* 极淡 */
  --leaf:       #7a9a5c;   /* 叶片绿 */
  --leaf-deep:  #55703c;   /* 深叶 */
  --leaf-pale:  #c3d4a8;   /* 嫩叶 */
  --sun:        #e8d98a;   /* 浅黄 */
  --line:       #ddd8c0;   /* 分隔线 */
  --line-soft:  #e8e3d0;

  --radius: 4px;          /* 扁平：小圆角 */
  --serif: "Songti SC", "Noto Serif SC", "Source Han Serif SC",
           Georgia, "Times New Roman", serif;
  --sans: -apple-system, BlinkMacSystemFont, "PingFang SC",
          "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}

* { box-sizing: border-box; }

html { scroll-behavior: smooth; }

body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--serif);
  font-size: 17px;
  line-height: 1.95;
  letter-spacing: .01em;
}

/* 弥散感：柔和的径向渐层，像漫射光下的纸面 */
body::before {
  content: "";
  position: fixed; inset: 0;
  pointer-events: none;
  z-index: 0;
  background:
    radial-gradient(ellipse 70% 50% at 15% 0%,  rgba(232,217,138,.22), transparent 60%),
    radial-gradient(ellipse 60% 45% at 92% 8%,  rgba(122,154,92,.14),  transparent 62%),
    radial-gradient(ellipse 80% 60% at 50% 100%, rgba(195,212,168,.16), transparent 65%);
}

.wrap {
  position: relative; z-index: 1;
  max-width: 1080px; margin: 0 auto; padding: 56px 28px 100px;
}

/* ── 报头 ────────────────────────────────────────────── */
.masthead {
  border-bottom: 3px double var(--line);
  padding-bottom: 22px; margin-bottom: 8px;
  text-align: center;
}
.masthead h1 {
  margin: 0; font-size: 38px; font-weight: 600;
  letter-spacing: .06em; color: var(--leaf-deep);
}
.masthead .subtitle {
  margin: 10px 0 0; color: var(--ink-soft);
  font-size: 15px; letter-spacing: .04em;
}
.dateline {
  display: flex; justify-content: space-between; align-items: baseline;
  font-family: var(--sans); font-size: 12px; color: var(--ink-faint);
  border-bottom: 1px solid var(--line);
  padding: 7px 2px; margin-bottom: 34px;
  letter-spacing: .06em;
}

/* ── 首页：报纸分栏 ──────────────────────────────────── */
.column-rule { columns: 2; column-gap: 44px; column-rule: 1px solid var(--line-soft); }
@media (max-width: 760px) { .column-rule { columns: 1; } }

.story {
  break-inside: avoid;
  margin-bottom: 30px; padding-bottom: 26px;
  border-bottom: 1px dotted var(--line-soft);
}
.story:last-child { border-bottom: none; }
.story h2 {
  margin: 0 0 8px; font-size: 22px; font-weight: 600;
  line-height: 1.45; letter-spacing: .02em;
}
.story h2 a { color: var(--ink); text-decoration: none; }
.story h2 a:hover { color: var(--leaf); }
.story .byline {
  font-family: var(--sans); font-size: 11.5px; color: var(--ink-faint);
  letter-spacing: .12em; margin-bottom: 12px; text-transform: uppercase;
}
.story .excerpt { margin: 0; color: var(--ink-soft); font-size: 15px; line-height: 1.85; }

.tag {
  display: inline-block; font-family: var(--sans);
  background: rgba(195,212,168,.4); color: var(--leaf-deep);
  border-radius: 3px; padding: 1px 7px; font-size: 11px;
  margin: 10px 5px 0 0; letter-spacing: .06em;
}

/* ── 文章页 ─────────────────────────────────────────── */
.article { max-width: 700px; margin: 0 auto; }
.article-head { text-align: center; margin-bottom: 40px; }
.article-head h1 {
  margin: 0 0 12px; font-size: 34px; font-weight: 600;
  line-height: 1.4; letter-spacing: .03em; color: var(--leaf-deep);
}
.article-head .byline {
  font-family: var(--sans); font-size: 12px; color: var(--ink-faint);
  letter-spacing: .16em; text-transform: uppercase;
}
.article-head hr {
  border: none; border-top: 1px solid var(--line);
  margin: 22px auto 0; width: 120px;
}

.article h2 {
  font-size: 21px; font-weight: 600; margin: 40px 0 14px;
  color: var(--leaf-deep); letter-spacing: .02em;
  padding-left: 13px; border-left: 3px solid var(--leaf-pale);
}
.article h3 { font-size: 17px; font-weight: 600; margin: 30px 0 10px; color: var(--ink-soft); }
.article p { margin: 16px 0; }
.article a { color: var(--leaf-deep); text-decoration: none; border-bottom: 1px solid var(--leaf-pale); }
.article a:hover { border-bottom-color: var(--leaf); }

.article blockquote {
  margin: 24px 0; padding: 4px 0 4px 22px;
  border-left: 2px solid var(--sun);
  color: var(--ink-soft); font-style: italic;
}
.article code {
  background: var(--paper-warm); color: var(--leaf-deep);
  padding: 2px 6px; border-radius: 3px;
  font-family: ui-monospace, "SF Mono", Menlo, monospace; font-size: 14px;
}
.article pre {
  background: var(--paper-warm); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 16px 18px; overflow-x: auto;
}
.article pre code { background: none; padding: 0; color: var(--ink); }
.article ul { padding-left: 24px; }
.article li { margin: 6px 0; }
.article hr { border: none; border-top: 1px solid var(--line-soft); margin: 34px 0; }

.article-footer { margin-top: 48px; padding-top: 20px; border-top: 1px solid var(--line-soft); }
.back {
  display: inline-block; font-family: var(--sans); font-size: 13px;
  color: var(--ink-soft); text-decoration: none; letter-spacing: .06em;
}
.back:hover { color: var(--leaf); }

.empty {
  text-align: center; padding: 80px 20px; color: var(--ink-faint);
  font-style: italic;
}

.site-footer {
  margin-top: 70px; padding-top: 22px; border-top: 3px double var(--line);
  text-align: center; font-family: var(--sans);
  font-size: 12px; color: var(--ink-faint); letter-spacing: .1em;
}
"""

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{subtitle}">
<link rel="stylesheet" href="style.css">
</head>
<body><div class="wrap">
{content}
</div></body>
</html>
"""


def excerpt(md: str, n: int = 96) -> str:
    """从正文里取一段纯文字做摘要。"""
    for line in md.splitlines():
        s = line.strip()
        if not s or s.startswith(("#", ">", "-", "*", "|", "```", "---")):
            continue
        s = re.sub(r"[*`_]", "", s)
        return s[:n] + ("…" if len(s) > n else "")
    return ""


def build():
    if not POSTS.exists():
        print("❌ posts/ 目录不存在")
        sys.exit(1)
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    # 同步 public/ 静态资源（images 等）到 dist
    PUBLIC = ROOT / "public"
    if PUBLIC.exists():
        shutil.copytree(PUBLIC, DIST, dirs_exist_ok=True)
    # 本地图片转 webp（压缩减小体积；国内加载 GitHub Pages 图片经常慢/卡，webp 更小更快）
    import subprocess as _sp
    IMG_SRC = DIST / "images" / "kaguya"
    if IMG_SRC.exists():
        for f in sorted(IMG_SRC.iterdir()):
            if f.suffix.lower() in (".jpg", ".jpeg", ".png"):
                orig_size = f.stat().st_size
                target = f.with_suffix(".webp")
                print(f"  ↓ 转换 {f.name} -> webp")
                r = _sp.run(
                    ["cwebp", "-quiet", "-q", "82", str(f), "-o", str(target)],
                    capture_output=True, text=True)
                if target.exists() and target.stat().st_size > 0:
                    f.unlink()
                    print(f"  ✓ {target.name} ({target.stat().st_size}B, 原 {orig_size}B)")
                else:
                    if target.exists():
                        target.unlink()
                    print(f"  ✗ cwebp 失败({r.stderr[:60]})，保留原图 {f.name}")
    (DIST / "style.css").write_text(CSS, encoding="utf-8")

    posts = []
    for f in sorted(POSTS.glob("*.md")):
        p = parse_post(f)
        if p:
            posts.append(p)
    posts.sort(key=lambda x: x["sort_key"], reverse=True)

    # 文章页
    page_footer = f'\n<div class="site-footer">{SITE["footer"]}</div>' if SITE.get("footer") else ""
    for p in posts:
        body_html = md_to_html(p["body"])
        tags = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in p["tags"])
        content = f"""<article class="article">
  <div class="article-head">
    <h1>{html.escape(p['title'])}</h1>
    <div class="byline">{p['date_display']}</div>
    <hr>
  </div>
  {body_html}
  <div>{tags}</div>
  <div class="article-footer"><a class="back" href="index.html">← 返回</a></div>
</article>{page_footer}"""
        (DIST / f"{p['slug']}.html").write_text(
            PAGE.format(title=html.escape(p["title"]), subtitle="", content=content),
            encoding="utf-8")

    # 首页：报头 + 分栏
    if posts:
        latest = posts[0]
        dateline = (
            f'<div class="dateline">'
            f"<span>{len(posts)} 篇</span>"
            f"<span>最后更新 {latest['date_display']}</span>"
            f"</div>"
        )
        stories = []
        for p in posts:
            tags = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in p["tags"])
            ex = html.escape(excerpt(p["body"]))
            stories.append(f"""<div class="story">
  <h2><a href="{p['slug']}.html">{html.escape(p['list_title'])}</a></h2>
  <div class="byline">{p['date_display']}</div>
  <p class="excerpt">{ex}</p>
  <div>{tags}</div>
</div>""")
        columns = f'<div class="column-rule">\n' + "\n".join(stories) + "\n</div>"
    else:
        dateline = ""
        columns = '<div class="empty">还没有文章。</div>\n<div class="empty" style="font-size:13px;padding-top:0">写点东西就会出现在这里。</div>'

    footer = f'\n<div class="site-footer">{SITE["footer"]}</div>' if SITE.get("footer") else ""

    index = f"""<header class="masthead">
  <h1>{SITE['title']}</h1>
  <p class="subtitle">{SITE['subtitle']}</p>
</header>
{dateline}
{columns}{footer}"""
    (DIST / "index.html").write_text(
        PAGE.format(title=SITE["title"], subtitle=SITE["subtitle"], content=index),
        encoding="utf-8")

    total = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
    print(f"✅ 构建完成：{len(posts)} 篇文章, {len(list(DIST.glob('*')))} 个文件, {total/1024:.1f} KB")
    for p in posts:
        print(f"   · {p['date_display']}  {p['title']}")
    return posts


if __name__ == "__main__":
    build()
