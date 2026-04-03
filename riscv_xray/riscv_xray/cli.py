"""cli.py - riscv-xray command-line interface."""

import argparse
import shutil
import sys
import importlib.util
from pathlib import Path

from . import __version__
from . import runner, profiler, classifier, recommender, report


def cmd_profile(args):
    """Run extension profiling on a binary."""
    binary = args.binary
    binary_args = args.args.split() if args.args else []
    fmt = args.output
    timeout = args.timeout

    print(f"  riscv-xray - profiling '{Path(binary).name}'...", file=sys.stderr)

    # Step 1: Run under QEMU
    try:
        mnemonics, mode = runner.run(binary, binary_args, timeout=timeout)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        from collections import Counter
        counts = Counter(mnemonics)
        print(f"\n[verbose] Top 20 mnemonics:")
        for mnem, cnt in counts.most_common(20):
            print(f"  {mnem:<20} {cnt:>6}")
        print()

    if not mnemonics:
        print("Warning: no instructions captured. Check that the binary runs correctly under qemu-riscv64.")

    # Step 2: Classify
    data = classifier.classify(mnemonics)

    # Step 3: Get backend
    backend = f"{profiler.get_backend()} ({mode})"

    # Step 4: Recommendations
    recs = recommender.recommend(data, Path(binary).name)

    # Step 5: Render and print
    output = report.render(Path(binary).name, data, recs, backend, fmt=fmt)
    print(output)


def _profile_one(binary, timeout=60):
    """Profile a single binary, return (data, mode, name)."""
    name = Path(binary).name
    print(f"  Profiling '{name}'...", file=sys.stderr)
    mnemonics, mode = runner.run(binary, [], timeout=timeout)
    data = classifier.classify(mnemonics)
    return data, mode, name


def cmd_compare(args):
    """Compare two binaries side-by-side."""
    from .extensions import EXTENSION_ORDER

    timeout = getattr(args, "timeout", 60)
    fmt = getattr(args, "output", "text")

    try:
        data1, mode1, name1 = _profile_one(args.binary1, timeout)
        data2, mode2, name2 = _profile_one(args.binary2, timeout)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if fmt == "json":
        import json
        print(json.dumps({
            "meta": {"tool": "riscv-xray", "version": __version__, "mode": "compare"},
            "binary1": {"name": name1, "mode": mode1, "extensions": {
                k: v for k, v in data1.items() if not k.startswith("_")
            }, "total": data1["_total"]},
            "binary2": {"name": name2, "mode": mode2, "extensions": {
                k: v for k, v in data2.items() if not k.startswith("_")
            }, "total": data2["_total"]},
        }, indent=2))
        return

    SIGNIFICANT = 5.0   # percentage point delta worth highlighting
    BAR = 10            # bar width per binary

    def bar(pct, width=BAR):
        filled = round(width * pct / 100)
        filled = max(0, min(width, filled))
        return "\u2588" * filled + "\u2591" * (width - filled)

    def delta_icon(d):
        if d > SIGNIFICANT:  return "[+]"
        if d < -SIGNIFICANT: return "[-]"
        return "   "

    width = 66
    sep = "-" * width

    lines = [
        sep,
        f"  riscv-xray v{__version__}  Compare Report",
        sep,
        f"  {'':6}  {'':12}  {name1[:10]:<12}  {name2[:10]:<12}  Delta",
        f"  {'':6}  {'':12}  ({mode1}){'':8}  ({mode2}){'':8}",
        "  " + "-" * (width - 2),
    ]

    for ext_name in EXTENSION_ORDER:
        if ext_name == "_total":
            continue
        p1 = data1.get(ext_name, {}).get("percentage", 0.0)
        p2 = data2.get(ext_name, {}).get("percentage", 0.0)
        delta = p2 - p1
        icon = delta_icon(delta)
        sign = f"{delta:+.1f}"

        from .extensions import EXTENSIONS
        short = EXTENSIONS.get(ext_name, {}).get("name", ext_name)

        lines.append(
            f"  {ext_name:<6}  {short[:12]:<12}  "
            f"{bar(p1)} {p1:>5.1f}%  "
            f"{bar(p2)} {p2:>5.1f}%  "
            f"{sign}% {icon}"
        )

    t1, t2 = data1["_total"], data2["_total"]
    lines += [
        "",
        f"  Total instructions:  {name1[:10]}: {t1:>6,}   {name2[:10]}: {t2:>6,}",
        "",
    ]

    # Significant changes summary
    changes = []
    for ext_name in EXTENSION_ORDER:
        if ext_name in ("_total", "Base"):
            continue
        p1 = data1.get(ext_name, {}).get("percentage", 0.0)
        p2 = data2.get(ext_name, {}).get("percentage", 0.0)
        delta = p2 - p1
        if abs(delta) >= SIGNIFICANT:
            direction = "increased" if delta > 0 else "decreased"
            changes.append(f"  {ext_name} {direction} by {abs(delta):.1f}pp "
                           f"({p1:.1f}% -> {p2:.1f}%)")

    if changes:
        lines.append("  Significant changes (>= 5pp):")
        lines += changes
    else:
        lines.append("  No significant extension changes between binaries.")

    lines += ["", sep]
    print("\n".join(lines))


def cmd_check(args):
    """Verify all dependencies are installed."""
    print("  riscv-xray dependency check\n")

    # Check QEMU
    qemu = shutil.which("qemu-riscv64")
    if qemu:
        import subprocess
        try:
            r = subprocess.run(["qemu-riscv64", "--version"],
                               capture_output=True, text=True, timeout=5)
            version = r.stdout.strip().split("\n")[0]
            print(f"  [+] QEMU:                     {version}")
        except Exception:
            print(f"  [+] QEMU:                     found at {qemu}")
    else:
        print("  [-] QEMU:                     NOT FOUND")
        print("       Install: sudo apt install qemu-user")

    # Check plugin
    plugin_paths = [
        Path(__file__).parent.parent / "plugin" / "xray_plugin.so",
        Path("plugin/xray_plugin.so"),
    ]
    plugin_found = any(p.exists() for p in plugin_paths)
    if plugin_found:
        found_path = next(p for p in plugin_paths if p.exists())
        print(f"  [+] xray_plugin.so:           found at {found_path}")
    else:
        print("  [-] xray_plugin.so:           NOT BUILT")
        print("       Build:   make plugin")

    # Check riscv-application-profiler
    if profiler.check_available():
        print("  [+] riscv-application-profiler: installed")
    else:
        print("  [~] riscv-application-profiler: NOT INSTALLED (optional)")
        print("       Install: pip install riscv-application-profiler")

    print()


def main():
    parser = argparse.ArgumentParser(
        prog="riscv-xray",
        description="Developer-friendly RISC-V extension profiler",
    )
    parser.add_argument("--version", action="version",
                        version=f"riscv-xray v{__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # profile command
    profile_parser = subparsers.add_parser("profile",
                                            help="Profile a RISC-V binary")
    profile_parser.add_argument("binary", help="Path to RISC-V binary")
    profile_parser.add_argument("--args", default="",
                                 help='Arguments to pass to binary (quoted string)')
    profile_parser.add_argument("--output", choices=["text", "html", "json"],
                                 default="text", help="Output format")
    profile_parser.add_argument("--timeout", type=int, default=60,
                                 help="QEMU timeout in seconds (default: 60)")
    profile_parser.add_argument("--verbose", action="store_true",
                                 help="Print raw mnemonic counts")

    # compare command
    compare_parser = subparsers.add_parser("compare",
                                            help="Compare two RISC-V binaries")
    compare_parser.add_argument("binary1", help="First binary (baseline)")
    compare_parser.add_argument("binary2", help="Second binary (comparison)")
    compare_parser.add_argument("--output", choices=["text", "json"],
                                 default="text", help="Output format")
    compare_parser.add_argument("--timeout", type=int, default=60,
                                 help="QEMU timeout per binary (default: 60)")

    # check command
    subparsers.add_parser("check", help="Verify dependencies")

    args = parser.parse_args()

    if args.command == "profile":
        cmd_profile(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "check":
        cmd_check(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
