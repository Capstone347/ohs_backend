from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from typing import Mapping


TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "emails"


class EmailTemplateRenderer:
    def __init__(self, templates_dir: Path | None = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render_order_confirmation(self, context: Mapping[str, object]) -> str:
        template = self.env.get_template("order_confirmation.html")
        return template.render(**context)

    def render_document_delivery(self, context: Mapping[str, object]) -> str:
        template = self.env.get_template("document_delivery.html")
        return template.render(**context)
