"""The parser is the foundation: a skill that mis-parses is a rule that silently
does not apply. Every construct outside the documented subset must be rejected
loudly rather than guessed at."""

import unittest

from patrick_os import frontmatter


class ParseTest(unittest.TestCase):
    def test_scalars_are_coerced(self):
        data = frontmatter.parse(
            "name: reddit-mine\nversion: 2\nratio: 0.5\nactive: true\n"
            "off: false\nempty:\nquoted: \"true\"\n"
        )
        self.assertEqual(data["name"], "reddit-mine")
        self.assertEqual(data["version"], 2)
        self.assertEqual(data["ratio"], 0.5)
        self.assertIs(data["active"], True)
        self.assertIs(data["off"], False)
        self.assertIsNone(data["empty"])
        self.assertEqual(data["quoted"], "true", "quoting must force a string")

    def test_block_list_of_scalars(self):
        data = frontmatter.parse("tags:\n  - research\n  - reddit\n")
        self.assertEqual(data["tags"], ["research", "reddit"])

    def test_block_list_of_maps(self):
        data = frontmatter.parse(
            "inputs:\n"
            "  - name: subreddit\n"
            "    required: true\n"
            "  - name: window\n"
            "    required: false\n"
            "    default: 14\n"
        )
        self.assertEqual(
            data["inputs"],
            [
                {"name": "subreddit", "required": True},
                {"name": "window", "required": False, "default": 14},
            ],
        )

    def test_url_in_list_is_a_scalar_not_a_map(self):
        data = frontmatter.parse("refs:\n  - https://example.com/x\n")
        self.assertEqual(data["refs"], ["https://example.com/x"])

    def test_comments_and_blank_lines_ignored(self):
        data = frontmatter.parse("# a comment\n\nname: x\n\n# another\nv: 1\n")
        self.assertEqual(data, {"name": "x", "v": 1})

    def test_split_returns_body(self):
        meta, body = frontmatter.load("---\nname: x\n---\n# Title\ntext\n")
        self.assertEqual(meta["name"], "x")
        self.assertEqual(body.strip(), "# Title\ntext")

    def test_document_without_frontmatter_is_all_body(self):
        meta, body = frontmatter.load("# Just markdown\n")
        self.assertEqual(meta, {})
        self.assertEqual(body, "# Just markdown\n")


class RejectionTest(unittest.TestCase):
    """Each of these silently 'works' in a hand-rolled parser and produces the
    wrong value. They must raise instead."""

    def assertRejected(self, source, fragment):
        with self.assertRaises(frontmatter.FrontmatterError) as caught:
            frontmatter.parse(source)
        self.assertIn(fragment, str(caught.exception))

    def test_tabs(self):
        self.assertRejected("name:\tx\n", "tabs")

    def test_block_scalar(self):
        self.assertRejected("body: |\n  text\n", "block scalars")

    def test_anchor(self):
        self.assertRejected("a: &anchor\n", "anchors")

    def test_flow_collection(self):
        self.assertRejected("tags: [a, b]\n", "flow collections")

    def test_duplicate_key(self):
        self.assertRejected("a: 1\na: 2\n", "duplicate key")

    def test_nested_mapping_rejected(self):
        self.assertRejected("a:\n  b:\n    c: 1\n", "list item")

    def test_over_indented_list_rejected(self):
        self.assertRejected("a:\n      - x\n", "unexpected indent")

    def test_zero_padded_values_stay_strings(self):
        """0001 is a decision id, not the number one. Coercing it loses the
        padding and breaks every lookup that used the padded form."""
        data = frontmatter.parse("id: 0001\nzip: 02134\ncount: 12\nzero: 0\n")
        self.assertEqual(data["id"], "0001")
        self.assertEqual(data["zip"], "02134")
        self.assertEqual(data["count"], 12)
        self.assertEqual(data["zero"], 0)

    def test_bare_key_is_none_not_empty_list(self):
        """A field left blank must read as absent, not as an empty collection."""
        self.assertIsNone(frontmatter.parse("channel:\n")["channel"])

    def test_orphan_list_item(self):
        self.assertRejected("- item\n", "list item without a parent key")

    def test_missing_colon(self):
        self.assertRejected("just a line\n", "expected 'key: value'")

    def test_unclosed_frontmatter(self):
        with self.assertRaises(frontmatter.FrontmatterError):
            frontmatter.split("---\nname: x\n")


if __name__ == "__main__":
    unittest.main()
