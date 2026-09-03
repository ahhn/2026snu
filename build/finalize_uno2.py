#!/usr/bin/env python3
"""usage: finalize_uno2.py in.docx out.docx out.pdf "판 구분"
① 목차 갱신 ② 모든 페이지 스타일 A4/여백 ③ 표지 배경 크림색(하단 흰 띠 제거)
④ 머리글: 좌 '기록정보서비스론' / 우 장 제목(Chapter 필드)
⑤ 바닥글: 왼쪽 페이지 좌측정렬·오른쪽 페이지 우측정렬 쪽수 ⑥ docx·pdf 저장"""
import subprocess, time, sys, os
import uno
from com.sun.star.beans import PropertyValue
from com.sun.star.style.ParagraphAdjust import RIGHT, LEFT
from com.sun.star.style.TabAlign import RIGHT as TAB_RIGHT

src, out_docx, out_pdf, edition = [os.path.abspath(a) if i < 3 else a for i, a in enumerate(sys.argv[1:5])]
GREEN, NAVY, TERRA, TAN, CREAM = 0x1F4A3A, 0x1F3557, 0xC8582F, 0xC9B58F, 0xF3EEE6
TITLE = "기록정보서비스론"

proc = subprocess.Popen(["soffice", "--headless", "--norestore", "--invisible",
                         "--accept=socket,host=127.0.0.1,port=2002;urp;"])
local = uno.getComponentContext()
resolver = local.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", local)
ctx = None
for _ in range(40):
    try:
        ctx = resolver.resolve("uno:socket,host=127.0.0.1,port=2002;urp;StarOffice.ComponentContext"); break
    except Exception:
        time.sleep(1)
assert ctx
desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
def prop(n, v):
    p = PropertyValue(); p.Name = n; p.Value = v; return p

doc = desktop.loadComponentFromURL("file://" + src, "_blank", 0, (prop("Hidden", True),))

def _page_field():
    fld = doc.createInstance("com.sun.star.text.TextField.PageNumber")
    fld.NumberingType = 4; fld.SubType = uno.Enum("com.sun.star.text.PageNumberType", "CURRENT")
    return fld

def _chapter_field():
    fld = doc.createInstance("com.sun.star.text.TextField.Chapter")
    fld.Level = 0; fld.ChapterFormat = 0
    return fld

def _bottom_border(cur):
    try:
        bl = uno.createUnoStruct("com.sun.star.table.BorderLine2"); bl.Color = TAN; bl.OuterLineWidth = 6; bl.LineWidth = 6
        cur.BottomBorder = bl; cur.BottomBorderDistance = 60
    except Exception as e:
        print("border skip:", e)

def set_header_left(text_obj):
    """왼쪽(짝수) 페이지: [쪽수 굵게]  기록정보서비스론  — 좌측 정렬"""
    text_obj.setString("")
    cur = text_obj.createTextCursor()
    cur.CharFontName = "Noto Serif CJK KR"; cur.CharFontNameAsian = "Noto Serif CJK KR"
    cur.CharWeight = 150; cur.CharHeight = 10.5; cur.CharColor = GREEN
    text_obj.insertTextContent(cur, _page_field(), False)
    cur.CharWeight = 100; cur.CharHeight = 8; cur.CharColor = NAVY
    cur.CharFontName = "Noto Sans CJK KR"; cur.CharFontNameAsian = "Noto Sans CJK KR"
    text_obj.insertString(cur, "    " + TITLE, False)
    cur.gotoStart(False); cur.gotoEnd(True); cur.ParaAdjust = LEFT
    _bottom_border(cur)

def set_header_right(text_obj):
    """오른쪽(홀수) 페이지: 장 제목  [쪽수 굵게] — 우측 정렬"""
    text_obj.setString("")
    cur = text_obj.createTextCursor()
    cur.CharFontName = "Noto Sans CJK KR"; cur.CharFontNameAsian = "Noto Sans CJK KR"
    cur.CharWeight = 100; cur.CharHeight = 8; cur.CharColor = NAVY
    text_obj.insertTextContent(cur, _chapter_field(), False)
    text_obj.insertString(cur, "    ", False)
    cur.CharFontName = "Noto Serif CJK KR"; cur.CharFontNameAsian = "Noto Serif CJK KR"
    cur.CharWeight = 150; cur.CharHeight = 10.5; cur.CharColor = GREEN
    text_obj.insertTextContent(cur, _page_field(), False)
    cur.gotoStart(False); cur.gotoEnd(True); cur.ParaAdjust = RIGHT
    _bottom_border(cur)

styles = doc.getStyleFamilies().getByName("PageStyles")
for name in styles.getElementNames():
    ps = styles.getByName(name)
    if not ps.isInUse():
        continue
    ps.Width, ps.Height = 21000, 29700
    is_cover = ps.LeftMargin == 0 and ps.TopMargin == 0
    if is_cover:
        ps.HeaderIsOn = False; ps.FooterIsOn = False
        ps.BackColor = CREAM            # 하단 흰 띠 → 표지와 같은 크림색
        continue
    ps.LeftMargin = ps.RightMargin = 2500
    ps.TopMargin, ps.BottomMargin = 2400, 2200
    text_width = ps.Width - ps.LeftMargin - ps.RightMargin
    ps.HeaderIsOn = True; ps.HeaderIsShared = False; ps.HeaderHeight = 800; ps.HeaderBodyDistance = 350
    set_header_right(ps.HeaderText)        # 오른쪽(홀수) 페이지
    set_header_left(ps.HeaderTextLeft)     # 왼쪽(짝수) 페이지
    ps.FooterIsOn = False

idx = doc.getDocumentIndexes()
for i in range(idx.getCount()):
    idx.getByIndex(i).update()

doc.storeToURL("file://" + out_docx, (prop("FilterName", "MS Word 2007 XML"),))
fd = uno.Any("[]com.sun.star.beans.PropertyValue", tuple([prop("UseLosslessCompression", True), prop("ReduceImageResolution", False), prop("Quality", 100)]))
doc.storeToURL("file://" + out_pdf, (prop("FilterName", "writer_pdf_Export"), prop("FilterData", fd)))
doc.close(False)
proc.terminate()
print("done:", os.path.basename(out_docx), os.path.basename(out_pdf))
