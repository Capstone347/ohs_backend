from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas.email import AuthOtpContext, DocumentDeliveryContext, OrderConfirmationContext, SjpDeliveryContext

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates" / "emails"


class EmailTemplateRenderer:
    def __init__(self, templates_dir: Path | None = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render_order_confirmation(self, context: OrderConfirmationContext) -> str:
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"templates directory not found: {self.templates_dir}")
        
        template = self.env.get_template("order_confirmation.html")
        return template.render(**context.model_dump())

    def render_document_delivery(self, context: DocumentDeliveryContext) -> str:
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"templates directory not found: {self.templates_dir}")
        
        template = self.env.get_template("document_delivery.html")
        return template.render(**context.model_dump())

    def render_sjp_delivery(self, context: SjpDeliveryContext) -> str:
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"templates directory not found: {self.templates_dir}")

        template = self.env.get_template("sjp_delivery.html")
        return template.render(**context.model_dump())

    def render_auth_otp(self, context: AuthOtpContext) -> str:
        if not self.templates_dir.exists():
            raise FileNotFoundError(f"templates directory not found: {self.templates_dir}")

        template = self.env.get_template("otp_request.html")
        return template.render(**context.model_dump())

