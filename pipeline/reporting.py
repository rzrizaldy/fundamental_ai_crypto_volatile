from __future__ import annotations

from pathlib import Path
from typing import Any
import shutil
import subprocess

from jinja2 import Template


def render_template(template_path: Path, context: dict[str, Any]) -> str:
    with template_path.open("r", encoding="utf-8") as handle:
        template = Template(handle.read())
    return template.render(**context)


def build_markdown_to_tex(markdown_path: Path, tex_path: Path) -> subprocess.CompletedProcess[str]:
    tex_path.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        ["pandoc", "-s", str(markdown_path), "-o", str(tex_path)],
        check=True,
        text=True,
        capture_output=True,
    )


def build_tex_to_pdf(tex_path: Path, output_dir: Path) -> subprocess.CompletedProcess[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if shutil.which("tectonic"):
        return subprocess.run(
            ["tectonic", str(tex_path), "--outdir", str(output_dir)],
            check=True,
            text=True,
            capture_output=True,
        )
    return subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", f"-output-directory={output_dir}", str(tex_path)],
        check=True,
        text=True,
        capture_output=True,
    )
