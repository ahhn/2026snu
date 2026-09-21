#!/usr/bin/env python3
"""src/*.md(최신) → 위키독스 학생용 16페이지 + 부록(토론 쟁점 해설) 동기화.
규칙: H1 제목 줄 제거, 헤딩 한 단계 낮춤(## → ###), 각주 [n] → [^cNNnN], 모범답안 박스 제거(부록으로 이동)."""
import glob, os, re, json, time, urllib.request, sys
sys.path.insert(0, "/home/claude/book")
from wd_style import stylize, GRAY

TOKEN = os.environ["WD_TOKEN"]; BASE = "https://wikidocs.net"
HDR = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}
SRC = "/home/claude/book/src"
PAGE_IDS = list(range(411525, 411541))   # 00 ~ 15
APPENDIX_ID = 424364
IMG_URL = "https://static.wikidocs.net/images/page/411536/ontology-site_71xmrXQ.png"

def patch(pid, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(BASE + f"/napi/pages/{pid}/", data=data, headers=HDR, method="PATCH")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))

def strip_answer_boxes(text):
    lines, out, i = text.splitlines(), [], 0
    while i < len(lines):
        if lines[i].lstrip().startswith(">") and "💬 모범 답안" in lines[i]:
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                i += 1
            # 뒤따르는 빈 줄 하나 제거
            if i < len(lines) and lines[i].strip() == "":
                i += 1
        else:
            out.append(lines[i]); i += 1
    return "\n".join(out)

def extract_boxes(text):
    """(라벨, 본문) 목록. 라벨 = 박스 자체 라벨 또는 직전 질문/실습 제목."""
    lines = text.splitlines()
    last_q, last_h, res = None, None, []
    for idx, ln in enumerate(lines):
        s = ln.strip()
        m = re.match(r"^\*\*(Q\d+\..+?)\*\*$", s)
        if m: last_q = m.group(1)
        if re.match(r"^#{2,3} ", s):
            last_h = re.sub(r"\s*\(.*?\)\s*$", "", s.lstrip("# ").strip()); 
            if s.startswith("## "): last_q = None
        if s.startswith(">") and "💬 모범 답안" in s:
            body = s.lstrip("> ").strip()
            mm = re.match(r"^\*\*💬 모범 답안(?::\s*(.*?))?\*\*\s*[—-]?\s*(.*)$", body)
            label = (mm.group(1) or "").strip() if mm else ""
            content = mm.group(2).strip() if mm else body
            # 여러 문단으로 이어지는 blockquote 답안 수집
            paras, cur = [content], []
            j = idx + 1
            while j < len(lines) and (lines[j].lstrip().startswith(">") or (lines[j].strip()=="" and j+1 < len(lines) and lines[j+1].lstrip().startswith(">"))):
                if "💬 모범 답안" in lines[j]: break
                if lines[j].strip()=="" and "💬 모범 답안" in lines[j+1]: break
                t = re.sub(r"^\s*>\s?", "", lines[j]).rstrip()
                if t == "" :
                    if cur: paras.append("\n".join(cur)); cur = []
                elif cur and not re.match(r"^(\d+(~\d+)?\.|-|\*|\|)\s?", t):
                    cur[-1] = cur[-1] + " " + t
                else:
                    cur.append(t)
                j += 1
            if cur: paras.append("\n".join(cur))
            content = "\n\n".join(x for x in paras if x.strip())
            if not label:
                label = last_q or last_h or "모범 답안"
            elif last_h:
                label = f"{last_h} — {label}"
            res.append((label, content))
    return res

def convert_footnotes(text, cid):
    m = re.search(r"^#+ 각주\s*$", text, flags=re.M)
    if not m: return text
    body, notes = text[:m.start()], text[m.end():]
    defs = {}
    for line in notes.splitlines():
        mm = re.match(r"^\[(\d+)\]\s+(.*)$", line.strip())
        if mm: defs[mm.group(1)] = mm.group(2)
    if not defs: return text
    body = re.sub(r"\[(\d+)\]", lambda mo: f"[^{cid}n{mo.group(1)}]" if mo.group(1) in defs else mo.group(0), body)
    foot = "\n\n".join(f"[^{cid}n{n}]: {t}" for n, t in defs.items())
    return body.rstrip() + "\n\n" + foot + "\n"

def shift_headings(text):
    return re.sub(r"^(#{1,5}) ", lambda mo: "#" * (len(mo.group(1)) + 1) + " ", text, flags=re.M)

def student_front(text):
    return text.replace(
        "- **💬 모범 답안**: 토론 질문·심화 토론 항목에는 모범 답안(예시 답안)을 음영 박스로 제공한다. 모범 답안은 '정답'이 아니라 논증의 예시이며, 수업에서는 이를 넘어서는 답을 기대한다. **박스를 읽기 전에 반드시 스스로 답을 구성해 볼 것.**",
        "- **💬 모범 답안**: 토론 질문·심화 토론 항목의 모범 답안(예시 답안)은 부록 「토론 쟁점 해설」에 모아 두었다. 모범 답안은 '정답'이 아니라 논증의 예시이며, 수업에서는 이를 넘어서는 답을 기대한다. **부록을 읽기 전에 반드시 스스로 답을 구성해 볼 것.**")

files = sorted(glob.glob(os.path.join(SRC, "*.md")))
assert len(files) == 16
appendix = ["이 부록은 각 장 토론 질문과 중간시험의 모범 답안(예시 답안)을 모아 정리한 것이다. 실습 결과물의 예시는 각 장 본문의 「실습 가이드」에 실었다. 모범 답안은 '정답'이 아니라 논증의 예시이며, 스스로 답을 구성해 본 뒤 참고하는 것을 권한다.\n"]

for f, pid in zip(files, PAGE_IDS):
    stem = os.path.basename(f)[:2]
    raw = open(f, encoding="utf-8").read()
    m = re.match(r"^# (.+)\n", raw)
    title = m.group(1).strip() if m else ""
    body = raw[m.end():] if m else raw
    # 부록 수집
    boxes = extract_boxes(body)
    if boxes:
        appendix.append(f"## {re.sub(r'\\s*\\(\\d+주\\)$', '', title)}\n")
        for label, content in boxes:
            appendix.append(f"### {label}\n\n{content}\n")
    # 학생용 본문
    student = strip_answer_boxes(body)
    if stem == "00": student = student_front(student)
    student = student.replace("(src/ontology-site.png)", f"({IMG_URL})")
    student = re.sub(r"(!\[([^\]]*)\]\(" + re.escape(IMG_URL) + r"\))", lambda mo: mo.group(1) + "\n\n<p align=\"center\"><em>" + mo.group(2) + "</em></p>", student)
    student = convert_footnotes(student, "c" + stem)
    ch = None if stem == "00" else int(stem)
    clean_title = re.sub(r"\s*\(\d+주\)\s*$", "", title)
    if ch is None:
        student = stylize(student, None, "기록정보서비스론",
                          "기록과 이용자를 연결하는 서비스의 설계 · 2026학년도 2학기")
    else:
        student = stylize(student, ch, re.sub(r"^\d+장\.\s*", "", clean_title))
    student = student.strip("\n") + "\n"
    patch(pid, {"content": student})
    print(f"{stem} (id={pid}) 갱신: {len(student)}자, 부록 항목 {len(boxes)}개")
    time.sleep(0.4)

app_text = "\n".join(appendix)
open("/home/claude/book/appendix/appendix.md", "w", encoding="utf-8").write(app_text)
patch(APPENDIX_ID, {"content": stylize(app_text, None, "토론 쟁점 해설", "각 장 토론 질문·중간시험의 모범 답안", label="부록 A")})
print("부록 갱신:", len(app_text), "자")
