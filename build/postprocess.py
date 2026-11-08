#!/usr/bin/env python3
"""pandoc 산출 docx 후처리:
 1) 전면(bleed) 표지 페이지를 첫 섹션으로 삽입
 2) 모든 표: 머리행 짙은녹색 배경·흰 글씨·굵게, 본문 셀 9.5pt, 표 안 정렬 왼쪽
 3) 본문 섹션에 머리글(도서명·판 구분)과 바닥글(쪽수) 연결, 표지는 제외
 4) AbstractTitle 'Abstract' → '강좌 안내'
usage: postprocess.py in.docx out.docx "판 구분 문구"
"""
import sys, zipfile, re, shutil, os

GREEN, NAVY, TERRA, TAN = "1F4A3A", "1F3557", "C8582F", "C9B58F"
src, dst, edition = sys.argv[1], sys.argv[2], sys.argv[3]
COVER = "/home/claude/book/cover.png"

zin = zipfile.ZipFile(src)
files = {n: zin.read(n) for n in zin.namelist()}
zin.close()

doc = files["word/document.xml"].decode("utf-8")
rels = files["word/_rels/document.xml.rels"].decode("utf-8")
ct = files["[Content_Types].xml"].decode("utf-8")

# ---------- 1) 표지 ----------
files["word/media/cover.png"] = open(COVER, "rb").read()
rels = rels.replace("</Relationships>",
    '<Relationship Id="rIdCover" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/cover.png"/>'
    '<Relationship Id="rIdHdrX" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="headerX.xml"/>'
    '<Relationship Id="rIdFtrX" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footerX.xml"/>'
    '</Relationships>')
if 'Extension="png"' not in ct:
    ct = ct.replace("<Default ", '<Default Extension="png" ContentType="image/png"/><Default ', 1)
ct = ct.replace("</Types>",
    '<Override PartName="/word/headerX.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
    '<Override PartName="/word/footerX.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')

W, H = 7560000, 10692000  # A4 EMU
cover_xml = (
 '<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr>'
 '<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
 f'<wp:extent cx="{W}" cy="{H}"/><wp:docPr id="9001" name="cover"/>'
 '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
 '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="9001" name="cover.png"/><pic:cNvPicPr/></pic:nvPicPr>'
 '<pic:blipFill><a:blip r:embed="rIdCover"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
 f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{W}" cy="{H}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
 '</a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
 '<w:p><w:pPr><w:spacing w:before="0" w:after="0"/><w:sectPr><w:type w:val="nextPage"/><w:pgSz w:w="11906" w:h="16838"/>'
 '<w:pgMar w:top="0" w:right="0" w:bottom="0" w:left="0" w:header="0" w:footer="0" w:gutter="0"/></w:sectPr></w:pPr></w:p>')
doc = doc.replace("<w:body>", "<w:body>" + cover_xml, 1)

# ---------- 2) 표 스타일 ----------
TOTAL = 9070  # 본문 폭(twips)
KEEP_TABLE_MAX_ROWS = 10  # 이 행수 이하의 표는 쪽을 넘기지 않고 통째로 옮긴다
MIN_COL = 1000            # 열 최소 폭(twips). 한글 3자 + 여백이 꺾이지 않는 선
HALF_W = 100              # 반각 1자의 대략적 폭(twips). 한글은 2단위로 센다
CELL_PAD = 240            # 셀 좌우 여백
MAX_FLOOR = 2800          # 한 낱말이 아주 길 때 열 하나가 표를 삼키지 않도록 둔 상한
def cell_text_len(tc):
    # <w:t ...> 만 잡는다. '<w:t[^>]*>'로 쓰면 <w:tcPr />·<w:tblHeader .../> 같은
    # 다른 태그까지 걸려 본문이 아니라 XML 마크업 길이를 세게 된다(열너비가 균등해지는 원인).
    txt = "".join(re.findall(r'<w:t(?:\s[^>]*)?>(.*?)</w:t>', tc, flags=re.S))
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in txt)
def cell_min_token(tc):
    # 셀 안에서 '끊을 수 없는 가장 긴 낱말'의 폭. 열의 min-content 폭을 정하는 데 쓴다.
    # 공백으로만 끊으므로 한글 어절 하나가 중간에서 꺾이는 일을 막는다.
    txt = "".join(re.findall(r'<w:t(?:\s[^>]*)?>(.*?)</w:t>', tc, flags=re.S))
    best = 0
    for tok in txt.split():
        best = max(best, sum(2 if ord(ch) > 0x2E80 else 1 for ch in tok))
    return best
def style_table(m):
    t = m.group(0)
    t = t.replace('<w:tcPr />', '<w:tcPr></w:tcPr>').replace('<w:tcPr/>', '<w:tcPr></w:tcPr>')
    rows = re.findall(r'<w:tr[ >].*?</w:tr>', t, flags=re.S)
    if not rows: return t
    ncol = max(len(re.findall(r'<w:tc>', r)) for r in rows)
    # 열 가중치: 각 열의 최대 텍스트 길이(상한 70, 하한 8)
    weights = []
    for c in range(ncol):
        lens = []
        for r in rows:
            tcs = re.findall(r'<w:tc>.*?</w:tc>', r, flags=re.S)
            if c < len(tcs): lens.append(cell_text_len(tcs[c]))
        L = max(lens) if lens else 10
        weights.append(min(max(L, 10), 70))
    widths = [int(TOTAL * w / sum(weights)) for w in weights]
    widths[-1] += TOTAL - sum(widths)
    # 열마다 최소 폭(floor)을 둔다. 가중치는 '가장 긴 셀'에 비례하므로, 긴 설명이 든 열이
    # 넓어지는 대신 짧은 이름만 든 열이 낱말 중간에서 꺾이는 일이 생긴다. 그래서 floor를
    # 그 열의 가장 긴 낱말이 한 줄에 들어가는 폭으로 잡고, 모자란 만큼 가장 넓은 열에서 가져온다.
    floors = []
    for c in range(ncol):
        tok = 0
        for r in rows:
            tcs = re.findall(r'<w:tc>.*?</w:tc>', r, flags=re.S)
            if c < len(tcs): tok = max(tok, cell_min_token(tcs[c]))
        floors.append(min(max(MIN_COL, tok * HALF_W + CELL_PAD), MAX_FLOOR))
    if len(widths) > 1:
        if sum(floors) > TOTAL:
            floors = [int(f * TOTAL / sum(floors)) for f in floors]
        widths = [max(widths[i], floors[i]) for i in range(ncol)]
        # 바닥을 올린 만큼 표가 넘치면, 여유(현재 폭 − 바닥)가 있는 열들에서 비례해 거둬들인다.
        excess = sum(widths) - TOTAL
        if excess > 0:
            slack = [widths[i] - floors[i] for i in range(ncol)]
            tot = sum(slack)
            if tot > 0:
                for i in range(ncol):
                    widths[i] -= int(excess * slack[i] / tot)
        # 반올림 오차는 여유가 가장 많은 열에서 흡수한다.
        slack = [widths[i] - floors[i] for i in range(ncol)]
        widths[slack.index(max(slack))] += TOTAL - sum(widths)
    grid = '<w:tblGrid>' + ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths) + '</w:tblGrid>'
    t = re.sub(r'<w:tblGrid>.*?</w:tblGrid>', grid, t, flags=re.S)
    t = re.sub(r'<w:tblW [^>]*/>', f'<w:tblW w:w="{TOTAL}" w:type="dxa"/><w:tblLayout w:type="fixed"/>', t)
    t = t.replace('<w:jc w:val="start" />', '<w:jc w:val="left"/>')
    # 짧은 표는 쪽을 넘기지 않게 묶는다(마지막 행을 뺀 모든 문단에 keepNext).
    # 한 쪽에 들어갈 수 없을 만큼 긴 표는 그대로 나뉘게 둔다.
    keep_together = len(rows) <= KEEP_TABLE_MAX_ROWS
    def fix_row(r, is_header, is_last):
        tcs = re.findall(r'<w:tc>.*?</w:tc>', r, flags=re.S)
        for i, tc in enumerate(tcs):
            w = widths[i] if i < len(widths) else widths[-1]
            shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{GREEN}"/>' if is_header else ''
            new = tc.replace('<w:tcPr></w:tcPr>', f'<w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shd}<w:vAlign w:val="top"/></w:tcPr>', 1)
            rpr = f'<w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="19"/><w:szCs w:val="19"/>' if is_header else '<w:rPr><w:sz w:val="19"/><w:szCs w:val="19"/>'
            new = re.sub(r'<w:r>(<w:rPr>)?', lambda mo: '<w:r>' + rpr + ('' if mo.group(1) else '</w:rPr>'), new)
            # pPr 자식은 스키마 순서를 지켜야 한다(pStyle → keepNext → spacing → 나머지).
            # 순서가 어긋나면 LibreOffice가 조용히 무시한다.
            keep = '<w:keepNext/>' if (keep_together and not is_last) else ''
            spacing = '<w:spacing w:before="40" w:after="40" w:line="280" w:lineRule="auto"/>'
            def rebuild_ppr(mo):
                inner = mo.group(1)
                style = ''
                ms = re.search(r'<w:pStyle[^>]*/>', inner)
                if ms:
                    style = ms.group(0)
                    inner = inner.replace(style, '', 1)
                inner = re.sub(r'<w:keepNext\s*/>|<w:spacing[^>]*/>', '', inner)
                return '<w:pPr>' + style + keep + spacing + inner + '</w:pPr>'
            new = re.sub(r'<w:pPr>(.*?)</w:pPr>', rebuild_ppr, new, flags=re.S)
            # pPr가 아예 없는 문단에는 만들어 준다.
            new = re.sub(r'<w:p>(?!\s*<w:pPr>)', '<w:p><w:pPr>' + keep + spacing + '</w:pPr>', new)
            r = r.replace(tc, new, 1)
        # 행 자체가 쪽에 걸쳐 쪼개지지 않게 한다.
        props = '<w:cantSplit/>' + ('<w:tblHeader/>' if is_header and '<w:tblHeader' not in r else '')
        if '<w:trPr>' in r:
            r = r.replace('<w:trPr>', '<w:trPr>' + props, 1)
        else:
            r = re.sub(r'<w:tr(\s[^>]*)?>', lambda mo: mo.group(0) + '<w:trPr>' + props + '</w:trPr>', r, count=1)
        return r
    last = len(rows) - 1
    for i, r in enumerate(rows):
        t = t.replace(r, fix_row(r, i == 0, i == last), 1)
    return t
doc = re.sub(r'<w:tbl>.*?</w:tbl>', style_table, doc, flags=re.S)

# ---------- 3) 머리글/바닥글 ----------
header_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
 '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
 f'<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="4" w:space="4" w:color="{TAN}"/></w:pBdr><w:tabs><w:tab w:val="right" w:pos="9070"/></w:tabs><w:spacing w:after="0"/><w:jc w:val="left"/></w:pPr>'
 f'<w:r><w:rPr><w:rFonts w:ascii="Noto Sans CJK KR" w:hAnsi="Noto Sans CJK KR" w:eastAsia="Noto Sans CJK KR"/><w:color w:val="{GREEN}"/><w:sz w:val="16"/></w:rPr><w:t xml:space="preserve">기록정보서비스론 강의교재</w:t></w:r>'
 f'<w:r><w:rPr><w:rFonts w:ascii="Noto Sans CJK KR" w:hAnsi="Noto Sans CJK KR" w:eastAsia="Noto Sans CJK KR"/><w:color w:val="{NAVY}"/><w:sz w:val="16"/></w:rPr><w:tab/><w:t xml:space="preserve">{edition}</w:t></w:r></w:p></w:hdr>')
footer_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
 '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
 '<w:p><w:pPr><w:spacing w:before="0" w:after="0"/><w:jc w:val="right"/></w:pPr>'
 f'<w:r><w:rPr><w:color w:val="{TERRA}"/><w:sz w:val="18"/></w:rPr><w:t xml:space="preserve">— </w:t></w:r>'
 f'<w:r><w:rPr><w:color w:val="{GREEN}"/><w:sz w:val="18"/></w:rPr><w:fldChar w:fldCharType="begin"/></w:r>'
 '<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r>'
 f'<w:r><w:rPr><w:color w:val="{GREEN}"/><w:sz w:val="18"/></w:rPr><w:t>1</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r>'
 f'<w:r><w:rPr><w:color w:val="{TERRA}"/><w:sz w:val="18"/></w:rPr><w:t xml:space="preserve"> —</w:t></w:r></w:p></w:ftr>')
files["word/headerX.xml"] = header_xml.encode("utf-8")
files["word/footerX.xml"] = footer_xml.encode("utf-8")
# 표지 sectPr(첫 번째) 제외, 나머지 sectPr에 연결 + 쪽번호 1부터
n = 0
def add_ref(m):
    global n
    n += 1
    if n == 1: return m.group(0)
    return m.group(0) + '<w:headerReference w:type="default" r:id="rIdHdrX"/><w:footerReference w:type="default" r:id="rIdFtrX"/>' + ('<w:pgNumType w:start="1"/>' if n == 2 else '')
doc = re.sub(r'<w:sectPr(?: [^>]*)?>', add_ref, doc)
# 표지 섹션에는 헤더/푸터가 없도록 titlePg가 아닌 '빈 참조' 유지(첫 sectPr에 참조 없음 = 이전 섹션 없음 → 없음)

# ---------- 4) 잡다 ----------
doc = doc.replace('<w:t xml:space="preserve">Abstract</w:t>', '<w:t xml:space="preserve">강좌 안내</w:t>').replace('<w:t>Abstract</w:t>', '<w:t>강좌 안내</w:t>')

files["word/document.xml"] = doc.encode("utf-8")
files["word/_rels/document.xml.rels"] = rels.encode("utf-8")
files["[Content_Types].xml"] = ct.encode("utf-8")
if os.path.exists(dst): os.remove(dst)
with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
    for name, data in files.items():
        z.writestr(name, data)
print("postprocess:", os.path.basename(dst), f"sectPr {n}개")
