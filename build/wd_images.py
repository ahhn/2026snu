"""원고의 그림 경로 → 위키독스에서 쓸 공개 URL.

위키독스에는 이미지 업로드 API가 없다. 그래서 원고가 `src/*.png`로 가리키는 그림을
위키독스에서는 이미 공개된 주소로 바꿔 끼운다. 주소는 셋 중 하나다.
  · 위키독스에 수동으로 올려 둔 파일(static.wikidocs.net)
  · 그림의 원 출처(남의 문서에서 인용한 화면)
  · 이 저장소의 raw URL(우리가 만든 그림)

sync_wikidocs.py(전체 동기화)와 sync_one.py(한 장만)가 함께 쓴다.
한쪽에만 적으면 어느 경로로 올렸느냐에 따라 그림이 깨지므로 여기 한 곳에만 둔다.
"""

IMG_MAP = {
    "src/ontology-site.png": "https://static.wikidocs.net/images/page/411536/ontology-site_71xmrXQ.png",
    "src/atom-description.png": "https://www.accesstomemory.org/en/docs/2.6/_images/context-menu-description.png",
    "src/fip-ontology.png": "https://raw.githubusercontent.com/ahhn/2026snu/main/src/fip-ontology.png",
}


def swap_images(text):
    """원고의 그림 경로를 공개 URL로 바꾸고, 캡션을 그림 아래 가운데 줄로 옮긴다."""
    import re
    for local, url in IMG_MAP.items():
        text = text.replace(f"({local})", f"({url})")
        text = re.sub(
            r"(!\[([^\]]*)\]\(" + re.escape(url) + r"\))",
            lambda mo: mo.group(1) + '\n\n<p align="center"><em>' + mo.group(2) + "</em></p>",
            text)
    return text
