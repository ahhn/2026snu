#!/usr/bin/env python3
"""부록 A 「토론 쟁점 해설」을 원고(src/*.md)에서 생성한다.

부록 A는 각 장에 흩어진 '💬 모범 답안' 상자를 한곳에 모은 파생 문서다.
학생용 빌드는 본문에서 상자를 떼어 내고(strip_answer_boxes) 그 내용을 이 부록으로 보낸다.
원고가 유일한 출처이므로 부록 파일 자체는 저장소에 두지 않고 빌드할 때마다 다시 만든다.

상자를 뽑는 규칙은 sync_wikidocs.py의 extract_boxes 하나뿐이다. 위키독스 부록 A 페이지와
인쇄본 부록 A가 어긋나지 않도록, 여기서는 그 함수를 그대로 가져다 쓴다(망 접속은 하지 않는다).

usage: python3 build/make_appendix.py [출력경로]   (기본값: <루트>/appendix/appendix.md)
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


def load_extract_boxes():
    """sync_wikidocs.py에서 extract_boxes만 가져온다. 모듈 최상단의 네트워크 코드는 실행하지 않는다."""
    path = os.path.join(HERE, "sync_wikidocs.py")
    src = open(path, encoding="utf-8").read()
    head = src.split("files = sorted(")[0]          # 페이지 전송 루프 직전까지
    head = re.sub(r"^TOKEN\s*=.*$", 'TOKEN = ""', head, flags=re.M)
    ns = {}
    exec(compile(head, path, "exec"), ns)
    return ns["extract_boxes"]


def main():
    extract_boxes = load_extract_boxes()
    parts, total = [INTRO, ""], 0
    for f in sorted(glob.glob(os.path.join(SRC, "*.md"))):
        raw = open(f, encoding="utf-8").read()
        m = re.match(r"^# (.+)\n", raw)
        title = m.group(1).strip() if m else ""
        body = raw[m.end():] if m else raw
        boxes = extract_boxes(body)
        if not boxes:
            continue
        parts.append(f"## {re.sub(r'\\s*\\(\\d+주\\)$', '', title)}\n")
        for label, content in boxes:
            parts.append(f"### {label}\n\n{content}\n")
            total += 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(parts))
    print(f"{OUT}: 해설 {total}개, {os.path.getsize(OUT)}바이트")


if __name__ == "__main__":
    main()
