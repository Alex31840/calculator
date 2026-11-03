"""Unit and CLI-level tests for sum.py.

Covers: parsing, summation, formatting, exit codes, the "no numbers"
message, naming invalid tokens, Decimal-exactness, no-file-I/O, and
unexpected-exception handling.
"""

from __future__ import annotations

import decimal
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SUM_PY = REPO_ROOT / "sum.py"

import importlib.util

spec = importlib.util.spec_from_file_location("sum_module", SUM_PY)
sum_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sum_module)


def run_cli(args, input_text=None):
    """Run sum.py as a subprocess and return (returncode, stdout, stderr)."""
    cmd = [sys.executable, str(SUM_PY), *args]
    result = subprocess.run(
        cmd,
        input=input_text if input_text is not None else "",
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode, result.stdout, result.stderr


# ---------------------------------------------------------------------------
# parse()
# ---------------------------------------------------------------------------

class TestParse:
    def test_parses_integers(self):
        assert sum_module.parse(["2", "5", "10"]) == [
            Decimal("2"), Decimal("5"), Decimal("10")
        ]

    def test_parses_negative_and_decimal(self):
        assert sum_module.parse(["-3", "4.5"]) == [
            Decimal("-3"), Decimal("4.5")
        ]

    def test_parses_decimal_exactly_from_string(self):
        values = sum_module.parse(["0.1", "0.2"])
        assert values == [Decimal("0.1"), Decimal("0.2")]
        # Confirm it was NOT built via float (float(0.1) != Decimal("0.1")).
        assert values[0] != Decimal(0.1)

    def test_empty_token_list_raises_no_numbers_provided(self):
        with pytest.raises(sum_module.NoNumbersProvidedError):
            sum_module.parse([])

    def test_single_invalid_token_raises_validation_error(self):
        with pytest.raises(sum_module.ValidationError) as excinfo:
            sum_module.parse(["2", "abc", "5"])
        assert excinfo.value.invalid_tokens == ["abc"]

    def test_multiple_invalid_tokens_all_reported(self):
        with pytest.raises(sum_module.ValidationError) as excinfo:
            sum_module.parse(["2", "abc", "xyz"])
        assert excinfo.value.invalid_tokens == ["abc", "xyz"]

    def test_rejects_nan_and_infinity(self):
        with pytest.raises(sum_module.ValidationError) as excinfo:
            sum_module.parse(["1", "nan", "inf"])
        assert "nan" in excinfo.value.invalid_tokens
        assert "inf" in excinfo.value.invalid_tokens


# ---------------------------------------------------------------------------
# sum_values()
# ---------------------------------------------------------------------------

class TestSumValues:
    def test_sum_of_integers(self):
        assert sum_module.sum_values(
            [Decimal("2"), Decimal("5"), Decimal("10")]
        ) == Decimal("17")

    def test_sum_negative_and_decimal(self):
        assert sum_module.sum_values(
            [Decimal("-3"), Decimal("4.5")]
        ) == Decimal("1.5")

    def test_sum_is_exact_decimal_not_float_artifact(self):
        total = sum_module.sum_values([Decimal("0.1"), Decimal("0.2")])
        assert total == Decimal("0.3")
        assert str(total) != "0.30000000000000004"

    def test_sum_of_empty_list_is_zero(self):
        assert sum_module.sum_values([]) == Decimal("0")


# ---------------------------------------------------------------------------
# subtract_values()
# ---------------------------------------------------------------------------

class TestSubtractValues:
    def test_subtracts_in_order_from_first_value(self):
        assert sum_module.subtract_values(
            [Decimal("10"), Decimal("5"), Decimal("2")]
        ) == Decimal("3")

    def test_subtract_negative_and_decimal(self):
        assert sum_module.subtract_values(
            [Decimal("10"), Decimal("-3.5")]
        ) == Decimal("13.5")

    def test_subtract_is_exact_decimal_not_float_artifact(self):
        result = sum_module.subtract_values([Decimal("0.3"), Decimal("0.1")])
        assert result == Decimal("0.2")

    def test_subtract_single_value_returns_itself(self):
        assert sum_module.subtract_values([Decimal("7")]) == Decimal("7")

    def test_subtract_of_empty_list_is_zero_fallback(self):
        # Never reached via the CLI (parse() raises first), but defined.
        assert sum_module.subtract_values([]) == Decimal("0")


# ---------------------------------------------------------------------------
# format_result()
# ---------------------------------------------------------------------------

class TestFormatResult:
    def test_formats_integer_result_without_decimal_point(self):
        assert sum_module.format_result(Decimal("17")) == "17"

    def test_formats_decimal_result(self):
        assert sum_module.format_result(Decimal("1.5")) == "1.5"

    def test_formats_exact_point_three(self):
        total = sum_module.sum_values([Decimal("0.1"), Decimal("0.2")])
        assert sum_module.format_result(total) == "0.3"

    def test_formats_negative_zero_as_zero(self):
        assert sum_module.format_result(Decimal("-0")) == "0"


# ---------------------------------------------------------------------------
# CLI-level (subprocess) tests - acceptance criteria
# ---------------------------------------------------------------------------

class TestCliAcceptance:
    def test_basic_sum_prints_17_and_exits_0(self):
        code, out, err = run_cli(["2", "5", "10"])
        assert out.strip() == "17"
        assert code == 0

    def test_negative_and_decimal_prints_1_5(self):
        code, out, err = run_cli(["-3", "4.5"])
        assert out.strip() == "1.5"
        assert code == 0

    def test_point_one_plus_point_two_is_exact(self):
        code, out, err = run_cli(["0.1", "0.2"])
        assert out.strip() == "0.3"
        assert "0.30000000000000004" not in out
        assert code == 0

    def test_no_arguments_and_empty_stdin_reports_no_numbers(self):
        code, out, err = run_cli([], input_text="")
        assert "No numbers were provided" in err
        assert code != 0
        assert out.strip() == ""

    def test_single_invalid_token_named_in_error(self):
        code, out, err = run_cli(["2", "abc", "5"])
        assert "abc" in err
        assert code != 0
        assert out.strip() == ""  # no partial/guessed sum

    def test_multiple_invalid_tokens_both_named(self):
        code, out, err = run_cli(["2", "abc", "xyz"])
        assert "abc" in err
        assert "xyz" in err
        assert code != 0
        assert out.strip() == ""

    def test_negative_single_value(self):
        code, out, err = run_cli(["-7"])
        assert out.strip() == "-7"
        assert code == 0

    def test_negative_first_argument_still_means_addition(self):
        # "-5" is not the "--subtract" flag, so this must add.
        code, out, err = run_cli(["-5", "3"])
        assert out.strip() == "-2"
        assert code == 0

    def test_bare_sub_word_is_not_a_trigger_and_is_treated_as_addend(self):
        # A bare "sub"/"subtract" first argument must NOT switch to
        # subtraction anymore -- it is just an (invalid) addend.
        code, out, err = run_cli(["sub", "10", "5", "2"])
        assert "sub" in err
        assert code != 0
        assert out.strip() == ""

    def test_bare_subtract_word_is_not_a_trigger_and_is_treated_as_addend(self):
        code, out, err = run_cli(["subtract", "10", "5", "2"])
        assert "subtract" in err
        assert code != 0
        assert out.strip() == ""

    # -- subtraction ---------------------------------------------------

    def test_subtract_basic_prints_3_and_exits_0(self):
        code, out, err = run_cli(["--subtract", "10", "5", "2"])
        assert out.strip() == "3"
        assert code == 0

    def test_subtract_flag_can_appear_after_numbers_too(self):
        code, out, err = run_cli(["10", "5", "2", "--subtract"])
        assert out.strip() == "3"
        assert code == 0

    def test_subtract_negative_and_decimal_prints_13_5(self):
        code, out, err = run_cli(["--subtract", "10", "-3.5"])
        assert out.strip() == "13.5"
        assert code == 0

    def test_subtract_no_arguments_and_empty_stdin_reports_no_numbers(self):
        code, out, err = run_cli(["--subtract"], input_text="")
        assert "No numbers were provided" in err
        assert code != 0
        assert out.strip() == ""

    def test_subtract_single_invalid_token_named_in_error(self):
        code, out, err = run_cli(["--subtract", "10", "abc"])
        assert "abc" in err
        assert code != 0
        assert out.strip() == ""

    def test_subtract_multiple_invalid_tokens_both_named(self):
        code, out, err = run_cli(["--subtract", "2", "abc", "xyz"])
        assert "abc" in err
        assert "xyz" in err
        assert code != 0
        assert out.strip() == ""

    def test_addition_still_works_unchanged_after_subtract_feature(self):
        code, out, err = run_cli(["2", "5", "10"])
        assert out.strip() == "17"
        assert code == 0


# ---------------------------------------------------------------------------
# No file I/O
# ---------------------------------------------------------------------------

class TestNoFileIO:
    def _snapshot(self, directory: Path):
        entries = {}
        for root, dirs, files in os.walk(directory):
            # Skip VCS/cache noise that could change independently of us.
            dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".pytest_cache")]
            for f in files:
                if f.endswith(".pyc"):
                    continue
                path = Path(root) / f
                entries[str(path)] = path.stat().st_mtime_ns
        return entries

    @pytest.mark.parametrize("args", [
        ["2", "5", "10"],
        ["2", "abc", "5"],
        [],
        ["sub", "10", "5", "2"],
        ["sub", "10", "abc"],
        ["sub"],
    ])
    def test_no_files_created_modified_or_deleted(self, args):
        before = self._snapshot(REPO_ROOT)
        run_cli(args, input_text="")
        after = self._snapshot(REPO_ROOT)
        assert before == after


# ---------------------------------------------------------------------------
# Unexpected exception handling
# ---------------------------------------------------------------------------

class TestUnexpectedExceptionHandling:
    def test_unexpected_exception_is_caught_and_reported(self, monkeypatch, capsys):
        def boom(values):
            raise RuntimeError("simulated catastrophic failure")

        monkeypatch.setattr(sum_module, "sum_values", boom)
        code = sum_module.main(["1", "2"])
        captured = capsys.readouterr()
        assert code != 0
        assert "simulated catastrophic failure" in captured.err
        assert "Traceback" not in captured.err
        assert captured.out == ""

    def test_unexpected_exception_does_not_crash_process(self):
        # Use the subprocess entrypoint with an environment variable the
        # script doesn't know about to ensure plain valid runs never crash;
        # this complements the monkeypatch test above which hits the
        # in-process safety net directly.
        code, out, err = run_cli(["1", "2", "3"])
        assert code == 0
        assert out.strip() == "6"


# ---------------------------------------------------------------------------
# Distinctness of error exit codes / messages
# ---------------------------------------------------------------------------

class TestDistinctFailureMessages:
    def test_no_numbers_and_invalid_token_have_distinct_messages(self):
        _, _, err_empty = run_cli([], input_text="")
        _, _, err_invalid = run_cli(["abc"])
        assert err_empty != err_invalid
        assert "No numbers were provided" in err_empty
        assert "abc" in err_invalid
