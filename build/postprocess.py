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
def cell_text_len(tc):
    txt = "".join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', tc, flags=re.S))
    return sum(2 if ord(ch) > 0x2E80 else 1 for ch in txt)
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
        weights.append(min(max(L, 8), 70))
    widths = [int(TOTAL * w / sum(weights)) for w in weights]
    widths[-1] += TOTAL - sum(widths)
    grid = '<w:tblGrid>' + ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths) + '</w:tblGrid>'
    t = re.sub(r'<w:tblGrid>.*?</w:tblGrid>', grid, t, flags=re.S)
    t = re.sub(r'<w:tblW [^>]*/>', f'<w:tblW w:w="{TOTAL}" w:type="dxa"/><w:tblLayout w:type="fixed"/>', t)
    t = t.replace('<w:jc w:val="start" />', '<w:jc w:val="left"/>')
    def fix_row(r, is_header):
        tcs = re.findall(r'<w:tc>.*?</w:tc>', r, flags=re.S)
        for i, tc in enumerate(tcs):
            w = widths[i] if i < len(widths) else widths[-1]
            shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{GREEN}"/>' if is_header else ''
            new = tc.replace('<w:tcPr></w:tcPr>', f'<w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shd}<w:vAlign w:val="top"/></w:tcPr>', 1)
            rpr = f'<w:rPr><w:b/><w:color w:val="FFFFFF"/><w:sz w:val="19"/><w:szCs w:val="19"/>' if is_header else '<w:rPr><w:sz w:val="19"/><w:szCs w:val="19"/>'
            new = re.sub(r'<w:r>(<w:rPr>)?', lambda mo: '<w:r>' + rpr + ('' if mo.group(1) else '</w:rPr>'), new)
            new = re.sub(r'<w:pPr>', '<w:pPr><w:spacing w:before="40" w:after="40" w:line="280" w:lineRule="auto"/>', new)
            r = r.replace(tc, new, 1)
        if is_header and '<w:tblHeader' not in r:
            r = r.replace('<w:tr>', '<w:tr><w:trPr><w:tblHeader/></w:trPr>', 1)
        return r
    for i, r in enumerate(rows):
        t = t.replace(r, fix_row(r, i == 0), 1)
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
