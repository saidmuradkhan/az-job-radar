import re

URGENT_MARK = re.compile(r"\b(?:[tT][əƏeE][cC][iİI][lL][iİI]|urgent)\b[!:.]*", re.IGNORECASE)
EDGE_JUNK = " -–—|,.!*\"'"


def clean_title(title: str) -> str:
    cleaned = URGENT_MARK.sub("", title)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(EDGE_JUNK)
    return cleaned or title.strip()
