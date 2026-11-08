#!/usr/bin/env python3
"""부록 A 「토론 쟁점 해설」을 원고(src/*.md)에서 생성한다.

부록 A는 각 장에 흩어진 '💬 모범 답안' 상자를 한곳에 모은 파생 문서다.
학생용 빌드는 본문에서 상자를 떼어 내고(strip_answer_boxes) 그 내용을 이 부록으로 보낸다.
원고가 유일한 출처이므로 부록 파일 자체는 저장소에 두지 않고 빌드 때마다 다시 만든다.

usage: python3 build/make_appendix.py [출력경로]   (기본값: appendix/appendix.md)
"""
import re, os, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))
# 저장소에서는 build/ 안에, 빌드 루트에서는 src/ 와 나란히 놓인다. 둘 다 받아 준다.
ROOT = HERE if os.path.isdir(os.path.join(HERE, "src")) else os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "appendix", "appendix.md")

INTRO = ("이 부록은 각 장 토론 질문과 중간시험의 모범 답안(예시 답안)을 모아 정리한 것이다. "
         "실습 결과물의 예시는 각 장 본문의 「실습 가이드」에 실었다. "
         "모범 답안은 '정답'이 아니라 논증의 예시이며, 스스로 답을 구성해 본 뒤 참고하는 것을 권한다.")

BOX = re.compile(r"^>\s*\*\*💬\s*모범\s*답안(?::\s*(?P<label>[^*]+?))?\*\*\s*(?:—\s*)?(?P<rest>.*)$")
QLINE = re.compile(r"^\*\*(?P<q>Q\d+\.[^\n]*?)\*\*\s*$")


def blocks(path):
    """(제목, 본문) 목록을 등장 순서대로 돌려준다."""
    lines = open(path, encoding="utf-8").read().splitlines()
    out, last_q, i = [], None, 0
    while i < len(lines):
        mq = QLINE.match(lines[i].strip())
        if mq:
            last_q = mq.group("q").strip()
            i += 1
            continue
        m = BOX.match(lines[i].strip())
        if not m:
            i += 1
            continue
        body = [m.group("rest").strip()]
        i += 1
        # 이어지는 blockquote 줄(사이의 빈 줄 포함)을 같은 상자로 본다
        while i < len(lines):
            s = lines[i].strip()
            if s.startswith(">"):
                body.append(re.sub(r"^>\s?", "", s))
                i += 1
            elif s == "" and i + 1 < len(lines) and lines[i + 1].strip().startswith(">"):
                body.append("")
                i += 1
            else:
                break
        label = (m.group("label") or "").strip()
        title = last_q if (last_q and not label) else (label or "모범 답안")
        out.append((title, "\n".join(body).strip()))
        last_q = None
    return out


def main():
    parts = [INTRO, ""]
    total = 0
    for f in sorted(glob.glob(os.path.join(SRC, "*.md"))):
        stem = os.path.basename(f)
        if stem == "00_front.md":
            continue
        bs = blocks(f)
        if not bs:
            continue
        head = open(f, encoding="utf-8").readline().strip().lstrip("# ")
        head = re.sub(r"\s*\(\d+주\)\s*$", "", head)
        parts.append(f"## {head}")
        parts.append("")
        for title, body in bs:
            parts.append(f"### {title}")
            parts.append("")
            parts.append(body)
            parts.append("")
            total += 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(parts).rstrip() + "\n")
    print(f"{OUT}: 해설 {total}개, {len(open(OUT, encoding='utf-8').read())}자")


if __name__ == "__main__":
    main()
