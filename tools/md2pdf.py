#!/usr/bin/env python3
import markdown
from weasyprint import HTML
import sys

with open('/home/duyw/physcausal/reports/paper_spin_em_coupling_cn.md') as f:
    md_text = f.read()

html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'codehilite'])

html_doc = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 2cm; }}
  body {{ 
    font-family: "Source Han Sans CN", "Noto Sans CJK SC", sans-serif; 
    font-size: 11pt; line-height: 1.8; color: #222;
  }}
  h1 {{ font-size: 16pt; border-bottom: 2px solid #333; padding-bottom: 4pt; }}
  h2 {{ font-size: 14pt; border-bottom: 1px solid #999; padding-bottom: 2pt; margin-top: 20pt; }}
  h3 {{ font-size: 12pt; }}
  h4 {{ font-size: 11pt; }}
  code {{ background: #f5f5f5; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }}
  pre {{ background: #f5f5f5; padding: 8pt; border-radius: 4px; font-size: 9pt; overflow-x: auto; }}
  pre code {{ background: none; padding: 0; }}
  blockquote {{ border-left: 3px solid #ccc; margin-left: 0; padding-left: 12pt; color: #555; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10pt 0; }}
  th, td {{ border: 1px solid #ccc; padding: 4pt 8pt; text-align: left; }}
  th {{ background: #eee; }}
</style>
</head>
<body>
{html_body}
</body>
</html>'''

output_path = '/home/duyw/physcausal/reports/paper_spin_em_coupling_cn.pdf'
HTML(string=html_doc).write_pdf(output_path)
print(f'OK: {output_path}')
