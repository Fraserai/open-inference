"""Small, dependency-free HTML helpers: tables, captions, headings and text.

Provider pages are parsed with the standard library's HTMLParser rather than
regular expressions, which are slow and fragile on 1 MB+ documentation pages.
"""

import re
from html.parser import HTMLParser

_SPACE = re.compile(r"\s+")


def squash(text):
    return _SPACE.sub(" ", text).strip()


class _Collector(HTMLParser):
    """Collects every table (with caption, preceding h2, rows of cell text and cell
    img alt texts), every element marked data-slot="card-title", and the page text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.card_titles = []
        self.text_parts = []
        self._heading = None          # text of the latest h2
        self._in_h2 = False
        self._h2_buf = []
        self._table = None
        self._row = None
        self._cell = None             # [text parts, img alts]
        self._caption = None
        self._card_depth = 0
        self._card_buf = []
        self._skip = 0                # inside script/style

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self._skip += 1
        elif tag == "h2":
            self._in_h2, self._h2_buf = True, []
        elif tag == "table":
            self._table = {"caption": None, "heading": self._heading, "rows": []}
        elif tag == "caption" and self._table is not None:
            self._caption = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = [[], []]
        elif tag == "img" and self._cell is not None:
            self._cell[1].append(attrs.get("alt") or "")
        if attrs.get("data-slot") == "card-title":
            self._card_depth, self._card_buf = 1, []
        elif self._card_depth:
            self._card_depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        elif tag == "h2" and self._in_h2:
            self._in_h2 = False
            self._heading = squash(" ".join(self._h2_buf))
        elif tag == "caption" and self._caption is not None:
            self._table["caption"] = squash(" ".join(self._caption))
            self._caption = None
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append({"text": squash(" ".join(self._cell[0])), "alts": self._cell[1]})
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self._table["rows"].append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None
        if self._card_depth:
            self._card_depth -= 1
            if self._card_depth == 0:
                self.card_titles.append(squash(" ".join(self._card_buf)))

    def handle_data(self, data):
        if self._skip:
            return
        self.text_parts.append(data)
        if self._in_h2:
            self._h2_buf.append(data)
        if self._caption is not None:
            self._caption.append(data)
        if self._cell is not None:
            self._cell[0].append(data)
        if self._card_depth:
            self._card_buf.append(data)


def parse(html):
    collector = _Collector()
    collector.feed(html)
    collector.close()
    collector.text = squash(" ".join(collector.text_parts))
    return collector


def table_with_header(tables, *names):
    """The first table whose first row contains all the given header names."""
    for table in tables:
        if table["rows"]:
            header = [c["text"].lower() for c in table["rows"][0]]
            if all(any(n.lower() == h for h in header) for n in names):
                return table
    return None
