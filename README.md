# core-addition-cli

A single-file, standard-library-only Python command-line tool that adds
(and, via an explicit `--subtract` flag, subtracts) numbers together using
exact `decimal.Decimal` arithmetic.

## Requirements

* **Python 3.10 or later** (see `requires-python = ">=3.10"` in
  `pyproject.toml`). No third-party packages are required to run it.

## Install / build

There is nothing to build or install — `sum.py` is a single, dependency-free
script. Just make sure a Python 3.10+ interpreter is on your `PATH`:

```sh
python3 --version   # must report 3.10 or higher
```

Optionally, if you also want to run the test suite, create a project-local
virtual environment (see "Running the tests" below).

## Usage

### Argument-passing mode

Pass the numbers to add as command-line arguments:

```sh
python sum.py 2 5 10
# 17

python sum.py -3 4.5
# 1.5

python sum.py 0.1 0.2
# 0.3   (exact — not 0.30000000000000004)
```

### Interactive-prompt mode

If you run it with no arguments, it tries to read numbers from stdin
instead. When stdin is an interactive terminal, it prints a prompt to
stderr and reads one line of space-separated numbers:

```sh
$ python sum.py
No numbers were provided as arguments. Enter numbers separated by spaces: 2 5 10
17
```

When stdin is *not* a terminal (e.g. piped or redirected), the same
no-argument invocation reads whatever numbers are available from stdin
without printing the interactive prompt:

```sh
echo "2 5 10" | python sum.py
# 17
```

### Empty-input case

If no arguments are given *and* stdin has nothing usable (e.g. it is
closed, empty, or immediately EOF), the script prints a clear message to
stderr and exits non-zero:

```sh
python sum.py < /dev/null
# stderr: Error: No numbers were provided.
```

### Invalid-input case

Invalid tokens are reported by name, and *all* invalid tokens are reported
together rather than just the first one found:

```sh
python sum.py 2 abc xyz
# stderr: Error: Invalid number(s): 'abc', 'xyz'
```

No sum is printed to stdout when any input token is invalid — there is no
partial or "best guess" result.

### Subtraction

In addition to summing numbers, `sum.py` can also subtract them. Pass an
explicit `--subtract` flag anywhere among the arguments; the remaining
numbers are subtracted in order, left to right, starting from the first
one (not from zero):

```sh
python sum.py --subtract 10 5 2
# 3   (10 - 5 - 2)
```

Negative numbers and decimals work the same way as for addition, and the
result is exact `Decimal` arithmetic — never float:

```sh
python sum.py --subtract 10 -3.5
# 13.5
```

Subtraction is **never** triggered by a bare word like `sub` or
`subtract` as the first argument — `python sum.py sub 10 5 2` is treated
as an addition invocation with `"sub"` as one of the tokens to parse
(which fails, since `"sub"` is not a number). Only the explicit
`--subtract` flag switches to subtraction, so there is no
accidental-trigger surface, and plain addition invocations like
`python sum.py -5 3` are unaffected.

Interactive-prompt mode, empty-input handling, and invalid-token
reporting all work identically to addition:

```sh
$ python sum.py --subtract
No numbers were provided as arguments. Enter numbers to subtract separated by spaces: 10 5 2
3
```

```sh
python sum.py --subtract < /dev/null
# stderr: Error: No numbers were provided.
```

```sh
python sum.py --subtract 10 abc xyz
# stderr: Error: Invalid number(s): 'abc', 'xyz'
```

As with addition, no result is printed when any input token is invalid,
and all invalid tokens are reported together rather than just the first.

## Exit codes

| Code | Meaning                                             |
|------|------------------------------------------------------|
| 0    | Success — the sum was computed and printed to stdout |
| 1    | No numbers were provided (empty argv and empty/absent stdin) |
| 2    | One or more input tokens could not be parsed as numbers |
| 3    | An unexpected internal error occurred (caught, reported, never a raw traceback) |

## Design notes

* **Decimal, never float.** Every number is built with
  `decimal.Decimal(token_string)` directly from the original command-line
  text, never via `float(...)`. This avoids binary floating-point
  representation error, so `0.1 + 0.2` prints as exactly `0.3`.
* **Single file, standard library only.** `sum.py` has no third-party
  dependencies, so there is nothing to install and no supply-chain surface
  to audit beyond the Python interpreter itself.
* **No file I/O, no network I/O, no logging of entered numbers.** The
  script only reads its `argv`/`stdin` and writes to `stdout`/`stderr`. It
  never opens a file or a socket.

### "No data to encrypt" rationale

The organisation's security policy requires encryption of sensitive data
both at rest and in transit. This tool is a short-lived process invoked
synchronously from a terminal on a bare VM — it starts, computes a sum,
and exits. Because it:

1. never persists anything to disk (no "at rest" data is ever created),
   and
2. never communicates over a network (no "in transit" data is ever
   created),

there is **structurally no data for the encryption-everywhere policy to
apply to**. The policy's goal — protecting data at rest and in transit —
is satisfied trivially and robustly by the absence of such data, which is
a stronger guarantee than encrypting data that could otherwise exist. This
reasoning is also recorded as a comment at the top of `sum.py`.

## Running the tests

```sh
python -m venv .venv && . .venv/bin/activate
pip install pytest
pytest
```
