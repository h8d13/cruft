import sys

from duper import BOLD, DIM, GREEN, RED, RESET, YELLOW

TOP_N = 10  # to display in terminal output
bar = "─" * 70

def _format_occurrences(g, pre="", post=""):
    return [
        f"      {pre}{occ.file}:{occ.start_line}{post}"
        for occ in g.occurrences
    ]

def format_group(i, g):
    lines = [
        f"#{i:>2}  {g.line_count}-line block  x{len(g.occurrences)}"
        f"  {g.wasted_lines} wasted lines  {g.similarity * 100:.0f}%  {g.kind}"
    ]
    lines.extend(_format_occurrences(g))
    lines.append("")
    lines.append(g.preview())
    lines.append("─" * 70)
    return lines

def report(results, root, total_files, out_path, warnings=None):
    total_wasted = sum(g.wasted_lines for g in results)

    for path, e in warnings or []:
        print(f"{YELLOW}[warn]{RESET} {path}: {e}", file=sys.stderr)

    # SUMMARY
    print("\n{}{}{}".format(BOLD, "─" * 70, RESET))
    print(f"{BOLD}  scan{RESET}  --  {root}")
    print(bar)
    print(f"  Files scanned   : {GREEN}{total_files}{RESET}")
    print(f"  Duplicate groups: {GREEN}{len(results)}{RESET}")
    wasted_c = RED if total_wasted >= 30 else YELLOW if total_wasted >= 10 else GREEN
    print(f"  Wasted lines    : {wasted_c}{total_wasted}{RESET}")
    print(f"  Full report     : {GREEN}{out_path}{RESET}")
    print(bar)

    if not results:
        print(
            f"  {GREEN}No duplicate blocks found -- clean codebase!{RESET}\n"
        )
        return

    # print top N to terminal with colour
    for i, g in enumerate(results[:TOP_N], 1):
        sc = GREEN if g.similarity >= 0.99 else YELLOW if g.similarity >= 0.85 else RED
        wc = RED if g.wasted_lines >= 30 else YELLOW if g.wasted_lines >= 10 else GREEN
        print(

                f"{BOLD}{wc}#{i:>2}  {g.line_count}-line block"
                f"  x{len(g.occurrences)}  {g.wasted_lines} wasted lines"
                f"  {sc}{BOLD}{g.similarity * 100:.0f}%{RESET}  {DIM}{g.kind}{RESET}"

        )
        for line in _format_occurrences(g, GREEN, RESET):
            print(line)
        print("\n{}{}{}\n{}\n".format(DIM, g.preview(), RESET, "─" * 70))

    if len(results) > TOP_N:
        print(
            f"  {DIM}... and {len(results) - TOP_N} more -- see {out_path}{RESET}"
        )

    # WRITE THE FULL TXT
    with open(str(out_path), "w") as fh:
        fh.write(f"scan report -- {root}\n")
        fh.write(
            f"files: {total_files}  groups: {len(results)}"
            f"  wasted lines: {total_wasted}\n"
        )
        fh.write("─" * 70 + "\n\n")
        for i, g in enumerate(results, 1):
            for line in format_group(i, g):
                fh.write(line + "\n")
            fh.write("\n")
