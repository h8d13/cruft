#!/usr/bin/env python3
"""
DUPER Duplicate & near-duplicate code detector

A couple of notable features:
- Respect gitignores glob
- Fuzzy matching
- Skip binary files
- Skip (.something) files/dirs

"""

import hashlib
import re
from difflib import SequenceMatcher
from pathlib import Path

# SETTINGS
MIN_LINES = 3  # wont get matched bellow 2
FUZZY_THRESHOLD = 0.66  # min similarity to report a near-duplicate group
EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
}  # else any valid text file BUT skip binaries
# and skip the following (as stem)
SKIP_FILES = {
    "LICENSE",
    "LICENCE",
    "CHANGELOG",
    "NOTICE",
    "AUTHORS",
    "COPYING",
}
SKIP_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    "dist",
    "build",
}  # also respect gitignore if found in the target path


def respect_gitignore(root):
    gitignore = Path(root) / ".gitignore"
    if not gitignore.is_file():
        return None

    def _to_re(pat, anchored):
        res, i = [], 0
        while i < len(pat):
            if pat[i : i + 2] == "**":
                res.append(".*")
                i += 2
                if i < len(pat) and pat[i] == "/":
                    i += 1
            elif pat[i] in ("*", "?"):
                res.append("[^/]*" if pat[i] == "*" else "[^/]")
                i += 1
            elif pat[i] == "[":
                j = i + 1
                if j < len(pat) and pat[j] in "!^":
                    j += 1
                if j < len(pat) and pat[j] == "]":
                    j += 1
                while j < len(pat) and pat[j] != "]":
                    j += 1
                res.append(pat[i : j + 1])
                i = j + 1
            else:
                res.append(re.escape(pat[i]))
                i += 1
        body = "".join(res)
        prefix = "^" if anchored else r"(^|.*/)"
        return re.compile(prefix + body + r"(/.*)?$")

    rules = []
    for raw in gitignore.read_text(errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        if negated:
            line = line[1:]
        dir_only = line.endswith("/")
        line = line.strip("/")
        anchored = "/" in line or line.startswith("/")
        if line.startswith("/"):
            line = line[1:]
        try:
            rules.append((negated, dir_only, _to_re(line, anchored)))
        except re.error:
            pass

    def matches(path):
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            return False
        is_dir = path.is_dir()
        ignored = False
        for negated, dir_only, regex in rules:
            if dir_only and not is_dir:
                continue
            if regex.match(rel):
                ignored = not negated
        return ignored

    return matches


# ANSI

## States
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
## Colors
RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"


# STRUCS
class Occurrence:
    def __init__(
        self, file, start_line, end_line, lines, norm_lines=None, fuzzy_lines=None
    ):
        self.file = file
        self.start_line = start_line
        self.end_line = end_line
        self.lines = lines  # original lines, for display
        self.norm_lines = norm_lines  # exact-normalised lines, for scoring
        self.fuzzy_lines = fuzzy_lines  # fuzzy-normalised lines, for fuzzy scoring


class DuplicateGroup:
    def __init__(self, lines, similarity):
        self.lines = lines  # canonical (first seen) raw lines
        self.occurrences = []
        self.similarity = similarity  # 1.0 = exact, <1.0 = fuzzy

    @property
    def line_count(self):
        return len(self.lines)

    @property
    def wasted_lines(self):
        return self.line_count * (len(self.occurrences) - 1)

    @property
    def kind(self):
        return "exact" if self.similarity >= 0.99 else "fuzzy"

    def preview(self, max_lines=5):
        snippet = self.lines[:max_lines]
        tail = (
            "\n    ... ({} more lines)".format(self.line_count - max_lines)
            if self.line_count > max_lines
            else ""
        )
        return "    " + "    ".join(snippet).rstrip() + tail


# COMM
_LINE_COMMENT_PREFIXES = ("//", "#", "--", ";", "%")
_BLOCK_MARKERS = [
    ("/*", "*/"),
    ("<!--", "-->"),
    ("--[[", "]]"),
    ("{-", "-}"),
    ('"""', '"""'),
    ("'''", "'''"),
]


def strip_comments(raw_lines):
    result = []
    in_block = None
    for line in raw_lines:
        s = line.rstrip("\n\r")
        if in_block is not None:
            idx = s.find(in_block)
            if idx == -1:
                result.append("")
                continue
            s = s[idx + len(in_block) :]
            in_block = None
        clean = s
        while True:
            earliest_pos, earliest_open, earliest_close = len(clean), None, None
            for open_m, close_m in _BLOCK_MARKERS:
                p = clean.find(open_m)
                if p != -1 and p < earliest_pos:
                    earliest_pos, earliest_open, earliest_close = p, open_m, close_m
            line_pos, line_marker = len(clean), None
            for prefix in _LINE_COMMENT_PREFIXES:
                p = clean.find(prefix)
                if p != -1 and p < line_pos:
                    line_pos, line_marker = p, prefix
            if earliest_open is None and line_marker is None:
                break
            if line_marker is not None and line_pos <= earliest_pos:
                clean = clean[:line_pos]
                break
            after_open = clean[earliest_pos + len(earliest_open) :]
            close_idx = after_open.find(earliest_close)
            if close_idx == -1:
                clean = clean[:earliest_pos]
                in_block = earliest_close
                break
            else:
                clean = (
                    clean[:earliest_pos] + after_open[close_idx + len(earliest_close) :]
                )
        result.append(clean)
    return result


# NORM
def norm_exact(line):
    return line.strip()


_STR_RE = re.compile(r'(["\'])(?:\\.|[^\\])*?\1')
_NUM_RE = re.compile(r"\b\d+(\.\d+)?\b")
_WORD_RE = re.compile(r"\b[A-Za-z_]\w*\b")


def norm_fuzzy(line):
    s = line.strip()
    s = _STR_RE.sub("STR", s)
    s = _NUM_RE.sub("NUM", s)
    s = _WORD_RE.sub("ID", s)
    return s


def hash_lines(lines):
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def similarity(a_lines, b_lines):
    a = " ".join(line.strip() for line in a_lines)
    b = " ".join(line.strip() for line in b_lines)
    return SequenceMatcher(None, a, b).ratio()


# SCAN
def is_binary(path):
    try:
        return b"\x00" in path.read_bytes()[:8192]
    except OSError:
        return True


def collect_files(root, spec=None):
    files = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.stem in SKIP_FILES:
            # note use stem so that we catch extensions
            continue
        if spec and spec(path):
            continue
        if (
            path.is_file()
            and (
                path.suffix.lower() in EXTENSIONS
                or (not path.suffix and not path.name.startswith("."))
            )
            and not is_binary(path)
        ):
            files.append(path)
    return sorted(files)


def scan(files):
    exact_index = {}  # exact_hash  -> DuplicateGroup
    fuzzy_index = {}  # fuzzy_hash  -> DuplicateGroup
    raw_cache = {}  # path -> list of raw lines (for group extension)
    warnings = []
    total = len(files)

    for i, path in enumerate(files, 1):
        pct = i / total * 100
        filled = int(25 * i / total)
        bar = "\u2588" * filled + "\u2591" * (25 - filled)
        label = path.name[:35].ljust(35)
        print(
            "\r  [{}] {:5.1f}%  {}{}{}".format(bar, pct, GREEN, label, RESET),
            end="",
            flush=True,
        )

        try:
            raw = path.read_text(errors="replace").splitlines(keepends=True)
        except OSError as e:
            warnings.append((path, e))  # this would mostly be perms issue
            continue

        raw_cache[path] = raw
        stripped = strip_comments(raw)
        exact_norm = [norm_exact(line) for line in stripped]
        fuzzy_norm = [norm_fuzzy(line) for line in stripped]
        n = len(raw)

        for start in range(n - MIN_LINES + 1):
            e_chunk = exact_norm[start : start + MIN_LINES]
            f_chunk = fuzzy_norm[start : start + MIN_LINES]
            block = raw[start : start + MIN_LINES]  # original lines for display

            if not e_chunk[0] or sum(bool(line) for line in e_chunk) < MIN_LINES * 0.6:
                continue

            eh = hash_lines(e_chunk)
            occ = Occurrence(
                path, start + 1, start + MIN_LINES, block, e_chunk, f_chunk
            )
            occ.exact_hash = eh

            # Exact pass
            exact_index.setdefault(eh, DuplicateGroup(block, 1.0)).occurrences.append(
                occ
            )

            # Fuzzy pass... only index if not already an exact match
            fh = hash_lines(f_chunk)
            if fh != eh:
                fuzzy_index.setdefault(
                    fh, DuplicateGroup(block, 0.0)
                ).occurrences.append(occ)

    print()

    # Exact duplicates seed with MIN_LINES blocks, then grow each one
    seeds = [g for g in exact_index.values() if len(g.occurrences) > 1]

    # Build lookup: frozenset(file, start_line) -> group, so we can detect
    # whether the "next shifted" group also exists (meaning the block can grow)
    sig_map = {}
    for g in seeds:
        sig = frozenset((o.file, o.start_line) for o in g.occurrences)
        sig_map[sig] = g

    absorbed = set()
    for g in seeds:
        if id(g) in absorbed:
            continue
        # Try to extend by one line at a time
        while True:
            # What would the next seed look like? Each occurrence shifted by 1
            next_sig = frozenset(
                (o.file, o.start_line + (g.line_count - MIN_LINES + 1))
                for o in g.occurrences
            )
            if next_sig not in sig_map:
                break
            neighbour = sig_map[next_sig]
            if id(neighbour) in absorbed:
                break
            # Grow: append the extra line from the first occurrence
            occ0 = g.occurrences[0]
            file_raw = raw_cache.get(occ0.file, [])
            new_line_idx = occ0.end_line  # end_line is 1-based; index = end_line
            if new_line_idx >= len(file_raw):
                break
            g.lines = g.lines + [file_raw[new_line_idx]]
            for occ in g.occurrences:
                occ.end_line += 1
            absorbed.add(id(neighbour))

    results = [g for g in seeds if id(g) not in absorbed]

    # Fuzzy duplicates: same structural hash, different exact hash.
    # A fuzzy group is only interesting when its occurrences come from at least
    # two DIFFERENT exact groups meaning "these distinct blocks are all the
    # same pattern".

    # If they all share one exact hash they're already an exact
    # duplicate. We pick one representative per exact-group (the first seen) so
    # the result shows one entry per structurally-similar variant.

    for g in fuzzy_index.values():
        if len(g.occurrences) < 2:
            continue
        # Bucket occurrences by their exact hash
        by_exact = {}
        for o in g.occurrences:
            by_exact.setdefault(o.exact_hash, []).append(o)
        # Need 2+ distinct exact groups to be worth reporting
        if len(by_exact) < 2:
            continue
        # One representative occurrence per exact-group
        reps = [occs[0] for occs in by_exact.values()]
        g.occurrences = reps
        # Score = avg lexical similarity on exact-normalised lines vs first rep
        ref = reps[0].norm_lines or reps[0].lines
        scores = [
            similarity(ref, o.norm_lines if o.norm_lines else o.lines) for o in reps[1:]
        ]
        g.similarity = sum(scores) / len(scores)
        if g.similarity >= FUZZY_THRESHOLD:
            results.append(g)

    return sorted(
        results, key=lambda g: (g.wasted_lines, g.similarity), reverse=True
    ), warnings
