#!/usr/bin/env python3
"""combined(교수자용) + combined_student(학생용: 모범답안 박스 제거) 생성, 표지 메타데이터 보강"""
import re, glob, os

SRC = "/home/claude/book/src"

def convert_footnotes(text, cid):
    m = re.search(r"^### 각주\s*$", text, flags=re.M)
    if not m:
        return text
    body, notes_block = text[:m.start()], text[m.end():]
    defs = {}
    for line in notes_block.splitlines():
        mm = re.match(r"^\[(\d+)\]\s+(.*)$", line.strip())
        if mm:
            defs[mm.group(1)] = mm.group(2)
    body = re.sub(r"\[(\d+)\]",
                  lambda mo: f"[^{cid}_{mo.group(1)}]" if mo.group(1) in defs else mo.group(0),
                  body)
    footdefs = "\n".join(f"[^{cid}_{n}]: {t}" for n, t in defs.items())
    return body.rstrip() + "\n\n" + footdefs + "\n"

def strip_answer_boxes(text):
    """'> **💬 모범 답안' 으로 시작하는 연속 blockquote 블록 제거"""
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        if lines[i].lstrip().startswith(">") and "💬 모범 답안" in lines[i]:
            while i < len(lines) and (lines[i].lstrip().startswith(">") or lines[i].strip() == ""):
                # 빈 줄 뒤에 blockquote가 이어지면 같은 블록
                if lines[i].strip() == "":
                    j = i + 1
                    if j < len(lines) and lines[j].lstrip().startswith(">"):
                        i += 1
                        continue
                    break
                i += 1
        else:
            out.append(lines[i])
            i += 1
    return "\n".join(out)

def student_adjust(text, stem):
    if stem == "00_front":
        text = text.replace(
            "- **💬 모범 답안**: 토론 질문·심화 토론 항목에는 모범 답안(예시 답안)을 음영 박스로 제공한다. 모범 답안은 '정답'이 아니라 논증의 예시이며, 수업에서는 이를 넘어서는 답을 기대한다. **박스를 읽기 전에 반드시 스스로 답을 구성해 볼 것.**",
            "- **💬 모범 답안**: 토론 질문·심화 토론 항목의 모범 답안(예시 답안)은 이 책 맨 뒤의 부록 「토론 쟁점 해설」에 모아 두었다. 모범 답안은 '정답'이 아니라 논증의 예시이며, 수업에서는 이를 넘어서는 답을 기대한다. **부록을 읽기 전에 반드시 스스로 답을 구성해 볼 것.**")
    if stem == "08":
        text = text.replace(
            "시험 대비는 각 장의 '발표 문헌 요약'과 '토론 질문'의 모범 답안 박스를 복습 자료로 활용하라.",
            "시험 대비는 각 장의 '발표 문헌 요약'과 '토론 질문'을 복습 자료로 활용하라.")
    return text

HEADER_TMPL = """---
title: "기록정보서비스론 강의교재"
subtitle: "Archival Reference & Access Services · 2026학년도 2학기{edition}"
author: "안대진 — 서울대학교 인문대학 협동과정 기록학전공"
date: "2026년 9월"
lang: ko
toc-title: "목차"
abstract-title: "강좌 안내"
abstract: |
  대학원 「기록정보서비스론」 주차별 강의(15주)에 대응하는 교재로, 이론(1~7장)·중간 종합(8장)·디지털/데이터/AI(9~13장)·아웃리치와 평가(14~15장)로 구성된다.
  주교재: Oestreicher(2020); 한국기록관리학회 편(2018). 부교재: Pugh(2005); Ramsey 외 편(2009); Roe(2019).
  수업방식: 이론 강의 + 문헌 발표·토론 + 바이브 코딩 실습 / 평가: 출석 30·과제 30·기말 40.
---

"""

files = sorted(glob.glob(os.path.join(SRC, "*.md")))
assert len(files) == 16

for edition, outpath, strip in [
    (" · 교수자용(모범 답안 수록)", "/home/claude/book/combined.md", False),
    (" · 학생용", "/home/claude/book/combined_student.md", True),
]:
    parts = []
    for f in files:
        stem = os.path.splitext(os.path.basename(f))[0]
        text = open(f, encoding="utf-8").read()
        if strip:
            text = student_adjust(strip_answer_boxes(text), stem)
        parts.append(convert_footnotes(text, "c" + stem[:2]))
    if strip:
        app = open("/home/claude/book/appendix/appendix.md", encoding="utf-8").read().strip()
        parts.append("# 부록. 토론 쟁점 해설\n\n" + app + "\n")
    with open(outpath, "w", encoding="utf-8") as fh:
        fh.write(HEADER_TMPL.format(edition=edition) + "\n\n".join(parts))
    boxes = open(outpath, encoding="utf-8").read().count("💬 모범 답안")
    print(f"{outpath}: {os.path.getsize(outpath)} bytes, 모범답안 표기 {boxes}회")

# 학생용 Wikidocs 세트
WIKI_S = "/home/claude/book/wikidocs_student"
os.makedirs(WIKI_S, exist_ok=True)
import shutil
titles = {os.path.splitext(os.path.basename(f))[0]: None for f in files}
for f in files:
    stem = os.path.splitext(os.path.basename(f))[0]
    text = student_adjust(strip_answer_boxes(open(f, encoding="utf-8").read()), stem)
    # wikidocs 파일명은 기존 세트와 동일 규칙
    src_wiki = sorted(glob.glob("/home/claude/book/wikidocs/*.md"))
    name = [os.path.basename(p) for p in src_wiki if p.split("/")[-1].startswith(stem[:2])]
    fname = name[0] if name else stem + ".md"
    open(os.path.join(WIKI_S, fname), "w", encoding="utf-8").write(text)
print("wikidocs_student:", len(os.listdir(WIKI_S)), "files")
