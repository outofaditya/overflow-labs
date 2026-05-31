from __future__ import annotations

from bs4 import BeautifulSoup


# split a stack overflow html body into (prose, code_blocks)
# <pre>...</pre> regions become entries in code_blocks; inline <code> stays in prose
def parse_body(html: str | None) -> tuple[str, list[str]]:
    if not html:
        return "", []
    soup = BeautifulSoup(html, "lxml")
    code_blocks: list[str] = []
    for pre in soup.find_all("pre"):
        code_blocks.append(pre.get_text())
        pre.decompose()
    prose = soup.get_text(separator=" ", strip=True)
    return prose, code_blocks
