"""Normalizes HTML output from AIs."""

from abc import ABC, abstractmethod


class Strategy(ABC):
    @abstractmethod
    def normalize(self, html: str) -> str | None: ...


class FindDoctypeNormalizer(Strategy):
    def normalize(self, html: str) -> str | None:
        parts = html.split("<!DOCTYPE html>", 1)
        if len(parts) == 1:
            return None
        [_, html] = parts
        html = "<!DOCTYPE html>" + html
        parts = html.split("</html>", 1)
        if len(parts) == 1:
            return None
        [html, _] = parts
        html = html + "</html>"
        return html


class FindHtmlNormalizer(Strategy):
    def normalize(self, html: str) -> str | None:
        parts = html.split("<html", 1)
        if len(parts) == 1:
            return None
        [_, html] = parts
        html = "<html" + html
        parts = html.split("</html>", 1)
        if len(parts) == 1:
            return None
        [html, _] = parts
        return html


class CodeBlockHtmlNormalizer(Strategy):
    def find(self, lines: list[str], start: str) -> int | None:
        for i, line in enumerate(lines):
            if line.strip().startswith(start):
                return i
        return None

    def normalize(self, html: str) -> str | None:
        lines = html.splitlines()

        if len(lines) < 3:
            return None

        block_start = self.find(lines, "```")
        if block_start is None:
            return None

        block_end = self.find(lines[block_start:], "```")
        if block_end is None:
            return None

        return "\n".join(lines[block_start : block_start + block_end + 1])


class NoopNormalizer(Strategy):
    def normalize(self, html: str) -> str | None:
        return html


class HtmlNormalizer:
    def __init__(self) -> None:
        self.strategies = [
            FindDoctypeNormalizer(),
            FindHtmlNormalizer(),
            CodeBlockHtmlNormalizer(),
            NoopNormalizer(),
        ]

    def normalize(self, html: str) -> str:
        for strategy in self.strategies:
            result = strategy.normalize(html)
            if result is not None:
                return result
        return html
