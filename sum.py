#!/usr/bin/env python3
"""sum.py - single-file addition CLI.

Security/compliance note (encryption-everywhere rationale)
------------------------------------------------------------
This tool is a single short-lived process invoked synchronously from a
terminal on a bare VM. It:
  * performs no file I/O (it never reads from or writes to disk),
  * performs no network I/O (it never opens a socket or makes a call out),
  * does not log, cache, or otherwise persist the numbers a user enters.
Because no data from this program is ever written to a persistence layer
and no data ever travels over a network, there is structurally no "data at
rest" or "data in transit" produced by this tool for the organisation's
encryption-everywhere policy to apply to. The policy is satisfied by the
absence of the data it would otherwise protect, not by adding encryption
machinery that would have nothing to encrypt.

Interface / contract
---------------------
  * CLI entrypoint   -> main()
  * Input Parser     -> parse(tokens)
  * Summation Engine -> sum_values(values)
  * Output Formatter -> format_result(value)

All arithmetic uses decimal.Decimal constructed directly from the original
input strings (never via float), so that e.g. 0.1 + 0.2 renders as exactly
0.3 rather than 0.30000000000000004.
"""

from __future__ import annotations

import decimal
import sys
from decimal import Decimal


class ValidationError(Exception):
    """Raised when one or more input tokens cannot be parsed as numbers.

    Attributes:
        invalid_tokens: the list of original tokens that failed to parse.
    """

    def __init__(self, invalid_tokens: list[str]):
        self.invalid_tokens = list(invalid_tokens)
        joined = ", ".join(repr(t) for t in self.invalid_tokens)
        super().__init__(f"Invalid number(s): {joined}")


class NoNumbersProvidedError(Exception):
    """Raised when there are no numbers to sum at all."""

    def __init__(self, message: str = "No numbers were provided."):
        super().__init__(message)


def parse(tokens: list[str]) -> list[Decimal]:
    """Parse a list of string tokens into a list of Decimal values.

    - If `tokens` is empty, raises NoNumbersProvidedError (distinct from
      the invalid-token case).
    - If any token fails to parse as a Decimal, raises ValidationError
      carrying *all* invalid tokens (not just the first).
    - Never constructs Decimal via float; always builds directly from the
      original string.
    """
    if not tokens:
        raise NoNumbersProvidedError()

    values: list[Decimal] = []
    invalid: list[str] = []

    for token in tokens:
        stripped = token.strip()
        try:
            if stripped == "":
                raise decimal.InvalidOperation(token)
            value = Decimal(stripped)
            if not value.is_finite():
                # Reject NaN / Infinity / -Infinity as "not a number" for
                # the purposes of this addition CLI.
                raise decimal.InvalidOperation(token)
        except (decimal.InvalidOperation, ValueError):
            invalid.append(token)
        else:
            values.append(value)

    if invalid:
        raise ValidationError(invalid)

    return values


def sum_values(values: list[Decimal]) -> Decimal:
    """Return the exact Decimal sum of the given values."""
    total = Decimal("0")
    for value in values:
        total += value
    return total


def format_result(value: Decimal) -> str:
    """Format a Decimal result for display, normalising trailing zeros
    while keeping an exact (non-scientific-notation) representation."""
    normalized = value.normalize()
    # normalize() can turn whole numbers into exponential form (e.g. 1E+2);
    # convert back to plain fixed-point notation for human-friendly output.
    sign, digits, exponent = normalized.as_tuple()
    if isinstance(exponent, int) and exponent > 0:
        normalized = normalized.quantize(Decimal(1))
    text = format(normalized, "f")
    if text == "-0":
        text = "0"
    return text


def _read_interactive_tokens() -> list[str]:
    """When no CLI arguments are given, try to read numbers from stdin
    (e.g. an interactive prompt). Returns the tokens found, or an empty
    list if stdin has nothing usable (closed/empty)."""
    if sys.stdin is None or sys.stdin.closed:
        return []
    try:
        if not sys.stdin.isatty():
            # Non-interactive stdin (pipe/redirect/empty): read whatever
            # is available, if anything.
            data = sys.stdin.read()
        else:
            # Interactive terminal: prompt the user once.
            sys.stderr.write("No numbers were provided as arguments. "
                              "Enter numbers separated by spaces: ")
            sys.stderr.flush()
            data = sys.stdin.readline()
    except (OSError, ValueError):
        return []
    return data.split()


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns the process exit code (does not call
    sys.exit itself, to keep it testable)."""
    args = sys.argv[1:] if argv is None else argv

    try:
        tokens = list(args)
        if not tokens:
            tokens = _read_interactive_tokens()

        values = parse(tokens)
        total = sum_values(values)
        print(format_result(total))
        return 0

    except NoNumbersProvidedError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    except ValidationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        # Never let an unexpected exception surface as a raw traceback.
        print(f"Error: an unexpected error occurred: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
