"""Normalizes HTML output from AIs."""


class HtmlNormalizer:
    def normalize(self, html: str) -> str:
        lines = html.splitlines()

        if len(lines) < 3:
            return html

        # AIs like to wrap their output in code blocks - strip them
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines[-1].strip().startswith("```"):
            lines = lines[:-1]

        return "\n".join(lines)
