# Getting Started with riscv-xray

riscv-xray tells you which RISC-V extensions your binary actually uses,
how well it targets the RVA23 profile, and what you can improve.

---

## What mode do I need?

riscv-xray has three modes. Pick based on what you have available.

```
Mode 1 — Static (objdump)
  You have:   Any Linux machine + binutils
  You get:    Extension presence, compliance gap, security analysis
  Install:    pip install riscv-xray
              sudo apt install binutils-riscv64-linux-gnu

Mode 2 — QEMU emulation
  You have:   QEMU 8.0+ with plugin support
  You get:    All features, instruction counts from emulated execution
  Install:    pip install riscv-xray && make plugin

Mode 3 — Real hardware (perf)
  You have:   RISC-V board (VisionFive 2, SpacemiT X60, etc.) + Linux perf
  You get:    Accurate runtime samples, hot path analysis
  Install:    pip install riscv-xray  (on the board or your dev machine)
```

Not sure which mode is available?

```bash
riscv-xray check
```

---

## Mode 1 — Static analysis

### Install

```bash
pip install riscv-xray
sudo apt install binutils-riscv64-linux-gnu
```

### What you can do

**CI compliance check** — the primary use case for static mode:

```bash
riscv-xray lint ./my-binary --profile rva23
```

Output on pass:
```
------------------------------------------
  PASS  10/10 mandatory extensions active
------------------------------------------
```

Output on fail:
```
------------------------------------------
  FAIL  3/10 mandatory extensions active (30%)
  Missing:  Zicond, Zcb, Zfa, Zvbb, Zvkng, Zvfhmin, Zicntr

  Fix: -march=rv64gcv_zba_zbb_zicond_zcb_zfa_zvbb_zvkng_zvfhmin_zicntr
------------------------------------------
```

Exit code 0 = PASS, exit code 1 = FAIL. Drop this directly into CI.

**Profile gap report:**

```bash
riscv-xray profile ./my-binary --profile rva23
```

Shows a table of every mandatory extension — active, minimal (<5%), or missing.
Includes a suggested `-march` flag covering what's missing.

**Security / CFI check:**

```bash
riscv-xray profile ./my-binary --security
```

Shows whether `Zicfilp` (landing pads) and `Zicfiss` (shadow stack) are
present, and the impact for automotive (ISO 26262), server, and embedded markets.

**Automotive CI check:**

```bash
riscv-xray lint ./my-binary --profile rva23 --market automotive
# FAIL if CFI is absent — required by ISO 26262 ASIL-D
```

**Runtime detection code:**

```bash
riscv-xray profile ./my-binary --profile rva23 --show-hwprobe
```

Generates copy-pasteable C code using the `riscv_hwprobe` syscall (Linux 6.4+)
so your binary can detect extensions at runtime and take fast paths.

**Missed vectorization (static):**

```bash
riscv-xray profile ./my-binary --check-vectorization
```

Finds functions that have loops and float/memory patterns but zero vector
instructions — candidates for auto-vectorization.
Always verify results with `gcc -fopt-info-vec-missed`.

---

## Mode 3 — Real hardware

This is the most accurate mode. Use it when optimizing for a specific board.

### Step 1: collect profile on your RISC-V board

```bash
# On the board
pip install riscv-xray
riscv-xray record ./my-service
# saves profile.txt
```

Or collect manually:

```bash
perf record -e cycles:u ./my-service
perf annotate --stdio --no-source > profile.txt
```

### Step 2: analyze (anywhere)

Copy `profile.txt` to your dev machine and run:

```bash
riscv-xray profile --from-perf profile.txt
riscv-xray profile --from-perf profile.txt --profile rva23
riscv-xray profile --from-perf profile.txt --vector-quality
riscv-xray profile --from-perf profile.txt --mtune
```

Real hardware profiles show actual runtime sample percentages — not static
instruction counts. A hot loop that runs 10,000 times shows up proportionally.

### Understanding the output

The profile shows which extensions appear in the hot path. A binary may
contain RVV instructions that rarely execute — static mode counts those,
perf mode weights them by actual CPU samples.

---

## Mode 2 — QEMU emulation

### Install

```bash
# Ubuntu 24.04 — QEMU from apt (check if plugin support is included)
sudo apt install qemu-user

# Build the xray QEMU plugin
make plugin

# Install riscv-xray
pip install -e .
```

If `make plugin` fails with "qemu-plugin.h not found", your QEMU package
was not compiled with plugin support. Build QEMU from source:

```bash
# Build QEMU 8.2 with plugin support
sudo apt install ninja-build libglib2.0-dev
wget https://download.qemu.org/qemu-8.2.2.tar.xz
tar xf qemu-8.2.2.tar.xz && cd qemu-8.2.2
./configure --target-list=riscv64-linux-user --enable-plugins
make -j$(nproc)
sudo make install
```

Then rebuild the plugin:
```bash
cd /path/to/riscv-xray
make plugin
```

### Profile a binary

```bash
riscv-xray profile ./my-riscv-binary
riscv-xray profile ./my-riscv-binary --args "--workers 4"
riscv-xray profile ./my-riscv-binary --verbose   # show top 20 mnemonics
```

QEMU mode captures every instruction executed during the run. Loop bodies
are counted each iteration — more accurate than static but slower to collect.

---

## Command reference

### `profile`

```
riscv-xray profile [binary] [options]

Arguments:
  binary                RISC-V ELF binary (omit with --from-perf)

Options:
  --from-perf FILE      Parse perf annotate output instead of running binary
  --args "..."          Arguments to pass to the binary
  --output text|html|json   Output format (default: text)
  --timeout N           Execution timeout in seconds (default: 60)
  --verbose             Show top 20 mnemonics by frequency
  --profile PROFILE     Show RVA profile compliance gap
                        Choices: rva22, rva23, rva23+ai
  --vector-quality      Show vector quality metrics
  --security            Show CFI/security extension analysis
  --mtune               Suggest -mtune target
  --show-hwprobe        Show riscv_hwprobe runtime detection snippets
  --check-vectorization Detect missed auto-vectorization opportunities
  --plugins DIR         Load extra plugins from directory
```

### `lint`

```
riscv-xray lint binary [options]

Arguments:
  binary                RISC-V ELF binary

Options:
  --profile PROFILE     Target profile (default: rva23)
                        Choices: rva22, rva23, rva23+ai
  --threshold N         Min % of mandatory extensions required (default: 100)
  --market MARKET       Apply market CFI requirements
                        Choices: automotive, server, embedded, desktop
  --timeout N           Execution timeout in seconds

Exit codes:
  0   PASS
  1   FAIL
```

### `compare`

```
riscv-xray compare binary1 binary2 [options]

Arguments:
  binary1               Baseline binary
  binary2               Comparison binary

Options:
  --output text|json    Output format (default: text)
  --timeout N           Per-binary timeout
  --function-diff       Show per-function extension diff (requires objdump)
```

### `record`

```
riscv-xray record binary [options]   (RISC-V hardware only)

Arguments:
  binary                Binary to profile

Options:
  --args "..."          Arguments for the binary
  --output FILE         Output file (default: profile.txt)
  --timeout N           perf record timeout in seconds (default: 120)
```

### `check`

```
riscv-xray check

Shows availability of all three modes on the current machine.
```

---

## RVA23 extensions explained

### Why extensions matter

RISC-V hardware ships with different extension sets. Code compiled for
"generic RISC-V" (`rv64gc`) won't use any of the faster instruction sets
even if the hardware supports them. You need to tell the compiler what's
available.

The RVA23 profile defines a guaranteed baseline for application processors:
if a chip claims RVA23 compliance, it must support all mandatory extensions.
Tools targeting RVA23 can use all of them without runtime detection.

### The mandatory set

| Extension | Compile flag | What it accelerates |
|-----------|-------------|----------------------|
| RVV | `-march=..._v` | Any loop over arrays — floating point, integer, memory |
| Zba | `_zba` | Pointer arithmetic, array indexing |
| Zbb | `_zbb` | Population count, leading zeros, byte reversal |
| Zicond | `_zicond` | Branchless conditionals, reduces mispredictions |
| Zcb | `_zcb` | 16-bit compressed instructions, reduces code size |
| Zfa | `_zfa` | IEEE 754-2019 float ops, NaN handling |
| Zvbb | `_zvbb` | Vector bit manipulation for crypto preprocessing |
| Zvkng | `_zvkng` | AES + GCM/GHASH vector acceleration (TLS fast path) |
| Zvfhmin | `_zvfhmin` | FP16↔FP32 conversion (AI inference) |
| Zicntr | `_zicntr` | rdcycle/rdtime performance counters |

To use all of them:

```bash
gcc -march=rv64gcv_zba_zbb_zicond_zcb_zfa_zvbb_zvkng_zvfhmin_zicntr -O2 ...
```

Or use the constant from riscv-xray:

```python
from riscv_xray.extensions import RVA23_FLAG
# RVA23_FLAG = "-march=rv64gcv_zba_zbb_zicond_zcb_zfa_zvbb_zvkng_zvfhmin_zicntr"
```

### AI/ML extensions (`rva23+ai`)

Three additional extensions for inference workloads:

| Extension | What it does |
|-----------|-------------|
| Zvfh | Full FP16 vector arithmetic |
| Zvfbfmin | BF16↔FP32 conversion |
| Zvfbfwma | BF16 widening multiply-accumulate (the key LLM op) |

```bash
riscv-xray lint ./llm-inference --profile rva23+ai
```

### CFI extensions

| Extension | What it does | Compiler flag |
|-----------|-------------|---------------|
| Zicfilp | Landing pads — forward-edge CFI | `-mbranch-protection=standard` |
| Zicfiss | Shadow stack — return-edge CFI | `-mbranch-protection=standard` |

Both require GCC 14+ or LLVM 18+ and are injected automatically by the
compiler — you do not write them manually.

---

## Interpreting results

### Status icons

| Icon | Meaning |
|------|---------|
| `[+]` | Active — extension is in use |
| `[ ]` | In use — lighter usage |
| `[~]` | Minimal — present but < 10% |
| `[-]` | Unused — extension not detected |
| `[!]` | Warning — action recommended |

### Profile gap scores

- **Active**: extension usage >= 5% of instructions
- **Minimal**: present but < 5% — may not be worth targeting
- **Missing**: zero instructions from this extension

Missing does not mean broken. Your binary may not need a given extension.
But if you process arrays (RVV), do crypto (Zvkng), or run ML (Zvfhmin),
absence indicates a missed optimization.

### Vector quality score

The quality score (0–100) combines three signals:

- **vsetvl ratio**: `vsetvli` instructions as % of all RVV. Ideal < 5%.
  High ratio means frequent vector-length resets — short, non-amortized loops.
- **Memory ratio**: vector loads + stores as % of RVV. > 40% is memory-bound.
- **VLEN utilization**: estimated fraction of vector register width used.

Deductions: -20 for vsetvl > 15%, -15 for memory-bound, -5 for low VLEN util.

### mtune confidence levels

| Confidence | Meaning |
|------------|---------|
| HIGH | Strong signal, clear hardware match |
| MEDIUM | Reasonable match, worth trying |
| LOW | Ambiguous mix — generic-ooo is the safe default |

Always benchmark on real hardware before committing to a specific `-mtune`.

---

## Plugin development

Plugins add extension detectors without modifying core riscv-xray code.

### Plugin interface

Create a Python file in `riscv_xray/plugins/` or a custom directory:

```python
# my_extension.py

EXTENSION_NAME = "XMyExt"

PREFIXES = ["xm.vadd", "xm.vmul", "xm.vload"]

METADATA = {
    "name":         "My Extension",
    "full_name":    "My Vendor Extension v1",
    "description":  "Vendor-specific acceleration instructions",
    "good_for":     "My specific use case",
    "compile_flag": "-march=rv64gc_xmyext",
    "rva23_status": "vendor",
}


def classify(mnemonic: str) -> bool:
    """Return True if mnemonic belongs to this extension."""
    return any(mnemonic.startswith(p) for p in PREFIXES)


def analyze(mnemonics: list) -> dict:
    """Return extension-specific analysis. Return {} if none needed."""
    count = sum(1 for m in mnemonics if classify(m))
    if count == 0:
        return {}
    return {"xmyext_note": f"Detected {count} vendor instructions."}
```

### Loading plugins

```bash
# Load from custom directory
riscv-xray profile ./binary --plugins ./my-plugins/

# Built-in plugins load automatically (riscv_xray/plugins/)
```

### Built-in: XTheadV

Detects T-Head vendor vector instructions (pre-RVV, C906/C910 chips):
`th.vsetvl`, `th.vld`, `th.vst`, `th.vadd`, `th.vmul`.

If you're targeting T-Head hardware, use this to detect code that uses
the non-standard vector ISA instead of standard RVV.

---

## Troubleshooting

### "No instructions captured"

- **QEMU mode**: binary may require specific environment variables or
  configuration files at runtime. Use `--args` to pass what it needs.
- **Static mode**: check that `riscv64-linux-gnu-objdump` is in PATH.
  Run `riscv-xray check` to confirm Mode 1 is available.

### "Not a RISC-V binary"

The binary must be a RISC-V 64-bit ELF. Check with:
```bash
file ./my-binary   # should show "ELF 64-bit ... RISC-V"
```

x86 binaries compiled for RISC-V cross-compilation test setups won't work.
You need the RISC-V binary, not the host binary.

### "objdump not found"

```bash
sudo apt install binutils-riscv64-linux-gnu
# provides: riscv64-linux-gnu-objdump
```

### "perf annotate parsing fails"

Make sure you ran:
```bash
perf annotate --stdio --no-source > profile.txt
```

Not just `perf report`. The `--stdio` flag is required.
The `--no-source` flag avoids source code interleaving that breaks parsing.

### QEMU plugin fails to build

Check that your QEMU was compiled with `--enable-plugins`:
```bash
qemu-riscv64 -d help 2>&1 | grep -i plugin
# should show: plugin  ...
```

If not, build QEMU from source (see Mode 2 setup above).

### Static mode shows 0% for everything

Static mode counts instruction presence, not frequency. A binary compiled
without extension flags (`-march=rv64gc` only) will show 0% for RVV even
if the hardware would support it. This is correct — the binary simply
doesn't contain those instructions.

Recompile with the full march flag:
```bash
gcc -march=rv64gcv_zba_zbb_zicond_zcb_zfa_zvbb_zvkng_zvfhmin_zicntr -O2 ...
```

---

## CI integration examples

### Basic RVA23 compliance

```yaml
# .github/workflows/riscv-compliance.yml
name: RISC-V Compliance

on: [push, pull_request]

jobs:
  rva23-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install riscv-xray
        run: |
          sudo apt-get install -y binutils-riscv64-linux-gnu
          pip install riscv-xray

      - name: Download RISC-V binary artifact
        uses: actions/download-artifact@v4
        with:
          name: riscv-binary

      - name: RVA23 compliance check
        run: riscv-xray lint ./my-service --profile rva23

      - name: Automotive CFI check
        run: riscv-xray lint ./my-service --profile rva23 --market automotive
```

### Profile gap as PR comment

```yaml
      - name: Generate profile report
        run: |
          riscv-xray profile ./my-service --profile rva23 --output json \
            > profile.json

      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const profile = require('./profile.json')
            const score = profile.extensions  // use in comment
```

### Threshold-based check (allow partial compliance)

```bash
# Require at least 70% of mandatory extensions active
riscv-xray lint ./my-service --profile rva23 --threshold 70
```

---

## Version history

| Version | What changed |
|---------|-------------|
| 0.3.0 | perf backend (real hardware), objdump backend (static), multi-signal mtune, function-level diff, CFI market checks, plugin architecture |
| 0.2.0 | Profile gap report, lint command, vector quality, hwprobe snippets, security analysis, AI/ML extensions |
| 0.1.0 | Initial release — QEMU plugin, basic extension classification, compare |
