import sys
from duper import RESET, BOLD, DIM, RED, YELLOW, GREEN

TOP_N = 10  # to display in terminal output
bar = "─" * 70


def format_group(i, g):
    lines = []
    lines.append(
        "#{:>2}  {}-line block  x{}  {} wasted lines  {:.0f}%  {}".format(
            i,
            g.line_count,
            len(g.occurrences),
            g.wasted_lines,
            g.similarity * 100,
            g.kind,
        )
    )
    for occ in g.occurrences:
        lines.append("      {}:{}".format(occ.file, occ.start_line))
    lines.append("")
    lines.append(g.preview())
    lines.append("─" * 70)
    return lines


def report(results, root, total_files, out_path, warnings=None):
    total_wasted = sum(g.wasted_lines for g in results)

    def score_colour(s):
        return GREEN if s >= 0.99 else YELLOW if s >= 0.85 else RED

    def wasted_colour(w):
        return RED if w >= 30 else YELLOW if w >= 10 else GREEN

    for path, e in warnings or []:
        print("{}[warn]{} {}: {}".format(YELLOW, RESET, path, e), file=sys.stderr)

    # SUMMARY
    print("\n{}{}{}".format(BOLD, "─" * 70, RESET))
    print("{}  scan{}  --  {}".format(BOLD, RESET, root))
    print(bar)
    print("  Files scanned   : {}{}{}".format(GREEN, total_files, RESET))
    print("  Duplicate groups: {}{}{}".format(GREEN, len(results), RESET))
    print(
        "  Wasted lines    : {}{}{}".format(
            wasted_colour(total_wasted), total_wasted, RESET
        )
    )
    print("  Full report     : {}{}{}".format(GREEN, out_path, RESET))
    print(bar)

    if not results:
        print(
            "  {}No duplicate blocks found -- clean codebase!{}\n".format(GREEN, RESET)
        )
        return

    # print top N to terminal with colour
    for i, g in enumerate(results[:TOP_N], 1):
        print(
            "{}{}#{:>2}  {}-line block  x{}  {} wasted lines  {}{}{:.0f}%{}  {}{}{}".format(
                BOLD,
                wasted_colour(g.wasted_lines),
                i,
                g.line_count,
                len(g.occurrences),
                g.wasted_lines,
                score_colour(g.similarity),
                BOLD,
                g.similarity * 100,
                RESET,
                DIM,
                g.kind,
                RESET,
            )
        )
        for occ in g.occurrences:
            print("      {}{}:{}{}".format(GREEN, occ.file, occ.start_line, RESET))
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
