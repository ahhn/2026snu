#!/usr/bin/env python3
"""src/NN.md 한 장만 위키독스에 반영한다. sync_wikidocs.py 의 변환 규칙을 그대로 따른다.

사용: python3 build/sync_one.py 09 [--dry]
"""
import os, re, sys, json, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from wd_style import stylize  # noqa: E402


TOKEN = open(os.path.expanduser("~/.wd_token")).read().strip()
BASE = "https://wikidocs.net"
HDR = {"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"}
SRC = os.path.join(os.path.dirname(HERE), "src")
PAGE_IDS = list(range(411525, 411541))  # 00 ~ 15
IMG_URL = "https://static.wikidocs.net/images/page/411536/ontology-site_71xmrXQ.png"


def api(method, pid, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(BASE + f"/napi/pages/{pid}/", data=data,
                                 headers=HDR, method=method)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))


def strip_answer_boxes(text):
    lines, out, i = text.splitlines(), [], 0
    while i < len(lines):
        if lines[i].lstrip().startswith(">") and "💬 모범 답안" in lines[i]:
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                i += 1
            if i < len(lines) and lines[i].strip() == "":
                i += 1
        else:
            out.append(lines[i]); i += 1
    return "\n".join(out)


def convert_footnotes(text, cid):
    m = re.search(r"^#+ 각주\s*$", text, flags=re.M)
    if not m:
        return text
    body, notes = text[:m.start()], text[m.end():]
    defs = {}
    for line in notes.splitlines():
        mm = re.match(r"^\[(\d+)\]\s+(.*)$", line.strip())
        if mm:
            defs[mm.group(1)] = mm.group(2)
    if not defs:
        return text
    body = re.sub(r"\[(\d+)\]",
                  lambda mo: f"[^{cid}n{mo.group(1)}]" if mo.group(1) in defs else mo.group(0),
                  body)
    foot = "\n\n".join(f"[^{cid}n{n}]: {t}" for n, t in defs.items())
    return body.rstrip() + "\n\n" + foot + "\n"


def render(stem):
    path = os.path.join(SRC, f"{stem}.md")
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"^# (.+)\n", raw)
    title = m.group(1).strip() if m else ""
    body = raw[m.end():] if m else raw
    student = strip_answer_boxes(body)
    student = student.replace("(src/ontology-site.png)", f"({IMG_URL})")
    student = re.sub(r"(!\[([^\]]*)\]\(" + re.escape(IMG_URL) + r"\))",
                     lambda mo: mo.group(1) + "\n\n<p align=\"center\"><em>" + mo.group(2) + "</em></p>",
                     student)
    student = convert_footnotes(student, "c" + stem)
    clean_title = re.sub(r"\s*\(\d+주\)\s*$", "", title)
    student = stylize(student, int(stem), re.sub(r"^\d+장\.\s*", "", clean_title))
    return student.strip("\n") + "\n"


if __name__ == "__main__":
    stem = sys.argv[1]
    dry = "--dry" in sys.argv
    pid = PAGE_IDS[int(stem)]
    new = render(stem)
    cur = api("GET", pid)
    old = cur.get("content", "")
    print(f"{stem}장 → 위키독스 {pid} ({cur.get('subject','?')})")
    print(f"  현재 {len(old):,}자 → 새 {len(new):,}자 (차이 {len(new)-len(old):+,})")
    if dry:
        import difflib
        d = [l for l in difflib.unified_diff(old.splitlines(), new.splitlines(),
                                             lineterm="", n=1)]
        print(f"  변경 줄 {len([l for l in d if l[:1] in '+-' and l[:3] not in ('+++','---')])}개")
        for l in d[:6]:
            print("   ", l[:110])
        print("  (dry run — 전송하지 않음)")
    else:
        api("PATCH", pid, {"content": new})
        print("  갱신 완료")
