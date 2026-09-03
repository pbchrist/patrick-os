"""Strict front-matter parser for Patrick OS.

Patrick OS does not depend on PyYAML. It parses a small, documented subset of
YAML and *rejects everything else loudly* rather than guessing. A skill file
that uses a construct outside the subset is a broken skill, not a skill that
quietly parses into something unexpected.

Supported subset
----------------
    key: value                  scalar
    key: "quoted value"         quoted scalar (single or double)
    key:                        empty value (None)
    key:                        block list of scalars
      - item
    key:                        block list of maps (exactly one level deep)
      - name: subreddit
        type: string
    # full-line comment
    (blank lines anywhere)

Scalar coercion: ``true``/``false`` -> bool, ``null``/``~``/empty -> None,
integers and floats -> numbers, everything else -> ``str``. Zero-padded numerics
(``0001``) stay strings, because they are always identifiers. Quote a value to
force it to stay a string.

Explicitly rejected: tabs, block scalars (``|`` / ``>``), anchors and aliases
(``&`` / ``*``), inline flow collections (``[...]`` / ``{...}``), documents
with more than the nesting shown above, and duplicate keys.
"""

from __future__ import annotations

import re

DELIMITER = "---"
_LEADING_ZERO = re.compile(r"^-?0\d+$")
_LIST_INDENT = 2
_MAP_INDENT = 4


class FrontmatterError(ValueError):
    """Raised for any input outside the documented subset."""

    def __init__(self, message, line_no=None, line=None):
        self.line_no = line_no
        self.line = line
        if line_no is not None:
            message = f"line {line_no}: {message}"
            if line is not None:
                message += f"\n  |{line}"
        super().__init__(message)


def split(text):
    """Split ``text`` into (frontmatter_source, body).

    Returns ``("", text)`` when the document has no front-matter block.
    """
    lines = text.split("\n")
    start = 0
    # Tolerate a leading BOM / blank lines before the opening delimiter.
    while start < len(lines) and lines[start].strip() == "":
        start += 1
    if start >= len(lines) or lines[start].strip() != DELIMITER:
        return "", text
    for index in range(start + 1, len(lines)):
        if lines[index].strip() == DELIMITER:
            return "\n".join(lines[start + 1:index]), "\n".join(lines[index + 1:])
    raise FrontmatterError("front-matter block was opened but never closed")


def parse(source):
    """Parse front-matter source into a dict. See module docstring for the subset."""
    data = {}
    current_key = None
    current_list = None
    current_map = None

    def close_list():
        nonlocal current_key, current_list, current_map
        if current_key is not None:
            if current_map is not None:
                current_list.append(current_map)
            # A bare "key:" with nothing indented under it is an empty value,
            # not an empty list. Only actual "- " items make it a list.
            data[current_key] = current_list if current_list else None
        current_key = current_list = current_map = None

    for offset, raw in enumerate(source.split("\n")):
        line_no = offset + 1
        if "\t" in raw:
            raise FrontmatterError("tabs are not allowed; use spaces", line_no, raw)
        if raw.strip() == "" or raw.lstrip().startswith("#"):
            continue

        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()

        if indent == 0:
            close_list()
            if stripped.startswith("- "):
                raise FrontmatterError("list item without a parent key", line_no, raw)
            key, sep, value = stripped.partition(":")
            if not sep:
                raise FrontmatterError("expected 'key: value'", line_no, raw)
            key = key.strip()
            _check_key(key, line_no, raw)
            if key in data:
                raise FrontmatterError(f"duplicate key {key!r}", line_no, raw)
            value = value.strip()
            if value == "":
                current_key, current_list, current_map = key, [], None
            else:
                data[key] = _scalar(value, line_no, raw)
            continue

        if current_key is None:
            raise FrontmatterError("indented line without a parent key", line_no, raw)

        if indent == _LIST_INDENT and stripped.startswith("- "):
            item = stripped[2:].strip()
            if current_map is not None:
                current_list.append(current_map)
                current_map = None
            key, sep, value = item.partition(":")
            if sep and not _looks_like_url(item):
                key = key.strip()
                _check_key(key, line_no, raw)
                current_map = {key: _scalar(value.strip(), line_no, raw)}
            else:
                current_list.append(_scalar(item, line_no, raw))
            continue

        if indent == _MAP_INDENT and current_map is not None:
            key, sep, value = stripped.partition(":")
            if not sep:
                raise FrontmatterError("expected 'key: value' inside a list item", line_no, raw)
            key = key.strip()
            _check_key(key, line_no, raw)
            if key in current_map:
                raise FrontmatterError(f"duplicate key {key!r} in list item", line_no, raw)
            current_map[key] = _scalar(value.strip(), line_no, raw)
            continue

        if indent == _LIST_INDENT:
            raise FrontmatterError(
                "expected a '- ' list item at this indent", line_no, raw)
        raise FrontmatterError(
            f"unexpected indent {indent}; the supported subset allows {_LIST_INDENT}-space "
            f"list items and {_MAP_INDENT}-space keys inside a list item",
            line_no,
            raw,
        )

    close_list()
    return data


def _check_key(key, line_no, raw):
    if not key:
        raise FrontmatterError("empty key", line_no, raw)
    if any(char in key for char in "&*[]{}|>"):
        raise FrontmatterError(
            f"key {key!r} uses a YAML feature outside the supported subset", line_no, raw
        )


def _looks_like_url(item):
    """``- https://x`` is a scalar, not a map, even though it contains a colon."""
    head = item.split(":", 1)[0].strip().lower()
    return head in {"http", "https", "file", "mailto", "ssh", "git"}


def _scalar(value, line_no, raw):
    if value == "" or value == "~" or value.lower() == "null":
        return None
    first = value[0]
    if first in "&*":
        raise FrontmatterError("anchors and aliases are not supported", line_no, raw)
    if first in "|>":
        raise FrontmatterError("block scalars are not supported", line_no, raw)
    if first in "[{":
        raise FrontmatterError(
            "inline flow collections are not supported; use a block list", line_no, raw
        )
    if len(value) >= 2 and first in "\"'" and value[-1] == first:
        return value[1:-1]
    lowered = value.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if _LEADING_ZERO.match(value):
        # 0001 is an identifier, not the number one. Zero-padded values are ids,
        # zip codes, and version segments; coercing them loses the padding and
        # silently breaks every lookup that used the padded form.
        return value
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def load(text):
    """Parse a whole document into ``(frontmatter_dict, body_str)``."""
    source, body = split(text)
    return parse(source), body
