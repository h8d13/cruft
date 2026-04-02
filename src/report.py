import sys
from duper import RESET, BOLD, DIM, RED, YELLOW, GREEN

TOP_N = 10  # to display in terminal output
bar = "─" * 70


def _format_occurrences(g, pre="", post=""):
    return [
        "      {}{}:{}{}".format(pre, occ.file, occ.start_line, post)
        for occ in g.occurrences
    ]


def format_group(i, g):
    lines = [
        "#{:>2}  {}-line block  x{}  {} wasted lines  {:.0f}%  {}".format(
            i,
            g.line_count,
            len(g.occurrences),
            g.wasted_lines,
            g.similarity * 100,
            g.kind,
        )
    ]
    lines.extend(_format_occurrences(g))
    lines.append("")
    lines.append(g.preview())
    lines.append("─" * 70)
    return lines


def report(results, root, total_files, out_path, warnings=None):
    total_wasted = sum(g.wasted_lines for g in results)

    for path, e in warnings or []:
        print("{}[warn]{} {}: {}".format(YELLOW, RESET, path, e), file=sys.stderr)

    # SUMMARY
    print("\n{}{}{}".format(BOLD, "─" * 70, RESET))
    print("{}  scan{}  --  {}".format(BOLD, RESET, root))
    print(bar)
    print("  Files scanned   : {}{}{}".format(GREEN, total_files, RESET))
    print("  Duplicate groups: {}{}{}".format(GREEN, len(results), RESET))
    wasted_c = RED if total_wasted >= 30 else YELLOW if total_wasted >= 10 else GREEN
    print("  Wasted lines    : {}{}{}".format(wasted_c, total_wasted, RESET))
    print("  Full report     : {}{}{}".format(GREEN, out_path, RESET))
    print(bar)

    if not results:
        print(
            "  {}No duplicate blocks found -- clean codebase!{}\n".format(GREEN, RESET)
        )
        return

    # print top N to terminal with colour
    for i, g in enumerate(results[:TOP_N], 1):
        sc = GREEN if g.similarity >= 0.99 else YELLOW if g.similarity >= 0.85 else RED
        wc = RED if g.wasted_lines >= 30 else YELLOW if g.wasted_lines >= 10 else GREEN
        print(
            (
                "{}{}#{:>2}  {}-line block  x{}  {} wasted lines  {}{}{:.0f}%{}  {}{}{}"
            ).format(
                BOLD,
                wc,
                i,
                g.line_count,
                len(g.occurrences),
                g.wasted_lines,
                sc,
                BOLD,
                g.similarity * 100,
                RESET,
                DIM,
                g.kind,
                RESET,
            )
        )
        for line in _format_occurrences(g, GREEN, RESET):
            print(line)
        print("\n{}{}{}\n{}\n".format(DIM, g.preview(), RESET, "─" * 70))

    if len(results) > TOP_N:
        print(
            "  {}... and {} more -- see {}{}".format(
                DIM, len(results) - TOP_N, out_path, RESET
            )
        )

    # WRITE THE FULL TXT
    with open(str(out_path), "w") as fh:
        fh.write("scan report -- {}\n".format(root))
        fh.write(
            "files: {}  groups: {}  wasted lines: {}\n".format(
                total_files, len(results), total_wasted
            )
        )
        fh.write("─" * 70 + "\n\n")
        for i, g in enumerate(results, 1):
            for line in format_group(i, g):
                fh.write(line + "\n")
            fh.write("\n")
