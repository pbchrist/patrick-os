"""End-to-end CLI behaviour and the decision log.

The CLI is the contract the brief specifies, so each of the seven required verbs
gets a test that runs it the way a person would.
"""

import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr

from patrick_os import decisions
from patrick_os.cli import main

from tests.support import REPO, TempRootTest


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliTest(TempRootTest):
    def setUp(self):
        super().setUp()
        self.write_skill("demo", channel="email")
        self.write_voice("global.md",
                         "---\nscope: global\n---\n\n## Rules\n\n- [G-001] Global rule.\n")
        self.base = ["--root", str(self.root)]

    def test_list_skills(self):
        code, out, _ = run_cli(*self.base, "skills", "list")
        self.assertEqual(code, 0)
        self.assertIn("demo", out)

    def test_inspect_skill(self):
        code, out, _ = run_cli(*self.base, "skills", "show", "demo")
        self.assertEqual(code, 0)
        self.assertIn("task class:  research", out)
        self.assertIn("topic (required)", out)

    def test_run_a_skill_with_inputs(self):
        code, out, _ = run_cli(*self.base, "run", "demo", "--input", "topic=reviews")
        self.assertEqual(code, 0)
        self.assertIn("(dry-run)", out)
        runs = list((self.root / "runs").iterdir())
        self.assertEqual(len(runs), 1)
        self.assertIn("reviews", (runs[0] / "workorder.md").read_text())

    def test_route_explains_itself_without_calling_anything(self):
        code, out, _ = run_cli(*self.base, "route", "judge.copy")
        self.assertEqual(code, 0)
        self.assertIn("local-qwen", out)
        self.assertIn("denied by route", out)

    def test_record_feedback_on_an_output(self):
        (self.root / "a.txt").write_text("Written for Acme Dental.")
        (self.root / "b.txt").write_text("Written for Sunrise Dental.")
        code, out, _ = run_cli(*self.base, "feedback", "add", "--skill", "demo",
                               "--original", str(self.root / "a.txt"),
                               "--edited", str(self.root / "b.txt"))
        self.assertEqual(code, 0)
        self.assertIn("recorded-local", out)
        self.assertIn("A correction stays local until it repeats", out)

    def test_promote_approved_feedback_into_the_right_rule_file(self):
        (self.root / "a.txt").write_text("This will unlock significant growth.")
        (self.root / "b.txt").write_text("The homepage lists three duplicate reviews.")
        for _ in range(2):
            run_cli(*self.base, "feedback", "add", "--skill", "demo",
                    "--channel", "email",
                    "--original", str(self.root / "a.txt"),
                    "--edited", str(self.root / "b.txt"))
        _, listing, _ = run_cli(*self.base, "feedback", "list")
        entry_id = [line.split()[0] for line in listing.strip().split("\n")
                    if "proposed" in line][0]
        code, out, _ = run_cli(*self.base, "feedback", "promote", entry_id)
        self.assertEqual(code, 0, out)
        self.assertIn("promoted S-001 into skill:demo", out)
        self.assertIn("- [S-001]",
                      (self.root / "voice" / "skills" / "demo.md").read_text())

    def test_run_regression_tests(self):
        code, out, _ = run_cli(*self.base, "test", "--no-unit")
        self.assertEqual(code, 0, out)
        self.assertIn("PASS", out)

    def test_regression_run_reports_failure_with_a_nonzero_exit(self):
        directory = self.root / "skills" / "demo"
        (directory / "fixtures" / "impossible.json").write_text(json.dumps(
            {"inputs": {"topic": "x"}, "expect": {"must_contain": ["not in the order"]}}))
        code, out, _ = run_cli(*self.base, "test", "--no-unit")
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)

    def test_log_a_decision(self):
        code, out, _ = run_cli(*self.base, "decision", "add", "--title",
                               "Route judges away from the writer model",
                               "--kind", "architecture", "--decision", "Deny it in the table.")
        self.assertEqual(code, 0)
        code, listing, _ = run_cli(*self.base, "decision", "list")
        self.assertIn("0001", listing)
        self.assertIn("Route judges away from the writer model", listing)

    def test_doctor_reports_without_calling_a_provider(self):
        code, out, _ = run_cli(*self.base, "doctor")
        self.assertEqual(code, 0)
        self.assertIn("credentials are read from the environment", out)

    def test_unknown_skill_exits_cleanly(self):
        code, _, err = run_cli(*self.base, "skills", "show", "nope")
        self.assertEqual(code, 2)
        self.assertIn("no skill named", err)

    def test_bad_input_syntax_is_reported(self):
        with self.assertRaises(SystemExit):
            run_cli(*self.base, "run", "demo", "--input", "no-equals-sign")


class DecisionTest(TempRootTest):
    def test_decisions_number_sequentially_and_keep_their_slug(self):
        first = decisions.add("First choice", base=self.root)
        second = decisions.add("Second choice", base=self.root)
        self.assertEqual(first["id"], "0001")
        self.assertEqual(second["id"], "0002")
        self.assertTrue(second["path"].endswith("0002-second-choice.md"))

    def test_decision_records_parse_back(self):
        decisions.add("A choice", kind="product", context="c", decision="d",
                      base=self.root)
        record = decisions.list_decisions(self.root)[0]
        self.assertEqual(record["meta"]["kind"], "product")
        self.assertEqual(record["meta"]["status"], "accepted")

    def test_invalid_kind_is_refused(self):
        with self.assertRaises(decisions.DecisionError):
            decisions.add("x", kind="vibes", base=self.root)


class RepoHygieneTest(unittest.TestCase):
    def test_no_credential_shaped_string_is_committed(self):
        import re
        pattern = re.compile(r"(sk-[A-Za-z0-9]{16,}|gho_[A-Za-z0-9]{16,}|"
                             r"AKIA[0-9A-Z]{16})")
        for path in REPO.rglob("*"):
            if not path.is_file() or ".git/" in str(path):
                continue
            if path.suffix not in {".py", ".json", ".md", ".sh", ""}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError):
                continue
            self.assertIsNone(pattern.search(text), f"credential-shaped string in {path}")


if __name__ == "__main__":
    unittest.main()
