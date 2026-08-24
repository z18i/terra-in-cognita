# Diary Entry Format

## Filename

Diary entries use the following format:

    YYYY-MM-DD.html

For example:

    2026-08-24.html

The filename represents the publication date.

Because the format is year-first, lexicographical sorting also produces
chronological ordering.

## Location

All diary entries live in:

    entries/

## Creating an entry

Create a new HTML file:

    entries/2026-08-24.html

Add the entry content, then commit and push it:

    git add entries/2026-08-24.html
    git commit -m "Add diary entry for 2026-08-24"
    git push

The GitHub Actions workflow automatically regenerates the entry list
in `index.html`.

## Index

The section between these markers in `index.html` is generated:

    <!-- ENTRIES_START -->
    <!-- ENTRIES_END -->

Do not manually edit the contents between these markers.
