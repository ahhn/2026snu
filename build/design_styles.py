#!/usr/bin/env python3
"""ref_base.docx → reference_book.docx : 표지 팔레트(크림/짙은녹색/네이비/테라코타/탄)를 본문 스타일에 적용"""
import re, zipfile, shutil, os

GREEN, NAVY, TERRA, TAN, CREAM, INK, GRAY = "1F4A3A", "1F3557", "C8582F", "C9B58F", "F5F1E8", "2B2B2B", "6B6B6B"
SERIF, SANS, MONO = "Noto Serif CJK KR", "Noto Sans CJK KR", "Noto Sans Mono CJK KR"

SRC = "/home/claude/book/ref_base.docx"
OUT = "/home/claude/book/reference_book.docx"
work = "/home/claude/book/ref_work"
shutil.rmtree(work, ignore_errors=True)
with zipfile.ZipFile(SRC) as z: z.extractall(work)
P = os.path.join(work, "word/styles.xml")
xml = open(P, encoding="utf-8").read()

def fonts(ascii=SERIF, ea=SERIF):
    return f'<w:rFonts w:ascii="{ascii}" w:hAnsi="{ascii}" w:eastAsia="{ea}" w:cs="{ascii}"/>'

def set_style(sid, ppr=None, rpr=None, replace_ppr=False, replace_rpr=False):
    """해당 styleId의 pPr/rPr에 내용 추가(또는 교체)"""
    global xml
    m = re.search(rf'<w:style [^>]*w:styleId="{sid}"[^>]*>.*?</w:style>', xml, flags=re.S)
    assert m, sid
    block = m.group(0); new = block
    if ppr is not None:
        if '<w:pPr>' in new or '<w:pPr/>' in new:
            if replace_ppr:
                new = re.sub(r'<w:pPr>.*?</w:pPr>|<w:pPr/>', f'<w:pPr>{ppr}</w:pPr>', new, count=1, flags=re.S)
            else:
                new = re.sub(r'<w:pPr>', f'<w:pPr>{ppr}', new, count=1) if '<w:pPr>' in new else new.replace('<w:pPr/>', f'<w:pPr>{ppr}</w:pPr>', 1)
        else:
            new = re.sub(r'(<w:rPr>|</w:style>)', lambda mo: f'<w:pPr>{ppr}</w:pPr>' + mo.group(1), new, count=1)
    if rpr is not None:
        if '<w:rPr>' in new or '<w:rPr/>' in new:
            if replace_rpr:
                new = re.sub(r'<w:rPr>.*?</w:rPr>|<w:rPr/>', f'<w:rPr>{rpr}</w:rPr>', new, count=1, flags=re.S)
            else:
                new = re.sub(r'<w:rPr>', f'<w:rPr>{rpr}', new, count=1) if '<w:rPr>' in new else new.replace('<w:rPr/>', f'<w:rPr>{rpr}</w:rPr>', 1)
        else:
            new = new.replace('</w:style>', f'<w:rPr>{rpr}</w:rPr></w:style>', 1)
    xml = xml.replace(block, new)

# 0) 문서 기본: 본문 명조 10.5pt, 줄간격 1.6, 양쪽 정렬
xml = re.sub(r'<w:docDefaults>.*?</w:docDefaults>',
    f'<w:docDefaults><w:rPrDefault><w:rPr>{fonts()}<w:color w:val="{INK}"/><w:sz w:val="21"/><w:szCs w:val="21"/>'
    f'<w:lang w:val="ko-KR" w:eastAsia="ko-KR"/></w:rPr></w:rPrDefault>'
    f'<w:pPrDefault><w:pPr><w:spacing w:after="160" w:line="384" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr></w:pPrDefault></w:docDefaults>',
    xml, flags=re.S)

# 1) 제목 계열
set_style("Title", ppr='<w:spacing w:before="2400" w:after="200"/><w:jc w:val="center"/>', 
          rpr=f'{fonts()}<w:b/><w:color w:val="{GREEN}"/><w:sz w:val="60"/><w:szCs w:val="60"/><w:spacing w:val="60"/>', replace_ppr=True, replace_rpr=True)
set_style("Subtitle", ppr=f'<w:pBdr><w:top w:val="single" w:sz="6" w:space="12" w:color="{TERRA}"/></w:pBdr><w:spacing w:before="120" w:after="480"/><w:jc w:val="center"/>',
          rpr=f'{fonts()}<w:color w:val="{NAVY}"/><w:sz w:val="26"/><w:szCs w:val="26"/>', replace_ppr=True, replace_rpr=True)
set_style("Author", ppr='<w:spacing w:before="600" w:after="60"/><w:jc w:val="center"/>',
          rpr=f'{fonts()}<w:color w:val="{NAVY}"/><w:sz w:val="24"/>', replace_ppr=True, replace_rpr=True)
set_style("Date", ppr='<w:spacing w:before="0" w:after="800"/><w:jc w:val="center"/>',
          rpr=f'{fonts(SANS,SANS)}<w:color w:val="{GRAY}"/><w:sz w:val="20"/>', replace_ppr=True, replace_rpr=True)
set_style("AbstractTitle", ppr=f'<w:pBdr><w:bottom w:val="single" w:sz="4" w:space="4" w:color="{TAN}"/></w:pBdr><w:spacing w:before="240" w:after="160"/><w:jc w:val="left"/>',
          rpr=f'{fonts()}<w:b/><w:color w:val="{GREEN}"/><w:sz w:val="24"/>', replace_ppr=True, replace_rpr=True)
set_style("Abstract", ppr=f'<w:shd w:val="clear" w:color="auto" w:fill="{CREAM}"/><w:ind w:left="284" w:right="284"/><w:spacing w:before="60" w:after="60" w:line="360" w:lineRule="auto"/>',
          rpr=f'<w:sz w:val="20"/><w:color w:val="{INK}"/>', replace_ppr=True, replace_rpr=True)

# 2) 장 제목(Heading1): 새 페이지, 위 여백 크게, 짙은 녹색 큰 명조, 아래 테라코타 규칙선
set_style("Heading1",
    ppr=f'<w:pageBreakBefore/><w:keepNext/><w:pBdr><w:bottom w:val="single" w:sz="8" w:space="10" w:color="{TERRA}"/></w:pBdr>'
        f'<w:spacing w:before="2400" w:after="720" w:line="300" w:lineRule="auto"/><w:jc w:val="left"/><w:outlineLvl w:val="0"/>',
    rpr=f'{fonts()}<w:b/><w:color w:val="{GREEN}"/><w:sz w:val="40"/><w:szCs w:val="40"/>', replace_ppr=True, replace_rpr=True)
# 3) 절 제목(Heading2): 네이비, 왼쪽 녹색 굵은 선
set_style("Heading2",
    ppr=f'<w:keepNext/><w:pBdr><w:left w:val="single" w:sz="18" w:space="8" w:color="{GREEN}"/></w:pBdr>'
        f'<w:spacing w:before="480" w:after="200"/><w:ind w:left="170"/><w:jc w:val="left"/><w:outlineLvl w:val="1"/>',
    rpr=f'{fonts()}<w:b/><w:color w:val="{NAVY}"/><w:sz w:val="28"/><w:szCs w:val="28"/>', replace_ppr=True, replace_rpr=True)
set_style("Heading3",
    ppr='<w:keepNext/><w:spacing w:before="320" w:after="120"/><w:jc w:val="left"/><w:outlineLvl w:val="2"/>',
    rpr=f'{fonts()}<w:b/><w:color w:val="{NAVY}"/><w:sz w:val="23"/><w:szCs w:val="23"/>', replace_ppr=True, replace_rpr=True)
set_style("Heading4",
    ppr='<w:keepNext/><w:spacing w:before="240" w:after="80"/><w:jc w:val="left"/><w:outlineLvl w:val="3"/>',
    rpr=f'{fonts(SANS,SANS)}<w:b/><w:color w:val="{GREEN}"/><w:sz w:val="21"/>', replace_ppr=True, replace_rpr=True)

# 4) 본문·목록
for s in ("BodyText", "FirstParagraph"):
    set_style(s, ppr='<w:spacing w:after="160" w:line="384" w:lineRule="auto"/><w:jc w:val="both"/>', replace_ppr=True)
set_style("Compact", ppr='<w:spacing w:before="40" w:after="40" w:line="360" w:lineRule="auto"/><w:jc w:val="both"/>', replace_ppr=True)

# 5) 모범 답안/안내 박스(BlockText): 크림 배경 + 녹색 왼쪽 굵은 선 + 탄색 테두리
set_style("BlockText",
    ppr=f'<w:pBdr><w:top w:val="single" w:sz="4" w:space="8" w:color="{TAN}"/><w:left w:val="single" w:sz="24" w:space="10" w:color="{GREEN}"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="8" w:color="{TAN}"/><w:right w:val="single" w:sz="4" w:space="8" w:color="{TAN}"/></w:pBdr>'
        f'<w:shd w:val="clear" w:color="auto" w:fill="{CREAM}"/><w:spacing w:before="200" w:after="240" w:line="340" w:lineRule="auto"/><w:ind w:left="284" w:right="284"/><w:jc w:val="both"/>',
    rpr='<w:sz w:val="20"/><w:szCs w:val="20"/>', replace_ppr=True, replace_rpr=True)

# 6) 코드 블록(프롬프트 예시): 연한 회색 상자, 고정폭
set_style("SourceCode",
    ppr=f'<w:pBdr><w:top w:val="single" w:sz="4" w:space="6" w:color="{TAN}"/><w:left w:val="single" w:sz="4" w:space="6" w:color="{TAN}"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="6" w:color="{TAN}"/><w:right w:val="single" w:sz="4" w:space="6" w:color="{TAN}"/></w:pBdr>'
        f'<w:shd w:val="clear" w:color="auto" w:fill="F7F5F0"/><w:spacing w:before="120" w:after="200" w:line="300" w:lineRule="auto"/><w:ind w:left="170" w:right="170"/><w:jc w:val="left"/>',
    rpr=f'{fonts(MONO,MONO)}<w:sz w:val="18"/><w:szCs w:val="18"/><w:color w:val="{INK}"/>', replace_ppr=True, replace_rpr=True) if 'w:styleId="SourceCode"' in xml else None
if 'w:styleId="SourceCode"' not in xml:
    xml = xml.replace('</w:styles>',
        f'<w:style w:type="paragraph" w:styleId="SourceCode"><w:name w:val="Source Code"/><w:basedOn w:val="Normal"/><w:pPr><w:pBdr><w:top w:val="single" w:sz="4" w:space="6" w:color="{TAN}"/><w:left w:val="single" w:sz="4" w:space="6" w:color="{TAN}"/><w:bottom w:val="single" w:sz="4" w:space="6" w:color="{TAN}"/><w:right w:val="single" w:sz="4" w:space="6" w:color="{TAN}"/></w:pBdr><w:shd w:val="clear" w:color="auto" w:fill="F7F5F0"/><w:spacing w:before="120" w:after="200" w:line="300" w:lineRule="auto"/><w:ind w:left="170" w:right="170"/><w:jc w:val="left"/></w:pPr><w:rPr>{fonts(MONO,MONO)}<w:sz w:val="18"/><w:szCs w:val="18"/><w:color w:val="{INK}"/></w:rPr></w:style></w:styles>')
set_style("VerbatimChar", rpr=f'{fonts(MONO,MONO)}<w:sz w:val="18"/>', replace_rpr=True)

# 7) 각주·캡션·목차
set_style("FootnoteText", ppr='<w:spacing w:after="40" w:line="260" w:lineRule="auto"/><w:jc w:val="both"/>',
          rpr=f'<w:sz w:val="17"/><w:szCs w:val="17"/><w:color w:val="{INK}"/>', replace_ppr=True, replace_rpr=True)
set_style("ImageCaption", ppr='<w:spacing w:before="80" w:after="240"/><w:jc w:val="center"/>',
          rpr=f'{fonts(SANS,SANS)}<w:i/><w:sz w:val="17"/><w:color w:val="{GRAY}"/>', replace_ppr=True, replace_rpr=True)
set_style("TOCHeading", ppr=f'<w:pageBreakBefore/><w:pBdr><w:bottom w:val="single" w:sz="8" w:space="10" w:color="{TERRA}"/></w:pBdr><w:spacing w:before="2400" w:after="600"/><w:jc w:val="left"/>',
          rpr=f'{fonts()}<w:b/><w:color w:val="{GREEN}"/><w:sz w:val="40"/>', replace_ppr=True, replace_rpr=True)
set_style("Hyperlink", rpr=f'<w:color w:val="{NAVY}"/><w:u w:val="none"/>', replace_rpr=True)

# 8) 표 스타일: 탄색 가는 선, 셀 여백
m = re.search(r'<w:style w:type="table"[^>]*w:styleId="Table">.*?</w:style>', xml, flags=re.S)
tbl = m.group(0)
newtbl = re.sub(r'<w:tblPr>.*?</w:tblPr>',
    f'<w:tblPr><w:tblBorders><w:top w:val="single" w:sz="8" w:space="0" w:color="{GREEN}"/><w:bottom w:val="single" w:sz="8" w:space="0" w:color="{GREEN}"/>'
    f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="{TAN}"/></w:tblBorders>'
    f'<w:tblCellMar><w:top w:w="70" w:type="dxa"/><w:left w:w="100" w:type="dxa"/><w:bottom w:w="70" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar></w:tblPr>',
    tbl, flags=re.S)
xml = xml.replace(tbl, newtbl)

# TOC 항목 스타일 추가(없으면)
if 'w:styleId="TOC1"' not in xml:
    xml = xml.replace('</w:styles>',
        f'<w:style w:type="paragraph" w:styleId="TOC1"><w:name w:val="toc 1"/><w:basedOn w:val="Normal"/><w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9350"/></w:tabs><w:spacing w:before="160" w:after="60" w:line="300" w:lineRule="auto"/><w:jc w:val="left"/></w:pPr><w:rPr><w:b/><w:color w:val="{GREEN}"/><w:sz w:val="21"/></w:rPr></w:style>'
        f'<w:style w:type="paragraph" w:styleId="TOC2"><w:name w:val="toc 2"/><w:basedOn w:val="Normal"/><w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="9350"/></w:tabs><w:spacing w:before="0" w:after="40" w:line="300" w:lineRule="auto"/><w:ind w:left="360"/><w:jc w:val="left"/></w:pPr><w:rPr><w:color w:val="{INK}"/><w:sz w:val="19"/></w:rPr></w:style></w:styles>')


# 8b) 저자 소개: 작은 글씨
xml = xml.replace('</w:styles>',
    f'<w:style w:type="paragraph" w:styleId="AuthorInfo"><w:name w:val="Author Info"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="0" w:after="40" w:line="280" w:lineRule="auto"/><w:jc w:val="left"/></w:pPr><w:rPr>{fonts(SANS,SANS)}<w:sz w:val="17"/><w:szCs w:val="17"/><w:color w:val="{GRAY}"/></w:rPr></w:style></w:styles>')
# 8c) 장 인트로 페이지의 절 제목 목록
xml = xml.replace('</w:styles>',
    f'<w:style w:type="paragraph" w:styleId="IntroSection"><w:name w:val="Intro Section"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="0" w:after="200" w:line="300" w:lineRule="auto"/><w:ind w:left="284"/><w:jc w:val="left"/></w:pPr><w:rPr>{fonts()}<w:color w:val="{NAVY}"/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr></w:style></w:styles>')
# 9) 색인 스타일
xml = xml.replace('</w:styles>',
    f'<w:style w:type="paragraph" w:styleId="IndexEntry"><w:name w:val="Index Entry"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="0" w:after="20" w:line="260" w:lineRule="auto"/><w:ind w:left="340" w:hanging="340"/><w:jc w:val="left"/></w:pPr><w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>'
    f'<w:style w:type="paragraph" w:styleId="IndexGroup"><w:name w:val="Index Group"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="200" w:after="60"/><w:jc w:val="left"/></w:pPr><w:rPr>{fonts(SANS,SANS)}<w:b/><w:color w:val="{TERRA}"/><w:sz w:val="21"/></w:rPr></w:style></w:styles>')

open(P, "w", encoding="utf-8").write(xml)

# 페이지 여백: 상 2.4 / 하 2.2 / 좌우 2.5cm
D = os.path.join(work, "word/document.xml")
d = open(D, encoding="utf-8").read()
d = re.sub(r'<w:pgMar [^>]*/>', '<w:pgMar w:top="1361" w:right="1418" w:bottom="1247" w:left="1418" w:header="680" w:footer="680" w:gutter="0"/>', d)
open(D, "w", encoding="utf-8").write(d)

if os.path.exists(OUT): os.remove(OUT)
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(work):
        for f in files:
            full = os.path.join(root, f)
            z.write(full, os.path.relpath(full, work))
print("reference_book.docx 생성")
