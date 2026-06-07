"""Shared Jinja2 templates instance with Starlette compatibility fix."""
from pathlib import Path
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape


class Templates:
    """Thin Jinja2 wrapper returning HTMLResponse to avoid Starlette bug."""

    def __init__(self, directory: str):
        self.env = Environment(
            loader=FileSystemLoader(directory),
            autoescape=select_autoescape(["html"]),
        )

    def TemplateResponse(self, name: str, context: dict, status_code: int = 200):
        """Render template and return HTMLResponse."""
        template = self.env.get_template(name)
        content = template.render(context)
        return HTMLResponse(content=content, status_code=status_code)


templates = Templates(directory=str(Path(__file__).parent / "templates"))
