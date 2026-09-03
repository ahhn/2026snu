#!/usr/bin/env python3
"""위키독스용 스타일 변환. 순수 마크다운을 받아 인쇄본과 같은 시각 언어의 HTML을 섞어 돌려준다.
정본은 src/*.md이며 이 변환은 출력 단계에서만 적용된다."""
import re

GREEN, NAVY, TERRA, TAN, CREAM, GRAY = "#1F4A3A", "#1F3557", "#C8582F", "#C9B58F", "#F7F3EC", "#5C6670"

def chapter_head(label, title, sub=""):
    out = (f'<div style="border-bottom:3px solid {TERRA};padding-bottom:10px;margin:4px 0 24px;">'
           f'<div style="font-size:0.8em;letter-spacing:3px;color:{TERRA};font-weight:700;">{label}</div>'
           f'<div style="font-size:1.6em;font-weight:700;color:{GREEN};line-height:1.35;">{title}</div>')
    if sub:
        out += f'<div style="font-size:0.95em;color:{GRAY};margin-top:6px;">{sub}</div>'
    return out + '</div>\n'

def section(num, title):
    label = f"{num} {title}".strip()
    return (f'<div style="border-left:5px solid {TERRA};padding-left:12px;margin:32px 0 12px;">'
            f'<span style="font-size:1.22em;font-weight:700;color:{NAVY};">{label}</span></div>\n')

def subsection(title):
    return (f'<div style="margin:24px 0 8px;padding-bottom:4px;border-bottom:1px solid {TAN};'
            f'font-size:1.05em;font-weight:700;color:{GREEN};">{title}</div>\n')

def callout(inner):
    return (f'<div style="background:{CREAM};border-left:5px solid {GREEN};border-radius:3px;'
            f'padding:12px 16px;margin:16px 0;line-height:1.85;">{inner}</div>\n')

def _split_front(text):
    """맨 앞 H1(장 제목) 분리."""
    m = re.match(r"^#\s+(.+?)\s*$", text, flags=re.M)
    if m and m.start() == 0:
        return m.group(1).strip(), text[m.end():].lstrip("\n")
    return None, text

def stylize(text, chapter_no=None, title=None, subtitle="", label=None):
    """chapter_no: 1~15. label을 주면 그 문구를 상단 라벨로 쓴다(부록 등)."""
    body = text
    if label is None:
        label = f"CHAPTER {chapter_no}" if chapter_no else "서문"
    head = chapter_head(label, title, subtitle) if title else ""

    # 절 제목: '## 1.1 제목' / '## 발표 문헌 요약' 등
    def _sec(m):
        raw = m.group(1).strip()
        mm = re.match(r"^(\d+\.\d+)\s+(.+)$", raw)
        return section(mm.group(1), mm.group(2)) if mm else section("", raw)
    body = re.sub(r"^##\s+(.+?)\s*$", _sec, body, flags=re.M)
    # 남은 1단계 헤딩(서문의 '일러두기', '교재·부교재' 등)도 절 제목으로
    body = re.sub(r"^#\s+(.+?)\s*$", lambda m: section("", m.group(1).strip()), body, flags=re.M)
    # 소제목
    body = re.sub(r"^###\s+(.+?)\s*$", lambda m: subsection(m.group(1).strip()), body, flags=re.M)

    # 인용 블록 → 크림 박스 (연속 줄 묶음)
    lines, out, i = body.splitlines(), [], 0
    while i < len(lines):
        if lines[i].lstrip().startswith("> "):
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append(callout("<br>".join(b for b in buf if b.strip())))
        else:
            out.append(lines[i]); i += 1
    body = "\n".join(out)

    # 논문 요약 토글 카드
    body = body.replace("<details>\n<summary>",
        f'<details style="background:#FFFFFF;border:1px solid {TAN};border-radius:4px;'
        f'padding:10px 14px;margin:14px 0;"><summary style="cursor:pointer;font-weight:700;color:{GREEN};">')
    body = body.replace("</summary>", "</summary>\n<div style=\"margin-top:10px;line-height:1.85;\">")
    body = body.replace("</details>", "</div></details>")

    # 표 머리행 강조는 위키독스 기본 테마를 따르므로 생략(가독성 우선)
    return head + body.strip() + "\n"
