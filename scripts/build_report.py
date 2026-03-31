from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pipeline.config import ROOT_DIR
from pipeline.reporting import build_markdown_to_tex, build_tex_to_pdf


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert Markdown reports to TeX and PDF.")
    parser.add_argument("--input", required=True, help="Markdown source.")
    parser.add_argument("--output-dir", default="reports/build", help="Directory for generated TeX/PDF files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    markdown_path = ROOT_DIR / args.input
    output_dir = ROOT_DIR / args.output_dir
    tex_path = markdown_path.with_suffix(".tex")
    build_markdown_to_tex(markdown_path, tex_path)
    build_tex_to_pdf(tex_path, output_dir)
    print(f"Built report artifacts under {output_dir}")


if __name__ == "__main__":
    main()
