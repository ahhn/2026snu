#!/usr/bin/env python3
"""usage: build_book.py {student|instructor}
1차 빌드로 페이지 매김을 얻고 색인을 만든 뒤 2차 빌드로 최종 docx/pdf 산출."""
import re, glob, os, sys, json, subprocess, time
sys.path.insert(0, "/home/claude/book")
_src = open('/home/claude/book/build2.py', encoding='utf-8').read().split('HEADER_TMPL')[0]
exec(_src)  # convert_footnotes, strip_answer_boxes, student_adjust

B = "/home/claude/book"
SRC, BACK = f"{B}/src", f"{B}/back"
kind = sys.argv[1]
public = kind == "public"          # 공개본: 학생용에서 부록 A(모범 답안)를 뺀 판
student = kind in ("student", "public")
edition_short = "학생용" if student else "교수자용 · 모범 답안 수록"
edition_sub = "" if student else "교수자용(모범 답안 수록)"
tag = "공개용" if public else ("학생용" if student else "교수자용")

HEADER = f"""---
title: "기록정보서비스론"
subtitle: "{edition_sub}"
author:
  - "서울대학교 인문대학 협동과정 기록학전공"
  - "저자: 안대진"
date: "2026년 9월"
lang: ko
toc-title: "목차"
abstract-title: "강좌 안내"
abstract: |
  대학원 「기록정보서비스론」 주차별 강의(15주)에 대응하는 교재로, 이론(1~7장)·중간 종합(8장)·디지털/데이터/AI(9~13장)·아웃리치와 평가(14~15장)로 구성된다.
  주교재: 안대진(2026). 부교재: Pugh(2005); Ramsey 외 편(2009); Roe(2019).
  수업방식: 이론 강의 + 문헌 발표·토론 + 바이브 코딩 실습.
---

"""

files = sorted(glob.glob(f"{SRC}/*.md")); assert len(files) == 16
terms = json.load(open(f"{BACK}/index_terms.json", encoding="utf-8"))

PAGEBREAK = '```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n'

def add_intro(t):
    """장 제목에서 (N주) 제거 + 인트로 페이지(장 제목·절 제목 목록) 삽입"""
    m = re.match(r"^# (.+)\n", t)
    if not m: return t
    title = re.sub(r"\s*\(\d+주\)\s*$", "", m.group(1).strip())
    body = t[m.end():]
    secs = [re.sub(r"\s*\(.*?\)\s*$", "", s.strip()) for s in re.findall(r"^## (.+)$", body, flags=re.M)]
    return f"# {title}\n{body}"

def body_parts():
    parts = []
    for f in files:
        stem = os.path.splitext(os.path.basename(f))[0]
        t = open(f, encoding="utf-8").read()
        if student:
            t = student_adjust(strip_answer_boxes(t), stem)
        if public and stem == "00_front":
            t = t.replace("이 책 맨 뒤의 부록 「토론 쟁점 해설」에 모아 두었다.",
                          "부록 「토론 쟁점 해설」로 묶어 학기 종료(2026년 12월) 후 공개한다. 이 판에는 부록 A가 실려 있지 않다.")
        if stem != "00_front":
            t = add_intro(t)
        parts.append(convert_footnotes(t, "c" + stem[:2]))
    if student and not public:
        app = open(f"{B}/appendix/appendix.md", encoding="utf-8").read().strip()
        parts.append("# 부록. 토론 쟁점 해설\n\n" + app + "\n")
    parts.append(open(f"{BACK}/serendipity.md", encoding="utf-8").read().strip() + "\n")
    parts.append(open(f"{BACK}/bibliography.md", encoding="utf-8").read().strip() + "\n")
    return parts

def colophon():
    return open(f"{BACK}/colophon.md", encoding="utf-8").read().strip() + "\n"

def chosung(ch):
    code = ord(ch) - 0xAC00
    if code < 0: return ch
    return "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"[code // 588]
MERGE = {"ㄲ": "ㄱ", "ㄸ": "ㄷ", "ㅃ": "ㅂ", "ㅆ": "ㅅ", "ㅉ": "ㅈ"}

def make_index_md(pages_of):
    """pages_of: term -> [page numbers]"""
    out = ["# 색인\n"]
    def group(items, keyf):
        groups = {}
        for term, pages in items:
            if not pages: continue
            groups.setdefault(keyf(term), []).append((term, pages))
        return groups
    ko = group(sorted(((t, pages_of.get(t, [])) for t in terms["ko"]), key=lambda x: x[0]),
               lambda t: MERGE.get(chosung(t[0]), chosung(t[0])))
    en = group(sorted(((t, pages_of.get(t, [])) for t in terms["en"]), key=lambda x: x[0].lower()),
               lambda t: t[0].upper())
    for label, groups in (("한글", ko), ("영문·인명", en)):
        out.append(f"## {label}\n")
        for g in sorted(groups):
            out.append(f'::: {{custom-style="IndexGroup"}}\n{g}\n:::\n')
            for term, pages in groups[g]:
                out.append(f'::: {{custom-style="IndexEntry"}}\n{term}  ···  {", ".join(str(p) for p in pages)}\n:::\n')
    return "\n".join(out)

def build(parts, out_docx, out_pdf):
    md = f"{B}/combined_{tag}.md"
    open(md, "w", encoding="utf-8").write(HEADER + "\n\n".join(parts))
    raw = f"{B}/raw_{tag}.docx"; pp = f"{B}/pp_{tag}.docx"
    subprocess.run(["pandoc", md, "-o", raw, "--reference-doc", f"{B}/reference_book.docx", "--toc", "--toc-depth=2",
                    "--resource-path", B, "-f", "markdown+footnotes+pipe_tables+fenced_code_blocks+line_blocks+raw_attribute"], check=True)
    subprocess.run(["python3", f"{B}/postprocess.py", raw, pp, edition_short], check=True)
    subprocess.run(["python3", f"{B}/finalize_uno2.py", pp, out_docx, out_pdf, edition_short], check=True)

def page_texts(pdf):
    t = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True).stdout
    return t.split("\f")

# ---- 1차 빌드 (색인 자리만 예약)
parts = body_parts()
parts_pass1 = parts + ["# 색인\n\n(생성 중)\n", colophon(), open(f"{BACK}/author.md", encoding="utf-8").read()]
p1_docx, p1_pdf = f"{B}/pass1_{tag}.docx", f"{B}/pdf/pass1_{tag}.pdf"
build(parts_pass1, p1_docx, p1_pdf)

# ---- 색인 생성: 본문(1장 시작 ~ 참고문헌 직전) 페이지만
pages = page_texts(p1_pdf)
def find_page(pattern, start=0):
    for i in range(start, len(pages)):
        if re.search(pattern, pages[i]): return i
    return None
toc = find_page(r"1\.1\s+기록정보서비스의\s+개념") or 2
first = find_page(r"1\.1\s+기록정보서비스의\s+개념", toc + 1) or 8
bib = find_page(r"^\s*참고문헌\s*$", first + 5) or len(pages)
pages_of = {}
for grp in ("ko", "en"):
    for term, pat in terms[grp].items():
        rx = re.compile(pat)
        hits = [i + 1 for i in range(first, bib) if rx.search(pages[i])]
        pages_of[term] = hits[:14]  # 과다 인용 억제
index_md = make_index_md(pages_of)
open(f"{BACK}/index_{tag}.md", "w", encoding="utf-8").write(index_md)
print(f"[{tag}] 본문 {first+1}~{bib}쪽, 색인어 {sum(1 for v in pages_of.values() if v)}개")

# ---- 2차 빌드
parts_final = parts + [index_md, colophon(), open(f"{BACK}/author.md", encoding="utf-8").read()]
out_docx, out_pdf = f"{B}/final_{tag}.docx", f"{B}/pdf/final_{tag}.pdf"
build(parts_final, out_docx, out_pdf)
print("FINAL", out_docx, out_pdf)
