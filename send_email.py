"""
send_email.py — Intel Briefing 邮件推送
通过 Resend API 将当天的日报 Markdown 文件发送到指定邮箱。

环境变量（在 GitHub Secrets 中配置）：
  RESEND_API_KEY   - Resend API 密钥（必须）
  RESEND_TO_EMAIL  - 收件人邮箱（必须）
  RESEND_FROM      - 发件人（可选，默认使用 Resend 官方域名）
"""

import os
import sys
import glob
from datetime import datetime, timezone, timedelta
import resend

# ── 配置 ──────────────────────────────────────────────────────────────────────

RESEND_API_KEY  = os.environ.get("RESEND_API_KEY", "")
TO_EMAIL        = os.environ.get("RESEND_TO_EMAIL", "")
FROM_EMAIL      = os.environ.get("RESEND_FROM", "Intel Briefing <onboarding@resend.dev>")
REPORTS_DIR     = "reports/daily_briefings"

# ── 工具函数 ───────────────────────────────────────────────────────────────────

def find_todays_report() -> str | None:
    """查找今天生成的日报文件（优先精确匹配，否则取最新文件）"""
    # 北京时间今天
    beijing_now = datetime.now(timezone(timedelta(hours=8)))
    date_str = beijing_now.strftime("%Y-%m-%d")

    exact = os.path.join(REPORTS_DIR, f"Morning_Report_{date_str}.md")
    if os.path.isfile(exact):
        return exact

    # 备选：取目录下最新的 .md 文件
    files = sorted(glob.glob(os.path.join(REPORTS_DIR, "*.md")), key=os.path.getmtime, reverse=True)
    return files[0] if files else None


def md_to_html(md_text: str) -> str:
    """将 Markdown 转为基础 HTML（无需额外依赖）"""
    import re
    lines = md_text.split("\n")
    html_lines = []
    in_code = False

    for line in lines:
        # 代码块
        if line.startswith("```"):
            tag = "</pre>" if in_code else "<pre style='background:#f4f4f4;padding:8px;border-radius:4px;overflow-x:auto;'>"
            in_code = not in_code
            html_lines.append(tag)
            continue
        if in_code:
            html_lines.append(line.replace("<", "&lt;").replace(">", "&gt;"))
            continue

        # 标题
        if line.startswith("### "):
            html_lines.append(f"<h3 style='color:#2c3e50;margin-top:20px;'>{line[4:]}</h3>")
        elif line.startswith("## "):
            html_lines.append(f"<h2 style='color:#1a252f;border-bottom:2px solid #3498db;padding-bottom:6px;'>{line[3:]}</h2>")
        elif line.startswith("# "):
            html_lines.append(f"<h1 style='color:#1a252f;'>{line[2:]}</h1>")
        # 列表
        elif line.startswith("- "):
            html_lines.append(f"<li>{line[2:]}</li>")
        # 分隔线
        elif line.strip() in ("---", "***", "___"):
            html_lines.append("<hr style='border:none;border-top:1px solid #ddd;margin:16px 0;'>")
        # 空行
        elif line.strip() == "":
            html_lines.append("<br>")
        # 普通段落：加粗 **text**
        else:
            line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
            line = re.sub(r"\*(.+?)\*", r"<em>\1</em>", line)
            line = re.sub(r"`(.+?)`", r"<code style='background:#f0f0f0;padding:2px 4px;border-radius:3px;'>\1</code>", line)
            # Markdown 链接 [text](url)
            line = re.sub(r"\[(.+?)\]\((https?://[^\)]+)\)", r'<a href="\2" style="color:#3498db;">\1</a>', line)
            html_lines.append(f"<p style='margin:6px 0;line-height:1.6;'>{line}</p>")

    return "\n".join(html_lines)


def build_html_email(md_content: str, date_str: str) -> str:
    """构建完整的 HTML 邮件正文"""
    body = md_to_html(md_content)
    return f"""
<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><title>Intel Briefing {date_str}</title></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;max-width:760px;margin:0 auto;padding:20px;color:#333;">
  <div style="background:linear-gradient(135deg,#1a252f,#2c3e50);color:white;padding:24px 28px;border-radius:10px 10px 0 0;">
    <div style="font-size:13px;opacity:0.7;margin-bottom:4px;">🕵️ AI 情报聚合系统</div>
    <div style="font-size:22px;font-weight:bold;">Intelligence Briefing</div>
    <div style="font-size:13px;opacity:0.8;margin-top:4px;">{date_str}・北京时间早报</div>
  </div>
  <div style="border:1px solid #e0e0e0;border-top:none;padding:24px 28px;border-radius:0 0 10px 10px;background:#fff;">
    {body}
  </div>
  <div style="text-align:center;color:#aaa;font-size:11px;margin-top:12px;">
    由 <a href="https://github.com/77AutumN/Intel_Briefing" style="color:#aaa;">Intel Briefing</a> 自动生成 · GitHub Actions
  </div>
</body>
</html>
"""

# ── 主流程 ────────────────────────────────────────────────────────────────────

def main():
    if not RESEND_API_KEY:
        print("❌ 缺少 RESEND_API_KEY 环境变量")
        sys.exit(1)
    if not TO_EMAIL:
        print("❌ 缺少 RESEND_TO_EMAIL 环境变量")
        sys.exit(1)

    report_path = find_todays_report()
    if not report_path:
        print(f"❌ 未找到日报文件（目录：{REPORTS_DIR}）")
        sys.exit(1)

    print(f"📄 读取日报：{report_path}")
    with open(report_path, encoding="utf-8") as f:
        md_content = f.read()

    beijing_now = datetime.now(timezone(timedelta(hours=8)))
    date_str = beijing_now.strftime("%Y年%m月%d日")

    resend.api_key = RESEND_API_KEY
    params: resend.Emails.SendParams = {
        "from": FROM_EMAIL,
        "to": [TO_EMAIL],
        "subject": f"🕵️ Intel Briefing · {date_str}",
        "html": build_html_email(md_content, date_str),
    }

    result = resend.Emails.send(params)
    print(f"✅ 邮件已发送！ID: {result.get('id', 'unknown')}")
    print(f"   收件人：{TO_EMAIL}")


if __name__ == "__main__":
    main()
