#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_docs.py - 文档构建脚本
将 /home/skyfend/ptz100_agx_code/github/doc 中的 Markdown 文件
转换为 HTML 并生成文档目录索引

用法:
    python3 tools/build_docs.py
"""

import os
import re
import json
import sys
from pathlib import Path

# ========================================
# Configuration
# ========================================
DOC_SOURCE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
WEB_TARGET = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DOCS_DIR = os.path.join(WEB_TARGET, "docs")
CATALOG_FILE = os.path.join(WEB_TARGET, "js", "doc-catalog.js")

# Category display configuration
CATEGORIES = {
    "1-通信协议": {"label": "通信协议", "icon": "network", "desc": "Alink、雷达、激光、PTZ等设备通信协议"},
    "2-软件资料": {"label": "软件资料", "icon": "code", "desc": "架构分析、模块设计、部署指南"},
    "3-硬件资料": {"label": "硬件资料", "icon": "chip", "desc": "产品规格、硬件说明"},
    "4-生产烧录": {"label": "生产烧录", "icon": "drive", "desc": "系统镜像、批量烧录"},
    "5-调试工具": {"label": "调试工具", "icon": "wrench", "desc": "调试与诊断工具"},
    "6-实验报告": {"label": "实验报告", "icon": "flask", "desc": "问题排查与优化分析报告"},
}

# Featured documents - relative paths from DOC_SOURCE
FEATURED = [
    "2-软件资料/软件模块设计说明/PTZ100_AGX架构分析文档.md",
    "2-软件资料/软件模块设计说明/PTZ100_AGX通信链路分析.md",
    "2-软件资料/软件模块设计说明/NexusGateway_开发方案.md",
    "6-实验报告/SpotterPro_天盾断流_CLOSE-WAIT_排查修复总结.md",
    "6-实验报告/hepu/和普clientTrack跟踪抖动问题分析与修复总结.md",
]

# File format detection
FORMAT_MAP = {
    '.md': 'md',
    '.pdf': 'pdf',
    '.docx': 'docx',
    '.doc': 'doc',
    '.txt': 'txt',
    '.xlsx': 'xlsx',
    '.xls': 'xls',
    '.pptx': 'pptx',
    '.ppt': 'ppt',
}

# Directories to skip
SKIP_DIRS = {'.git', '__pycache__', '.idea', '.vscode', 'web'}

# ========================================
# Markdown to HTML converter
# ========================================

def simple_md_to_html(md_text):
    """Simple markdown to HTML converter (no external dependencies)"""
    lines = md_text.split('\n')
    html_lines = []
    in_code_block = False
    in_list = False
    list_type = None

    for line in lines:
        # Code blocks
        if line.strip().startswith('```'):
            if not in_code_block:
                in_code_block = True
                lang = line.strip()[3:].strip()
                html_lines.append('<pre><code>')
            else:
                in_code_block = False
                html_lines.append('</code></pre>')
            continue

        if in_code_block:
            html_lines.append(escape_html(line))
            continue

        # Close list if needed
        if in_list and not line.strip().startswith(('- ', '* ', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
            if not line.strip() == '':
                if list_type == 'ul':
                    html_lines.append('</ul>')
                else:
                    html_lines.append('</ol>')
                in_list = False

        # Empty line
        if line.strip() == '':
            html_lines.append('')
            continue

        # Headings
        if line.startswith('######'):
            html_lines.append('<h6>' + inline_format(line[6:].strip()) + '</h6>')
        elif line.startswith('#####'):
            html_lines.append('<h5>' + inline_format(line[5:].strip()) + '</h5>')
        elif line.startswith('####'):
            html_lines.append('<h4>' + inline_format(line[4:].strip()) + '</h4>')
        elif line.startswith('###'):
            html_lines.append('<h3>' + inline_format(line[3:].strip()) + '</h3>')
        elif line.startswith('##'):
            html_lines.append('<h2>' + inline_format(line[2:].strip()) + '</h2>')
        elif line.startswith('#'):
            html_lines.append('<h1>' + inline_format(line[1:].strip()) + '</h1>')
        # Horizontal rule
        elif re.match(r'^[-*_]{3,}\s*$', line.strip()):
            html_lines.append('<hr>')
        # Blockquote
        elif line.startswith('>'):
            content = line.lstrip('>').strip()
            html_lines.append('<blockquote><p>' + inline_format(content) + '</p></blockquote>')
        # Unordered list
        elif line.strip().startswith(('- ', '* ')):
            if not in_list or list_type != 'ul':
                if in_list:
                    html_lines.append('</ol>' if list_type == 'ol' else '</ul>')
                html_lines.append('<ul>')
                in_list = True
                list_type = 'ul'
            content = re.sub(r'^[\s]*[-*]\s+', '', line)
            html_lines.append('<li>' + inline_format(content) + '</li>')
        # Ordered list
        elif re.match(r'^[\s]*\d+\.\s', line):
            if not in_list or list_type != 'ol':
                if in_list:
                    html_lines.append('</ul>' if list_type == 'ul' else '</ol>')
                html_lines.append('<ol>')
                in_list = True
                list_type = 'ol'
            content = re.sub(r'^[\s]*\d+\.\s+', '', line)
            html_lines.append('<li>' + inline_format(content) + '</li>')
        # Table row
        elif '|' in line and line.strip().startswith('|'):
            # Simple table handling
            cells = [c.strip() for c in line.strip().split('|')[1:-1]]
            # Skip separator rows
            if all(re.match(r'^[-:]+$', c) for c in cells):
                continue
            row = '<tr>' + ''.join('<td>' + inline_format(c) + '</td>' for c in cells) + '</tr>'
            html_lines.append(row)
        # Paragraph
        else:
            html_lines.append('<p>' + inline_format(line) + '</p>')

    # Close any remaining list
    if in_list:
        html_lines.append('</ul>' if list_type == 'ul' else '</ol>')

    return '\n'.join(html_lines)


def inline_format(text):
    """Apply inline formatting: bold, italic, code, links"""
    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Bold
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__([^_]+)__', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
    text = re.sub(r'_([^_]+)_', r'<em>\1</em>', text)
    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    # Images
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', text)
    return text


def escape_html(text):
    """Escape HTML special characters"""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    return text


def wrap_in_template(title, body):
    """Wrap HTML body in a standalone template for iframe"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)}</title>
    <link rel="stylesheet" href="../../css/markdown.css">
</head>
<body>
    <article class="markdown-body">{body}</article>
    <script>
        // Sync theme with parent page
        try {{
            var parentTheme = window.parent.document.documentElement.getAttribute('data-theme');
            if (parentTheme) document.documentElement.setAttribute('data-theme', parentTheme);
            // Listen for theme changes
            var observer = new MutationObserver(function(mutations) {{
                mutations.forEach(function(m) {{
                    if (m.attributeName === 'data-theme') {{
                        var t = window.parent.document.documentElement.getAttribute('data-theme');
                        if (t) document.documentElement.setAttribute('data-theme', t);
                    }}
                }});
            }});
            observer.observe(window.parent.document.documentElement, {{ attributes: true }});
        }} catch(e) {{}}
    </script>
</body>
</html>"""


def extract_summary(md_content, max_length=150):
    """Extract first meaningful paragraph as summary"""
    lines = md_content.strip().split('\n')
    past_heading = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            past_heading = True
            continue
        if past_heading and stripped and not stripped.startswith('#') and not stripped.startswith('>') and not stripped.startswith('```') and not stripped.startswith('|') and not stripped.startswith('---'):
            # Clean markdown formatting
            clean = re.sub(r'[#*`\[\]()>_]', '', stripped).strip()
            if len(clean) > 10:
                return clean[:max_length] + ('...' if len(clean) > max_length else '')
    # Fallback: first non-empty, non-heading line
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('```') and len(stripped) > 5:
            clean = re.sub(r'[#*`\[\]()>_]', '', stripped).strip()
            return clean[:max_length] + ('...' if len(clean) > max_length else '')
    return ""


def extract_title(md_content, filename):
    """Extract title from first heading, fallback to filename"""
    for line in md_content.split('\n'):
        if line.startswith('#'):
            return re.sub(r'^#+\s*', '', line).strip()
    # Clean filename for title
    name = os.path.splitext(os.path.basename(filename))[0]
    return name


# ========================================
# Document Processing
# ========================================

def process_directory(dir_path, rel_prefix):
    """Process a directory and return documents and sub-categories"""
    documents = []
    sub_categories = []

    try:
        entries = sorted(os.listdir(dir_path))
    except PermissionError:
        return documents, sub_categories

    # Collect direct files and subdirectories
    direct_files = []
    subdirs = []

    for entry in entries:
        if entry.startswith('.') or entry in SKIP_DIRS:
            continue
        full_path = os.path.join(dir_path, entry)
        if os.path.isdir(full_path):
            subdirs.append(entry)
        else:
            direct_files.append(entry)

    # Process direct files
    for filename in direct_files:
        ext = os.path.splitext(filename)[1].lower()
        fmt = FORMAT_MAP.get(ext, 'unknown')
        rel_path = os.path.join(rel_prefix, filename)

        doc_entry = {
            "title": os.path.splitext(filename)[0],
            "format": fmt,
            "file": None,
            "originalPath": rel_path,
            "summary": "",
            "featured": rel_path in FEATURED
        }

        if fmt == 'md':
            full_path = os.path.join(dir_path, filename)
            try:
                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                doc_entry["title"] = extract_title(content, filename)
                doc_entry["summary"] = extract_summary(content)

                # Convert and save HTML
                html_body = convert_md(content)
                html_full = wrap_in_template(doc_entry["title"], html_body)

                # Compute output path
                out_rel = os.path.join(rel_prefix, filename.replace('.md', '.html'))
                out_path = os.path.join(DOCS_DIR, out_rel)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(html_full)

                doc_entry["file"] = "docs/" + out_rel
                print(f"  ✓ {rel_path}")
            except Exception as e:
                print(f"  ✗ {rel_path}: {e}")
        else:
            print(f"  ○ {rel_path} ({fmt})")

        documents.append(doc_entry)

    # Process subdirectories as sub-categories
    for subdir in subdirs:
        sub_path = os.path.join(dir_path, subdir)
        sub_rel = os.path.join(rel_prefix, subdir)

        sub_docs, sub_subs = process_directory(sub_path, sub_rel)

        if sub_docs or sub_subs:
            sub_cat = {
                "name": subdir,
                "label": subdir,
                "documents": sub_docs,
                "subCategories": sub_subs
            }
            sub_categories.append(sub_cat)

    return documents, sub_categories


def build_catalog():
    """Walk doc directory, convert documents, build catalog"""
    catalog = []

    if not os.path.isdir(DOC_SOURCE):
        print(f"Error: Source directory not found: {DOC_SOURCE}")
        return catalog

    print(f"Source: {DOC_SOURCE}")
    print(f"Target: {DOCS_DIR}")
    print(f"{'='*50}")

    for cat_dir in sorted(os.listdir(DOC_SOURCE)):
        cat_path = os.path.join(DOC_SOURCE, cat_dir)
        if not os.path.isdir(cat_path) or cat_dir.startswith('.') or cat_dir in SKIP_DIRS:
            continue

        cat_info = CATEGORIES.get(cat_dir, {"label": cat_dir, "icon": "folder", "desc": ""})
        print(f"\n📂 {cat_info['label']} ({cat_dir})")

        documents, sub_categories = process_directory(cat_path, cat_dir)

        cat_entry = {
            "category": cat_dir,
            "label": cat_info["label"],
            "icon": cat_info["icon"],
            "description": cat_info["desc"],
            "documents": documents,
            "subCategories": sub_categories
        }
        catalog.append(cat_entry)

    return catalog


def generate_catalog_js(catalog):
    """Write catalog as a JavaScript file"""
    js_content = f"""/**
 * doc-catalog.js - 文档目录索引数据
 * 由 tools/build_docs.py 自动生成
 * 生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 */
var DOC_CATALOG = {json.dumps(catalog, ensure_ascii=False, indent=2)};
"""
    with open(CATALOG_FILE, 'w', encoding='utf-8') as f:
        f.write(js_content)
    print(f"\n{'='*50}")
    print(f"✓ Catalog generated: {CATALOG_FILE}")
    print(f"✓ Total categories: {len(catalog)}")

    # Count stats
    total_docs = 0
    md_docs = 0
    for cat in catalog:
        total_docs += len(cat.get('documents', []))
        md_docs += sum(1 for d in cat.get('documents', []) if d.get('format') == 'md')
        for sub in cat.get('subCategories', []):
            total_docs += len(sub.get('documents', []))
            md_docs += sum(1 for d in sub.get('documents', []) if d.get('format') == 'md')
    print(f"✓ Total documents: {total_docs} (Markdown: {md_docs}, Other: {total_docs - md_docs})")


def convert_md(md_text):
    """Convert markdown to HTML, preferring the markdown library if available"""
    try:
        import markdown as _md
        return _md.markdown(md_text, extensions=[
            'tables', 'fenced_code', 'toc', 'nl2br', 'sane_lists'
        ])
    except ImportError:
        return simple_md_to_html(md_text)


# ========================================
# Main
# ========================================

if __name__ == "__main__":
    print("PTZ100 AGX Document Builder")
    print("=" * 50)

    # Ensure output directory exists
    os.makedirs(DOCS_DIR, exist_ok=True)

    # Try to use markdown library for better conversion
    import markdown as _md_lib
    _use_md_lib = True
    print("✓ Using 'markdown' library for conversion")

    catalog = build_catalog()
    generate_catalog_js(catalog)
    print("\nDone! Open index.html in your browser to view.")
