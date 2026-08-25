#!/usr/bin/env python3

from pathlib import Path
import re
import shutil
import sys


ROOT = Path(__file__).resolve().parent.parent

SOURCE_DIR = ROOT / "entries"
BUILD_DIR = ROOT / "build"
BUILD_ENTRIES_DIR = BUILD_DIR / "entries"

INDEX_FILE = ROOT / "index.html"

CSS_SOURCE = ROOT / "css" / "stylez.css"
BUILD_CSS_DIR = BUILD_DIR / "css"


START_MARKER = "<!-- ENTRIES_START -->"
END_MARKER = "<!-- ENTRIES_END -->"


# Characters commonly seen when UTF-8 has accidentally been decoded
# as Latin-1 / Windows-1252.
MOJIBAKE_MARKERS = (
    "Ã",
    "Â",
    "â",
    "ð",
    "ƒ",
    "„",
    "™",
    "œ",
    "ž",
    "�",
)


def mojibake_score(text: str) -> int:
    """
    Give suspicious UTF-8 mojibake a score.

    A higher score means the text contains more characters/sequences
    commonly associated with encoding corruption.
    """

    score = 0

    for marker in MOJIBAKE_MARKERS:
        score += text.count(marker)

    common_sequences = (
        "Ã¤",
        "Ã¶",
        "Ã¼",
        "ÃŸ",
        "â€",
        "ðŸ",
        "Â¯",
        "Â°",
    )

    for sequence in common_sequences:
        score += 3 * text.count(sequence)

    return score


def repair_mojibake(text: str) -> str:
    """
    Attempt to repair common UTF-8-as-CP1252/Latin-1 corruption.

    The original text is kept unless the repaired candidate has
    a demonstrably lower mojibake score.
    """

    original_score = mojibake_score(text)

    if original_score == 0:
        return text

    candidates = []

    for encoding in ("cp1252", "latin1"):
        try:
            candidate = text.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue

        candidates.append(candidate)

    if not candidates:
        return text

    best = min(candidates, key=mojibake_score)

    if mojibake_score(best) < original_score:
        return best

    return text


def read_utf8(path: Path) -> str:
    """
    Read a file as strict UTF-8.

    If the file is not valid UTF-8, stop the build with a clear error.
    If it contains recognizable mojibake, attempt to repair it.
    """

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit(
            f"ERROR: {path.relative_to(ROOT)} is not valid UTF-8.\n"
            f"Please save the file as UTF-8.\n"
            f"Details: {exc}"
        )

    repaired = repair_mojibake(text)

    if repaired != text:
        print(
            f"Repaired likely UTF-8 mojibake: "
            f"{path.relative_to(ROOT)}"
        )

    return repaired


def build_entry(source: Path) -> Path:
    """
    Convert a minimal diary entry into a complete HTML document.
    """

    content = read_utf8(source).strip()

    # Require exactly one <title>...</title>.
    titles = re.findall(
        r"<title\b[^>]*>(.*?)</title\s*>",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if len(titles) != 1:
        raise SystemExit(
            f"ERROR: {source.relative_to(ROOT)} must contain exactly "
            f"one <title>...</title> element. Found {len(titles)}."
        )

    title = titles[0].strip()

    # Remove the title from the original source.
    # Everything remaining becomes the page body.
    body = re.sub(
        r"<title\b[^>]*>.*?</title\s*>",
        "",
        content,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()

    if not body:
        raise SystemExit(
            f"ERROR: {source.relative_to(ROOT)} has a title "
            f"but no body content."
        )

    generated = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="stylesheet" href="../css/stylez.css">
</head>
<body>
    <main>
{body}
    </main>
</body>
</html>
"""

    destination = BUILD_ENTRIES_DIR / source.name

    destination.write_text(
        generated,
        encoding="utf-8",
        newline="\n",
    )

    return destination


def update_index() -> None:
    """
    Update only the section between ENTRIES_START and ENTRIES_END
    in the main index.html.
    """

    if not INDEX_FILE.exists():
        raise SystemExit("ERROR: index.html not found.")

    content = read_utf8(INDEX_FILE)

    if START_MARKER not in content:
        raise SystemExit(
            "ERROR: ENTRIES_START marker not found in index.html"
        )

    if END_MARKER not in content:
        raise SystemExit(
            "ERROR: ENTRIES_END marker not found in index.html"
        )

    start_position = content.index(START_MARKER)
    end_position = content.index(END_MARKER)

    if start_position >= end_position:
        raise SystemExit(
            "ERROR: ENTRIES_START must appear before ENTRIES_END"
        )

    # Find generated HTML files.
    files = sorted(
        (
            path
            for path in BUILD_ENTRIES_DIR.iterdir()
            if path.is_file()
            and path.suffix.lower() in {".html", ".htm"}
        ),
        key=lambda path: path.name,
        reverse=True,
    )

    lines = [
        '<ul class="entries">'
    ]

    for file in files:
        label = file.stem

        lines.append(
            f'  <li><a href="entries/{file.name}">'
            f'{label}'
            f'</a></li>'
        )

    lines.append("</ul>")

    entries_html = "\n".join(lines)

    start = start_position + len(START_MARKER)
    end = end_position

    updated = (
        content[:start]
        + "\n"
        + entries_html
        + "\n"
        + content[end:]
    )

    INDEX_FILE.write_text(
        updated,
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    if not SOURCE_DIR.exists():
        raise SystemExit(
            "ERROR: entries/ directory not found."
        )

    if not CSS_SOURCE.exists():
        raise SystemExit(
            f"ERROR: {CSS_SOURCE.relative_to(ROOT)} not found."
        )

    # Always rebuild from scratch.
    #
    # This ensures that if an entry is deleted from entries/,
    # its generated version cannot remain in build/.
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    BUILD_ENTRIES_DIR.mkdir(parents=True)
    BUILD_CSS_DIR.mkdir(parents=True)

    sources = sorted(
        (
            path
            for path in SOURCE_DIR.iterdir()
            if path.is_file()
            and path.suffix.lower() in {".html", ".htm"}
        ),
        key=lambda path: path.name,
    )

    if not sources:
        print("WARNING: no HTML entries found in entries/")

    for source in sources:
        destination = build_entry(source)

        print(
            f"Built: "
            f"{source.relative_to(ROOT)} -> "
            f"{destination.relative_to(ROOT)}"
        )

    # Copy the stylesheet into build/ as well.
    shutil.copy2(
        CSS_SOURCE,
        BUILD_CSS_DIR / CSS_SOURCE.name,
    )

    print(
        f"Copied: "
        f"{CSS_SOURCE.relative_to(ROOT)} -> "
        f"{(BUILD_CSS_DIR / CSS_SOURCE.name).relative_to(ROOT)}"
    )

    # Update the main index.html.
    update_index()

    print("Updated index.html entry list.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
