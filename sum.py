#!/usr/bin/env python3
"""sum.py - single-file addition / subtraction CLI.

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
  * CLI entrypoint      -> main()
  * Input Parser        -> parse(tokens)
  * Summation Engine    -> sum_values(values)
  * Subtraction Engine  -> subtract_values(values)
  * Output Formatter    -> format_result(value)

All arithmetic uses decimal.Decimal constructed directly from the original
input strings (never via float), so that e.g. 0.1 + 0.2 renders as exactly
0.3 rather than 0.30000000000000004.

Operation selection
--------------------
By default (no "--subtract" flag anywhere in the arguments) the script
adds its numbers, exactly as before:

    python sum.py 2 5 10          # -> 17

To subtract instead, pass an explicit "--subtract" flag. The remaining
arguments are subtracted in order, left to right, starting from the first
number (not from zero):

    python sum.py --subtract 10 5 2      # -> 3   (10 - 5 - 2)
    python sum.py --subtract 10 -3.5     # -> 13.5

Subtraction is never triggered by a bare word like "sub" or "subtract" as
the first argument (e.g. "python sum.py sub 10 5 2" just adds the three
values "sub", 10, 5, 2 — which fails to parse since "sub" is not a
number). Only the explicit "--subtract" flag switches to subtraction, so
there is no accidental-trigger surface: a plain positional argument can
never be mistaken for the flag, and negative numbers (e.g. "python sum.py
-5 3") continue to work for the addition path unchanged.
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


def subtract_values(values: list[Decimal]) -> Decimal:
    """Return the exact Decimal result of subtracting values[1:] from
    values[0], in order: values[0] - values[1] - ... - values[n-1].

    Unlike addition, subtraction has no neutral starting element, so the
    accumulator starts at the *first* value rather than at zero (folding
    from zero would incorrectly negate every term).

    In practice this is only ever called with a non-empty list: parse()
    raises NoNumbersProvidedError before an empty list can reach here,
    same as for the addition path. If it is ever called with an empty
    list directly (e.g. in a unit test), it returns Decimal("0") as a
    defined-but-unreached fallback.
    """
    if not values:
        return Decimal("0")
    result = values[0]
    for value in values[1:]:
        result -= value
    return result


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


_SUBTRACT_FLAGS = ("--subtract",)


def _read_interactive_tokens(verb: str = "add") -> list[str]:
    """When no CLI arguments are given, try to read numbers from stdin
    (e.g. an interactive prompt). Returns the tokens found, or an empty
    list if stdin has nothing usable (closed/empty).

    `verb` only tailors the prompt text ("add"/"subtract"); it has no
    effect on parsing behaviour.
    """
    if sys.stdin is None or sys.stdin.closed:
        return []
    try:
        if not sys.stdin.isatty():
            # Non-interactive stdin (pipe/redirect/empty): read whatever
            # is available, if anything.
            data = sys.stdin.read()
        else:
            # Interactive terminal: prompt the user once.
            sys.stderr.write(
                f"No numbers were provided as arguments. "
                f"Enter numbers to {verb} separated by spaces: "
            )
            sys.stderr.flush()
            data = sys.stdin.readline()
    except (OSError, ValueError):
        return []
    return data.split()


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns the process exit code (does not call
    sys.exit itself, to keep it testable).

    Dispatches between addition (default) and subtraction: if an explicit
    "--subtract" flag is present among the arguments, it is removed from
    the list and the remaining arguments are subtracted in order (first
    value minus the rest); otherwise all arguments are treated as numbers
    to add, exactly as before. There is no bare-word trigger: a plain
    positional first argument (even the literal words "sub"/"subtract")
    is never special-cased, so `python sum.py -5 3` (a negative number
    first) and `python sum.py sub 10 5 2` (treated as four values to add,
    which fails because "sub" is not a number) behave exactly like any
    other addition invocation.
    """
    args = sys.argv[1:] if argv is None else argv
    args = list(args)

    subtract = False
    if any(flag in args for flag in _SUBTRACT_FLAGS):
        subtract = True
        args = [arg for arg in args if arg not in _SUBTRACT_FLAGS]

    try:
        tokens = args
        if not tokens:
            tokens = _read_interactive_tokens(
                "subtract" if subtract else "add"
            )

        values = parse(tokens)
        if subtract:
            result = subtract_values(values)
        else:
            result = sum_values(values)
        print(format_result(result))
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
