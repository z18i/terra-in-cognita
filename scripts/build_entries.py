#!/usr/bin/env python3

from pathlib import Path
import re
import shutil
import sys


ROOT = Path(__file__).resolve().parent.parent

SOURCE_DIR = ROOT / "entries"

BUILD_DIR = ROOT / "build"
BUILD_ENTRIES_DIR = BUILD_DIR / "entries"
BUILD_CSS_DIR = BUILD_DIR / "css"

INDEX_FILE = ROOT / "index.html"
CSS_SOURCE = ROOT / "css" / "stylez.css"

START_MARKER = "<!-- ENTRIES_START -->"
END_MARKER = "<!-- ENTRIES_END -->"


# Characters commonly seen when UTF-8 has accidentally been
# interpreted as Latin-1 / Windows-1252.
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

    A higher score means the text contains more characters or
    sequences commonly associated with encoding corruption.
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
        "Â\\",
    )

    for sequence in common_sequences:
        score += 3 * text.count(sequence)

    return score


def repair_mojibake(text: str) -> str:
    """
    Attempt to repair common UTF-8-as-CP1252/Latin-1 corruption.

    The original text is kept unless a candidate repair has a
    demonstrably lower mojibake score.
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

    If the file is not valid UTF-8, stop the build with a useful error.

    If recognizable mojibake is found, attempt to repair it.
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


def extract_entry_date(source: Path) -> str:
    """
    Extract YYYY-MM-DD from the entry filename.

    Example:

        2026-08-26.html

    becomes:

        2026-08-26
    """

    match = re.fullmatch(
        r"(\d{4}-\d{2}-\d{2})",
        source.stem,
    )

    if not match:
        raise SystemExit(
            f"ERROR: {source.relative_to(ROOT)} does not use the "
            f"required YYYY-MM-DD filename format."
        )

    return match.group(1)


def get_entry_files() -> list[Path]:
    """
    Return all source diary entries, newest first.
    """

    return sorted(
        (
            path
            for path in SOURCE_DIR.iterdir()
            if path.is_file()
            and path.suffix.lower() in {".html", ".htm"}
        ),
        key=lambda path: path.name,
        reverse=True,
    )


def build_entry(
    source: Path,
    previous_entry: Path | None,
    next_entry: Path | None,
) -> Path:
    """
    Convert a minimal diary entry into a complete HTML document.

    Source example:

        <h1>The beginning.</h1>

        <p>Hello.</p>

    Filename:

        2026-08-26.html

    Generated document gets:

        <title>2026-08-26</title>
        <meta charset="UTF-8">
        <link rel="stylesheet" href="../css/stylez.css">

    The source HTML itself is otherwise left untouched.
    """

    content = read_utf8(source).strip()

    if not content:
        raise SystemExit(
            f"ERROR: {source.relative_to(ROOT)} is empty."
        )

    entry_date = extract_entry_date(source)

    # ------------------------------------------------------------
    # Navigation
    #
    # get_entry_files() returns entries newest -> oldest.
    #
    # Therefore:
    #
    # previous_entry = older entry
    # next_entry     = newer entry
    # ------------------------------------------------------------

    navigation_parts = []

    if previous_entry is not None:
        navigation_parts.append(
            f'<a href="{previous_entry.name}" class="previous">'
            f'← Previous'
            f'</a>'
        )

    navigation_parts.append(
        '<a href="../index.html" class="index-link">'
        'Index'
        '</a>'
    )

    if next_entry is not None:
        navigation_parts.append(
            f'<a href="{next_entry.name}" class="next">'
            f'Next →'
            f'</a>'
        )

    navigation = "\n                ".join(
        navigation_parts
    )

    # ------------------------------------------------------------
    # Generate complete HTML document.
    #
    # The source entry is inserted directly into <article>.
    #
    # No <h1> is generated.
    # No <p> is generated.
    #
    # This means your source remains:
    #
    #   <h1>Your heading</h1>
    #   <p>Your paragraph.</p>
    # ------------------------------------------------------------

    generated = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>{entry_date}</title>

    <link
        rel="stylesheet"
        href="../css/stylez.css"
    >
</head>

<body>

    <main class="notebook-page">

        <article class="entry-content">
{content}
        </article>

        <nav class="entry-navigation">
                {navigation}
        </nav>

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
        raise SystemExit(
            "ERROR: index.html not found."
        )

    content = read_utf8(INDEX_FILE)

    if START_MARKER not in content:
        raise SystemExit(
            "ERROR: ENTRIES_START marker not found in index.html."
        )

    if END_MARKER not in content:
        raise SystemExit(
            "ERROR: ENTRIES_END marker not found in index.html."
        )

    start_position = content.index(START_MARKER)
    end_position = content.index(END_MARKER)

    if start_position >= end_position:
        raise SystemExit(
            "ERROR: ENTRIES_START must appear before ENTRIES_END."
        )

    files = get_entry_files()

    lines = [
        '<ul class="entries">'
    ]

    for file in files:
        entry_date = extract_entry_date(file)

        lines.append(
            f'  <li>'
            f'<a href="entries/{file.name}">'
            f'{entry_date}'
            f'</a>'
            f'</li>'
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
    """
    Build the complete website output.
    """

    if not SOURCE_DIR.exists():
        raise SystemExit(
            "ERROR: entries/ directory not found."
        )

    if not CSS_SOURCE.exists():
        raise SystemExit(
            f"ERROR: {CSS_SOURCE.relative_to(ROOT)} not found."
        )

    # ------------------------------------------------------------
    # Start with a completely clean build directory.
    #
    # This is important because deleting an entry from entries/
    # must also remove its generated version from build/.
    # ------------------------------------------------------------

    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    BUILD_ENTRIES_DIR.mkdir(
        parents=True
    )

    BUILD_CSS_DIR.mkdir(
        parents=True
    )

    # ------------------------------------------------------------
    # Find source entries.
    # ------------------------------------------------------------

    entries = get_entry_files()

    if not entries:
        print(
            "WARNING: no HTML entries found in entries/"
        )

    # ------------------------------------------------------------
    # Generate every entry.
    # ------------------------------------------------------------

    for index, source in enumerate(entries):

        # Entries are newest -> oldest.

        # Older entry.
        previous_entry = (
            entries[index + 1]
            if index + 1 < len(entries)
            else None
        )

        # Newer entry.
        next_entry = (
            entries[index - 1]
            if index > 0
            else None
        )

        destination = build_entry(
            source,
            previous_entry,
            next_entry,
        )

        print(
            f"Built: "
            f"{source.relative_to(ROOT)}"
            f" -> "
            f"{destination.relative_to(ROOT)}"
        )

    # ------------------------------------------------------------
    # Copy CSS into build/.
    # ------------------------------------------------------------

    css_destination = BUILD_CSS_DIR / CSS_SOURCE.name

    shutil.copy2(
        CSS_SOURCE,
        css_destination,
    )

    print(
        f"Copied: "
        f"{CSS_SOURCE.relative_to(ROOT)}"
        f" -> "
        f"{css_destination.relative_to(ROOT)}"
    )

    # ------------------------------------------------------------
    # Update the main index.html.
    # ------------------------------------------------------------

    update_index()

    print(
        "Updated index.html entry list."
    )

    print(
        "Build completed successfully."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
