#!/usr/bin/env python3
"""Convert Chinese markdown with LaTeX math to PDF using matplotlib + weasyprint."""
import re, os, hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from weasyprint import HTML

INPUT = '/home/duyw/physcausal/reports/paper_spin_em_coupling_cn.md'
OUTPUT = '/home/duyw/physcausal/reports/paper_spin_em_coupling_cn.pdf'
IMG_DIR = '/tmp/math_pngs'
os.makedirs(IMG_DIR, exist_ok=True)

with open(INPUT) as f:
    md_text = f.read()

def render_latex(latex, is_display=True):
    """Render LaTeX to PNG using matplotlib mathtext."""
    h = hashlib.md5(latex.encode()).hexdigest()[:12]
    fname = f'eq_{h}.png'
    fpath = os.path.join(IMG_DIR, fname)
    
    if os.path.exists(fpath):
        return fpath
    
    fig, ax = plt.subplots(figsize=(6, 0.6) if is_display else (3, 0.5))
    ax.axis('off')
    try:
        ax.text(0.5, 0.5, f'${latex}$', transform=ax.transAxes,
                fontsize=14 if is_display else 11,
                ha='center', va='center')
    except:
        # Fallback: just show raw LaTeX
        ax.text(0.5, 0.5, latex, transform=ax.transAxes,
                fontsize=11, ha='center', va='center', family='monospace')
    
    fig.savefig(fpath, dpi=150, bbox_inches='tight', pad_inches=0.1,
                facecolor='white', edgecolor='none')
    plt.close(fig)
    return fpath

# Replace display math $$...$$ with images
def replace_display(m):
    latex = m.group(1).strip()
    path = render_latex(latex, is_display=True)
    return f'<p align="center"><img src="file://{path}" alt="{latex}" style="max-width:100%"></p>'

md_text = re.sub(r'\$\$\s*(.+?)\s*\$\$', replace_display, md_text, flags=re.DOTALL)

# Replace inline math $...$ with images
def replace_inline(m):
    latex = m.group(1).strip()
    path = render_latex(latex, is_display=False)
    return f' <img src="file://{path}" alt="{latex}" style="vertical-align:middle;max-height:1.2em"> '

md_text = re.sub(r'\$(.+?)\$', replace_inline, md_text)

# Convert markdown to HTML
import markdown
html_body = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])

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
  code {{ background: #f5f5f5; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }}
  pre {{ background: #f5f5f5; padding: 8pt; border-radius: 4px; font-size: 9pt; overflow-x: auto; }}
  pre code {{ background: none; padding: 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10pt 0; }}
  th, td {{ border: 1px solid #ccc; padding: 4pt 8pt; text-align: left; }}
  th {{ background: #eee; }}
</style>
</head>
<body>
{html_body}
</body>
</html>'''

HTML(string=html_doc).write_pdf(OUTPUT)
print(f'OK: {OUTPUT}')
