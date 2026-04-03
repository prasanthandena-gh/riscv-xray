"""cli.py - riscv-xray command-line interface."""

from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path

from . import __version__
from . import runner, profiler, classifier, recommender, report
from . import profile_checker, vector_quality, hwprobe, flag_generator, security
from . import autovec, accuracy
from .plugin_loader import load_plugins
from .backends import objdump_backend, perf_backend


def _run_profile(binary, binary_args=None, timeout=60, plugin_dir=None):
    """
    Run QEMU, classify, return (mnemonics, data, mode, backend, name).
    Loads any plugins and merges them into the classifier.
    """
    if binary_args is None:
        binary_args = []

    name = Path(binary).name

    # Load plugins (built-in + optional extra dir)
    plugins = load_plugins(plugin_dir)
    if plugins:
        from .extensions import EXTENSIONS
        merged = __import__(
            "riscv_xray.plugin_loader", fromlist=["merge_with_core"]
        ).merge_with_core(EXTENSIONS, plugins)
        # Patch classifier temporarily
        import riscv_xray.classifier as cls_mod
        import riscv_xray.extensions as ext_mod
        _orig = ext_mod.EXTENSIONS
        ext_mod.EXTENSIONS = merged
    else:
        _orig = None

    try:
        mnemonics, mode = runner.run(binary, binary_args, timeout=timeout)
    except RuntimeError as e:
        if _orig is not None:
            ext_mod.EXTENSIONS = _orig
        raise

    if _orig is not None:
        ext_mod.EXTENSIONS = _orig

    data = classifier.classify(mnemonics)
    backend = f"{profiler.get_backend()} ({mode})"
    return mnemonics, data, mode, backend, name


def cmd_profile(args):
    """Run extension profiling on a binary."""
    from_perf = getattr(args, "from_perf", None)
    backend_flag = getattr(args, "backend", "auto")
    fmt = args.output
    plugin_dir = getattr(args, "plugins", None)

    # ── perf backend path ──────────────────────────────────────────────────────
    if from_perf:
        print(f"  riscv-xray - parsing perf profile '{Path(from_perf).name}'...",
              file=sys.stderr)
        try:
            from .backends import BackendResult, run_backend
            result = run_backend(from_perf, backend="perf")
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        for w in result.warnings:
            print(f"  {w}", file=sys.stderr)
        mnemonics = result.mnemonics
        mode = "perf-hardware"
        backend_str = f"perf-annotate (real hardware)"
        name = Path(from_perf).stem
        data = classifier.classify(mnemonics)

    # ── QEMU / default path ────────────────────────────────────────────────────
    else:
        binary = args.binary
        binary_args = args.args.split() if args.args else []
        timeout = args.timeout
        print(f"  riscv-xray - profiling '{Path(binary).name}'...", file=sys.stderr)
        try:
            mnemonics, data, mode, backend_str, name = _run_profile(
                binary, binary_args, timeout, plugin_dir
            )
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    if getattr(args, "verbose", False):
        from collections import Counter
        counts = Counter(mnemonics)
        print(f"\n[verbose] Top 20 mnemonics:", file=sys.stderr)
        for mnem, cnt in counts.most_common(20):
            print(f"  {mnem:<20} {cnt:>6}", file=sys.stderr)
        print(file=sys.stderr)

    if not mnemonics:
        print("Warning: no instructions captured.", file=sys.stderr)

    recs = recommender.recommend(data, name)

    # Build output
    output_parts = [report.render(name, data, recs, backend_str, fmt=fmt)]

    # --profile gap report
    profile_name = getattr(args, "profile", None)
    if profile_name and fmt == "text":
        result = profile_checker.check_profile(data, profile_name)
        output_parts.append(profile_checker.format_profile_report(result, data))

    # --vector-quality
    if getattr(args, "vector_quality", False) and fmt == "text":
        vq = vector_quality.analyze_vector_quality(mnemonics)
        section = vector_quality.format_vector_quality_report(vq)
        if section:
            output_parts.append(section)

    # --security
    if getattr(args, "security", False) and fmt == "text":
        sec = security.analyze_security(data)
        output_parts.append(security.format_security_report(sec))

    # --mtune
    if getattr(args, "mtune", False) and fmt == "text":
        suggestion = flag_generator.suggest_mtune(data)
        output_parts.append(flag_generator.format_mtune_section(suggestion))

    # --show-hwprobe
    if getattr(args, "show_hwprobe", False) and fmt == "text" and profile_name:
        result = profile_checker.check_profile(data, profile_name)
        section = hwprobe.format_hwprobe_section(result["missing"])
        if section:
            output_parts.append(section)

    # --check-vectorization
    if getattr(args, "check_vectorization", False) and fmt == "text":
        av = autovec.analyze_autovec(mnemonics)
        section = autovec.format_autovec_report(av)
        if section:
            output_parts.append(section)

    # Accuracy warning — skip for real hardware perf data
    if fmt == "text" and mode != "perf-hardware":
        warn = accuracy.format_accuracy_warning(mode)
        if warn:
            output_parts.append(warn)

    print("\n".join(output_parts))


def _profile_one(binary, timeout=60, plugin_dir=None):
    """Profile a single binary for compare mode."""
    name = Path(binary).name
    print(f"  Profiling '{name}'...", file=sys.stderr)
    mnemonics, data, mode, backend, name = _run_profile(
        binary, [], timeout, plugin_dir
    )
    return data, mode, name


def cmd_compare(args):
    """Compare two binaries side-by-side."""
    from .extensions import EXTENSION_ORDER, EXTENSIONS
    from . import function_diff as fdiff

    timeout = getattr(args, "timeout", 60)
    fmt     = getattr(args, "output", "text")
    plugin_dir = getattr(args, "plugins", None)

    try:
        data1, mode1, name1 = _profile_one(args.binary1, timeout, plugin_dir)
        data2, mode2, name2 = _profile_one(args.binary2, timeout, plugin_dir)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if fmt == "json":
        import json
        print(json.dumps({
            "meta": {"tool": "riscv-xray", "version": __version__, "mode": "compare"},
            "binary1": {"name": name1, "mode": mode1,
                        "extensions": {k: v for k, v in data1.items()
                                       if not k.startswith("_")},
                        "total": data1["_total"]},
            "binary2": {"name": name2, "mode": mode2,
                        "extensions": {k: v for k, v in data2.items()
                                       if not k.startswith("_")},
                        "total": data2["_total"]},
        }, indent=2))
        return

    SIGNIFICANT = 5.0
    BAR = 10

    def bar(pct, width=BAR):
        filled = round(width * pct / 100)
        filled = max(0, min(width, filled))
        return "\u2588" * filled + "\u2591" * (width - filled)

    def delta_icon(d):
        if d > SIGNIFICANT:  return "[+]"
        if d < -SIGNIFICANT: return "[-]"
        return "   "

    width = 70
    sep = "-" * width

    lines = [
        sep,
        f"  riscv-xray v{__version__}  Compare Report",
        sep,
        f"  {'':6}  {'':14}  {name1[:10]:<12}  {name2[:10]:<12}  Delta",
        f"  {'':6}  {'':14}  ({mode1}){'':8}  ({mode2}){'':8}",
        "  " + "-" * (width - 2),
    ]

    for ext_name in EXTENSION_ORDER:
        if ext_name == "_total":
            continue
        p1 = data1.get(ext_name, {}).get("percentage", 0.0)
        p2 = data2.get(ext_name, {}).get("percentage", 0.0)
        delta = p2 - p1
        icon  = delta_icon(delta)
        sign  = f"{delta:+.1f}"
        short = EXTENSIONS.get(ext_name, {}).get("name", ext_name)

        lines.append(
            f"  {ext_name:<8}  {short[:14]:<14}  "
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

    changes = []
    for ext_name in EXTENSION_ORDER:
        if ext_name in ("_total", "Base"):
            continue
        p1 = data1.get(ext_name, {}).get("percentage", 0.0)
        p2 = data2.get(ext_name, {}).get("percentage", 0.0)
        delta = p2 - p1
        if abs(delta) >= SIGNIFICANT:
            direction = "increased" if delta > 0 else "decreased"
            changes.append(
                f"  {ext_name} {direction} by {abs(delta):.1f}pp "
                f"({p1:.1f}% -> {p2:.1f}%)"
            )

    if changes:
        lines.append("  Significant changes (>= 5pp):")
        lines += changes
    else:
        lines.append("  No significant extension changes between binaries.")

    lines += ["", sep]
    print("\n".join(lines))

    # --function-diff
    if getattr(args, "function_diff", False):
        print(f"\n  Analyzing functions in '{name1}'...", file=sys.stderr)
        funcs1 = fdiff.analyze_binary_functions(args.binary1)
        print(f"  Analyzing functions in '{name2}'...", file=sys.stderr)
        funcs2 = fdiff.analyze_binary_functions(args.binary2)
        print(fdiff.diff_functions(funcs1, funcs2, name1, name2))


def cmd_lint(args):
    """Quick pass/fail RVA23 compliance check for CI pipelines."""
    binary      = args.binary
    profile_name = getattr(args, "profile", "rva23")
    threshold   = getattr(args, "threshold", 100)
    market      = getattr(args, "market", None)
    plugin_dir  = getattr(args, "plugins", None)
    timeout     = getattr(args, "timeout", 60)

    print(f"  riscv-xray lint - {Path(binary).name} [{profile_name}]",
          file=sys.stderr)

    try:
        mnemonics, data, mode, backend, name = _run_profile(
            binary, [], timeout, plugin_dir
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    result = profile_checker.check_profile(data, profile_name)
    total  = result["total_mandatory"]
    score  = result["score"]
    pct    = result["percentage"]
    pass_threshold = threshold  # % of mandatory that must be active

    sep = "-" * 46

    # Market-specific check (e.g. automotive requires CFI)
    market_fail = False
    if market:
        sec = security.analyze_security(data)
        mkt = sec["market_impact"].get(market, {})
        if mkt.get("status") == "FAIL":
            market_fail = True

    passed = (pct >= pass_threshold) and not market_fail

    if passed:
        print(f"\n{sep}")
        print(f"  PASS  {score}/{total} mandatory extensions active")
        if market:
            print(f"  Market: {market} — OK")
        print(sep)
        sys.exit(0)
    else:
        print(f"\n{sep}")
        print(f"  FAIL  {score}/{total} mandatory extensions active ({pct:.0f}%)")
        if result["missing"]:
            print(f"  Missing:  {', '.join(result['missing'])}")
        if result["minimal"]:
            print(f"  Minimal:  {', '.join(result['minimal'])} (< 5%)")
        if market_fail:
            print(f"  Market:   {market} — CFI required but absent")
        print(f"\n  Fix: {result['suggested_march']}")
        print(sep)
        sys.exit(1)


def cmd_record(args):
    """Collect a perf profile on real RISC-V hardware."""
    import subprocess, platform

    arch = platform.machine()
    perf_path = shutil.which("perf")

    if not perf_path:
        print("Error: perf not found. Install with: sudo apt install linux-perf",
              file=sys.stderr)
        sys.exit(1)

    if "riscv" not in arch.lower():
        print(
            f"  riscv-xray record requires real RISC-V hardware.\n"
            f"  Your system: {arch}\n"
            f"\n"
            f"  For QEMU profiling:   riscv-xray profile ./binary\n"
            f"  For static analysis:  riscv-xray lint ./binary --profile rva23",
            file=sys.stderr,
        )
        sys.exit(1)

    binary = args.binary
    binary_args = args.args.split() if getattr(args, "args", "") else []
    output_file = getattr(args, "output_file", "profile.txt") or "profile.txt"

    print(f"  Recording: perf record -e cycles:u {binary}", file=sys.stderr)
    r = subprocess.run(
        ["perf", "record", "-e", "cycles:u", binary] + binary_args,
        timeout=getattr(args, "timeout", 120),
    )
    if r.returncode != 0:
        print("Error: perf record failed.", file=sys.stderr)
        sys.exit(1)

    print(f"  Annotating to {output_file}...", file=sys.stderr)
    with open(output_file, "w") as f:
        subprocess.run(
            ["perf", "annotate", "--stdio", "--no-source"],
            stdout=f, stderr=subprocess.DEVNULL,
        )

    print(f"\n  Profile saved to {output_file}")
    print(f"  Now run: riscv-xray profile --from-perf {output_file}")


def cmd_check(args):
    """Verify all dependencies are installed."""
    print(f"  riscv-xray v{__version__} — Environment Check\n")

    import platform, subprocess
    sep = "-" * 58
    available_modes = []

    # ── Mode 1: Static (objdump) ───────────────────────────────────────────────
    print(f"  Mode 1 — Static Analysis (objdump)")
    found, objdump_path = objdump_backend.check_objdump()
    if found:
        print(f"  [+] riscv64-objdump:  found at {objdump_path}")
        print(f"      Supports: lint, profile gap, security analysis")
        available_modes.append("Mode 1 (static)")
    else:
        print(f"  [-] riscv64-objdump:  NOT FOUND")
        print(f"       Install: sudo apt install binutils-riscv64-linux-gnu")
    print()

    # ── Mode 2: QEMU ──────────────────────────────────────────────────────────
    print(f"  Mode 2 — QEMU Emulation")
    qemu = shutil.which("qemu-riscv64")
    if qemu:
        try:
            r = subprocess.run(["qemu-riscv64", "--version"],
                               capture_output=True, text=True, timeout=5)
            version = r.stdout.strip().split("\n")[0]
            print(f"  [+] qemu-riscv64:     {version}")
        except Exception:
            print(f"  [+] qemu-riscv64:     found at {qemu}")
    else:
        print(f"  [-] qemu-riscv64:     NOT FOUND")
        print(f"       Install: sudo apt install qemu-user")

    plugin_paths = [
        Path(__file__).parent.parent / "plugin" / "xray_plugin.so",
        Path("plugin/xray_plugin.so"),
    ]
    plugin_found = any(p.exists() for p in plugin_paths)
    if plugin_found:
        found_path = next(p for p in plugin_paths if p.exists())
        print(f"  [+] xray_plugin.so:   found at {found_path}")
        if qemu:
            available_modes.append("Mode 2 (QEMU)")
    else:
        print(f"  [-] xray_plugin.so:   NOT BUILT")
        print(f"       Build: make plugin")
    print()

    # ── Mode 3: Real hardware (perf) ──────────────────────────────────────────
    print(f"  Mode 3 — Real Hardware (perf annotate)")
    perf = shutil.which("perf")
    arch = platform.machine()
    if perf:
        print(f"  [+] perf:             found")
    else:
        print(f"  [-] perf:             NOT FOUND")
        print(f"       Install: sudo apt install linux-perf")
    if "riscv" in arch.lower():
        print(f"  [+] Architecture:     {arch}  (RISC-V hardware detected)")
        if perf:
            available_modes.append("Mode 3 (real hardware)")
    else:
        print(f"  [~] Architecture:     {arch}  (not RISC-V — Mode 3 requires RISC-V board)")
        print(f"       Use: riscv-xray record on your RISC-V board")
    print()

    # ── Plugins ────────────────────────────────────────────────────────────────
    plugins = load_plugins()
    if plugins:
        print(f"  [+] Plugins:          {', '.join(plugins.keys())}")
    else:
        print(f"  [~] Plugins:          none loaded")
    print()

    # ── Summary ────────────────────────────────────────────────────────────────
    print(sep)
    if available_modes:
        print(f"  Available: {', '.join(available_modes)}")
    else:
        print(f"  No modes available. Install binutils-riscv64-linux-gnu at minimum.")
    print(sep)
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="riscv-xray",
        description="Developer-friendly RISC-V extension profiler",
    )
    parser.add_argument("--version", action="version",
                        version=f"riscv-xray v{__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # ── profile ────────────────────────────────────────────────────────────────
    pp = subparsers.add_parser("profile", help="Profile a RISC-V binary")
    pp.add_argument("binary", nargs="?", default=None,
                    help="RISC-V binary (omit when using --from-perf)")
    pp.add_argument("--from-perf", dest="from_perf", default=None,
                    metavar="FILE",
                    help="Parse perf annotate output file (real hardware)")
    pp.add_argument("--backend", choices=["auto", "qemu", "objdump", "perf"],
                    default="auto", help="Force a specific backend")
    pp.add_argument("--args",    default="",
                    help="Arguments for binary (quoted string)")
    pp.add_argument("--output",  choices=["text", "html", "json"],
                    default="text")
    pp.add_argument("--timeout", type=int, default=60)
    pp.add_argument("--verbose", action="store_true")
    pp.add_argument("--profile", choices=profile_checker.get_profile_names(),
                    help="Show RVA profile compliance gap report")
    pp.add_argument("--vector-quality", dest="vector_quality",
                    action="store_true",
                    help="Show vector quality metrics")
    pp.add_argument("--security", action="store_true",
                    help="Show CFI/security extension analysis")
    pp.add_argument("--mtune",   action="store_true",
                    help="Suggest -mtune target based on instruction mix")
    pp.add_argument("--show-hwprobe", dest="show_hwprobe",
                    action="store_true",
                    help="Show riscv_hwprobe runtime detection snippets")
    pp.add_argument("--check-vectorization", dest="check_vectorization",
                    action="store_true",
                    help="Detect missed auto-vectorization opportunities")
    pp.add_argument("--plugins", default=None,
                    metavar="DIR", help="Extra plugin directory")

    # ── compare ────────────────────────────────────────────────────────────────
    cp = subparsers.add_parser("compare", help="Compare two RISC-V binaries")
    cp.add_argument("binary1", help="Baseline binary")
    cp.add_argument("binary2", help="Comparison binary")
    cp.add_argument("--output", choices=["text", "json"], default="text")
    cp.add_argument("--timeout", type=int, default=60)
    cp.add_argument("--function-diff", dest="function_diff",
                    action="store_true",
                    help="Show per-function extension usage diff")
    cp.add_argument("--plugins", default=None, metavar="DIR")

    # ── lint ───────────────────────────────────────────────────────────────────
    lp = subparsers.add_parser("lint",
                                help="CI pass/fail compliance check")
    lp.add_argument("binary")
    lp.add_argument("--profile", choices=profile_checker.get_profile_names(),
                    default="rva23")
    lp.add_argument("--threshold", type=int, default=100,
                    help="Min %% of mandatory extensions required (default 100)")
    lp.add_argument("--market",
                    choices=list(security.MARKET_CFI_REQUIREMENTS.keys()),
                    help="Apply market-specific checks (e.g. automotive)")
    lp.add_argument("--timeout", type=int, default=60)
    lp.add_argument("--plugins", default=None, metavar="DIR")

    # ── check ──────────────────────────────────────────────────────────────────
    subparsers.add_parser("check", help="Verify dependencies")

    # ── record ─────────────────────────────────────────────────────────────────
    rp = subparsers.add_parser("record",
                                help="Collect perf profile on RISC-V hardware")
    rp.add_argument("binary", help="Binary to profile")
    rp.add_argument("--args", default="", help="Arguments for binary")
    rp.add_argument("--output", dest="output_file", default="profile.txt",
                    help="Output file for perf annotate (default: profile.txt)")
    rp.add_argument("--timeout", type=int, default=120)

    args = parser.parse_args()

    if args.command == "profile":
        if not args.binary and not getattr(args, "from_perf", None):
            pp.error("Provide a binary or --from-perf FILE")
        cmd_profile(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "lint":
        cmd_lint(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "record":
        cmd_record(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
