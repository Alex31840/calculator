"""Tests that README.md documents what the acceptance criteria require.

These tests check the *content* of README.md itself (not sum.py's
behaviour, which is covered by tests/test_sum.py), to make sure the
documentation keeps the required examples and statements.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"


def _read_readme() -> str:
    assert README.exists(), "README.md must exist at the project root"
    return README.read_text(encoding="utf-8")


class TestReadmeExists:
    def test_readme_exists_and_is_not_empty(self):
        text = _read_readme()
        assert text.strip() != ""


class TestArgumentInvocationExample:
    def test_contains_argument_invocation_example(self):
        text = _read_readme()
        assert "python sum.py 2 5 10" in text

    def test_contains_expected_output_for_argument_example(self):
        text = _read_readme()
        # The documented example output for `python sum.py 2 5 10` is 17.
        assert re.search(r"python sum\.py 2 5 10\s*\n#\s*17", text)


class TestInteractiveModeDocumented:
    def test_mentions_interactive_prompt_mode(self):
        text = _read_readme()
        assert "Interactive-prompt mode" in text or "interactive" in text.lower()

    def test_documents_prompt_text(self):
        text = _read_readme()
        assert "Enter numbers separated by spaces" in text


class TestEmptyInputExample:
    def test_contains_no_input_example(self):
        text = _read_readme()
        assert "python sum.py < /dev/null" in text or "No numbers were provided" in text

    def test_contains_no_numbers_message(self):
        text = _read_readme()
        assert "No numbers were provided." in text


class TestInvalidTokenExample:
    def test_contains_invalid_token_invocation(self):
        text = _read_readme()
        assert "python sum.py 2 abc xyz" in text

    def test_contains_invalid_token_message(self):
        text = _read_readme()
        assert "Invalid number(s): 'abc', 'xyz'" in text


class TestSubtractionDocumented:
    def test_contains_subtract_invocation_example(self):
        text = _read_readme()
        assert "python sum.py --subtract 10 5 2" in text

    def test_contains_expected_output_for_subtract_example(self):
        text = _read_readme()
        assert re.search(r"python sum\.py --subtract 10 5 2\s*\n#\s*3", text)

    def test_contains_subtract_negative_decimal_example(self):
        text = _read_readme()
        assert "python sum.py --subtract 10 -3.5" in text
        assert re.search(
            r"python sum\.py --subtract 10 -3\.5\s*\n#\s*13\.5", text
        )

    def test_contains_subtract_empty_input_example(self):
        text = _read_readme()
        assert "python sum.py --subtract < /dev/null" in text

    def test_contains_subtract_invalid_token_example(self):
        text = _read_readme()
        assert "python sum.py --subtract 10 abc xyz" in text
        # Reuses the same error-message phrasing as addition.
        assert "Invalid number(s): 'abc', 'xyz'" in text

    def test_bare_sub_word_is_not_documented_as_a_trigger(self):
        # The old bare-word "sub"/"subtract" subcommand trigger must not
        # be documented as *working* anymore -- only the explicit
        # --subtract flag is. (The README may still mention the bare word
        # to explain that it no longer triggers subtraction.)
        text = _read_readme()
        assert "subcommand" not in text.lower()
        assert re.search(r"python sum\.py sub 10 5 2\s*\n#\s*3", text) is None

    def test_addition_example_unchanged(self):
        # Guard against the new section accidentally perturbing the
        # pre-existing, exact-match addition example strings.
        text = _read_readme()
        assert "python sum.py 2 5 10" in text
        assert re.search(r"python sum\.py 2 5 10\s*\n#\s*17", text)


class TestPythonVersionRequirement:
    def test_states_minimum_python_version(self):
        text = _read_readme()
        assert "3.10" in text

    def test_states_it_explicitly_as_a_requirement(self):
        text = _read_readme()
        assert re.search(r"Python\s*3\.10", text)


class TestEncryptionRationale:
    def test_has_a_rationale_section(self):
        text = _read_readme()
        assert re.search(r"#+\s*.*[Nn]o data to encrypt.*rationale", text)

    def test_mentions_no_data_at_rest(self):
        text = _read_readme()
        assert "at rest" in text.lower()

    def test_mentions_no_data_in_transit(self):
        text = _read_readme()
        assert "in transit" in text.lower()

    def test_explains_why_no_separate_encryption_controls(self):
        text = _read_readme()
        lower = text.lower()
        assert "no data" in lower or "no persist" in lower or "never persists" in lower


class TestInstallAndRunInstructions:
    def test_references_real_package_name(self):
        text = _read_readme()
        assert "core-addition-cli" in text

    def test_documents_running_tests(self):
        text = _read_readme()
        assert "pytest" in text
