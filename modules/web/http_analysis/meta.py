"""Minimal HTML metadata extraction using the stdlib HTMLParser."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser


@dataclass(frozen=True, slots=True)
class PageMetadata:
    title: str | None
    description: str | None
    canonical: str | None
    robots: str | None
    language: str | None
    open_graph: dict[str, str] = field(default_factory=dict)


class _MetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.description: str | None = None
        self.canonical: str | None = None
        self.robots: str | None = None
        self.language: str | None = None
        self.open_graph: dict[str, str] = {}
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value for key, value in attrs}
        if tag == "title":
            self._in_title = True
            self._title_parts = []
        elif tag == "html":
            self.language = values.get("lang")
        elif tag == "meta":
            name = values.get("name")
            property_name = values.get("property")
            content = values.get("content")
            if name == "description":
                self.description = content
            elif name == "robots":
                self.robots = content
            elif property_name and property_name.startswith("og:") and content:
                self.open_graph[property_name] = content
        elif tag == "link" and values.get("rel") == "canonical":
            self.canonical = values.get("href")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
            self.title = "".join(self._title_parts).strip() or None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)


def parse_page_metadata(html: str) -> PageMetadata:
    parser = _MetaParser()
    parser.feed(html)
    parser.close()
    return PageMetadata(
        title=parser.title,
        description=parser.description,
        canonical=parser.canonical,
        robots=parser.robots,
        language=parser.language,
        open_graph=dict(parser.open_graph),
    )
