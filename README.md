# riscv-xray

[![CI](https://github.com/prasanthandena-gh/riscv-xray/actions/workflows/ci.yml/badge.svg)](https://github.com/prasanthandena-gh/riscv-xray/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/riscv-xray)](https://pypi.org/project/riscv-xray/)

**riscv-xray tells you what your workload actually demands from RISC-V hardware — which extensions it uses, which it misses, and whether the silicon area investment pays off.**

---

## Why riscv-xray

RISC-V's modular ISA means chip architects choose which extensions to include.
Including unnecessary extensions wastes silicon area.
Missing critical ones leaves performance on the table.

But until now there was no easy way to answer:
**"For my workload, which extensions actually matter?"**

riscv-xray answers that question in one command.

```
$ riscv-xray profile ./my-service --profile rva23

  RVA23 Compliance Gap Report
  ----------------------------------------------------------
  RVV        Vector              52.1%   [+] Active
  Zba        Address gen          7.7%   [+] Active
  Zbb        Bit manip            1.2%   [~] Minimal (<5%)
  Zicond     Conditional ops      0.0%   [-] Missing
  Zvkng      Vector GCM           0.0%   [-] Missing
  Zvfhmin    Vector FP16 cvt      0.0%   [-] Missing

  Score: 4/10 mandatory extensions active  (40%)
  Fix: -march=rv64gcv_zba_zbb_zicond_zcb_zfa_zvbb_zvkng_zvfhmin_zicntr
```

---

## Vendor extension support

Chip vendors can add support for their own proprietary extensions without
touching core code. A plugin is a single Python file dropped into a directory.

```python
# my_vendor_ext.py
EXTENSION_NAME = "XMyCore"
PREFIXES       = ["xmc.vadd", "xmc.vmul", "xmc.load"]
METADATA       = {"name": "MyCore Vector", "rva23_status": "vendor", ...}

def classify(mnemonic: str) -> bool:
    return any(mnemonic.startswith(p) for p in PREFIXES)
```

```bash
riscv-xray profile ./binary --plugins ./my-plugins/
```

The **XTheadV** plugin (T-Head C906/C910 pre-RVV vendor vector) ships built-in
as a reference implementation.

---

## Three modes — choose what you have

| Mode | Requires | Best for |
|------|----------|----------|
| **Static** (objdump) | `binutils-riscv64-linux-gnu` | CI compliance checks, any machine |
| **QEMU** | QEMU 8.0+ with plugin | Dev without hardware |
| **Hardware** (perf) | RISC-V board + Linux perf | Accurate runtime profiling |

---

## Quick Start

### Static analysis — works on any machine

```bash
pip install riscv-xray
sudo apt install binutils-riscv64-linux-gnu

riscv-xray lint ./my-riscv-binary --profile rva23
riscv-xray check
```

### Real hardware — on your RISC-V board

```bash
pip install riscv-xray

# Step 1: collect profile on the board
riscv-xray record ./my-service
# saves profile.txt

# Step 2: analyze anywhere
riscv-xray profile --from-perf profile.txt --profile rva23
```

### QEMU emulation

```bash
sudo apt install qemu-user
make plugin
pip install -e .
riscv-xray profile ./my-binary
```

---

## Commands

### `profile` — full extension report

```bash
riscv-xray profile ./my-binary
riscv-xray profile ./my-binary --profile rva23        # RVA23 compliance gap
riscv-xray profile ./my-binary --vector-quality       # vsetvl ratio, quality score
riscv-xray profile ./my-binary --security             # CFI extension analysis
riscv-xray profile ./my-binary --mtune                # -mtune recommendation
riscv-xray profile ./my-binary --check-vectorization  # missed vectorization
riscv-xray profile ./my-binary --show-hwprobe         # runtime detection C code
riscv-xray profile --from-perf profile.txt            # real hardware perf data
riscv-xray profile ./my-binary --output json          # machine-readable
riscv-xray profile ./my-binary --output html > r.html # HTML report
```

### `lint` — CI pass/fail check

```bash
riscv-xray lint ./my-binary --profile rva23
riscv-xray lint ./my-binary --profile rva23 --threshold 80   # require 80%
riscv-xray lint ./my-binary --profile rva23 --market automotive
# exits 0 on PASS, 1 on FAIL
```

### `compare` — diff two binaries

```bash
riscv-xray compare ./v1 ./v2
riscv-xray compare ./v1 ./v2 --function-diff   # per-function breakdown
riscv-xray compare ./v1 ./v2 --output json
```

### `record` — collect perf profile (RISC-V hardware only)

```bash
riscv-xray record ./my-service
riscv-xray record ./my-service --output bench.txt --args "--workers 4"
```

### `check` — environment report

```bash
riscv-xray check
# shows Mode 1/2/3 availability
```

---

## What gets analyzed

### Extensions tracked (RVA23)

| Extension | Status | What it detects |
|-----------|--------|-----------------|
| RVV | mandatory | Vector instructions (`vadd`, `vle`, `vmul`, ...) |
| Zba | mandatory | Address generation (`sh1add`, `sh2add`, `sh3add`) |
| Zbb | mandatory | Bit manipulation (`clz`, `ctz`, `cpop`, `andn`, ...) |
| Zicond | mandatory | Conditional ops (`czero.eqz`, `czero.nez`) |
| Zcb | mandatory | Compressed ops (`c.lbu`, `c.not`, `c.mul`, ...) |
| Zfa | mandatory | Float additions (`fli`, `fminm`, `fmaxm`, ...) |
| Zvbb | mandatory | Vector bit manipulation (`vbrev8`, `vrev8`, `vandn`, ...) |
| Zvkng | mandatory | Vector AES/GCM (`vghsh`, `vaesdf`, `vaeskf1`, ...) |
| Zvfhmin | mandatory | Vector FP16 conversion (`vfncvt.f.f.w`, `vfwcvt.f.f.v`) |
| Zicntr | mandatory | Performance counters (`rdcycle`, `rdtime`) |
| Zbc | optional | Carry-less multiply (`clmul`, `clmulh`) |
| Zvfh | optional | Vector FP16 arithmetic |
| Zvfbfmin | optional | BF16 conversion |
| Zvfbfwma | optional | BF16 multiply-accumulate (LLM ops) |
| Zvksg | optional | SM3/SM4 crypto |
| Zicfilp | security | Forward-edge CFI (landing pads) |
| Zicfiss | security | Return-edge CFI (shadow stack) |

### Profile targets

| Profile | Mandatory extensions |
|---------|----------------------|
| `rva22` | RVV, Zba, Zbb |
| `rva23` | RVV, Zba, Zbb, Zicond, Zcb, Zfa, Zvbb, Zvkng, Zvfhmin, Zicntr |
| `rva23+ai` | rva23 + Zvfh, Zvfbfmin, Zvfbfwma |

### Market compliance (`--market`)

| Market | CFI requirement |
|--------|-----------------|
| `automotive` | Required — ISO 26262 ASIL-D |
| `server` | Required — production hardening |
| `embedded` | Optional |
| `desktop` | Optional |

---

## Output examples
## Real benchmark results

Two versions of the same workload: scalar (compiled with `-march=rv64gc`) 
vs explicit RVV intrinsics (compiled with `-march=rv64gcv`).

### Scalar binary — no vector extensions

\```
$ riscv-xray profile ./bench_scalar --profile rva23

  Binary:   bench_scalar
  Backend:  objdump-static (367 instructions)

  RVV    Vector         ░░░░░░░░░░░░░░░░    0.0%  [-]
  Zbb    Bit manip      ░░░░░░░░░░░░░░░░    0.3%  [-]
  Base   Scalar base                       99.7%

  Score: 0/10 mandatory extensions active (0%)
  Fix: -march=rv64gcv_zba_zbb_zicond_zcb_zfa_zvbb_zvkng_zvfhmin_zicntr
\```

### RVV binary — explicit vector intrinsics

\```
$ riscv-xray profile ./bench_rvv --profile rva23

  Binary:   bench_rvv
  Backend:  objdump-static (327 instructions)

  RVV    Vector         █░░░░░░░░░░░░░░░    7.0%  [+]
  Base   Scalar base                       93.0%

  Score: 1/10 mandatory extensions active (10%)
\```

### Compare — scalar vs RVV

\```
$ riscv-xray compare ./bench_scalar ./bench_rvv

                        bench_scalar   bench_rvv    Delta
  RVV    Vector           0.0%          7.0%        +7.0% [+]
  Base   Scalar base     99.7%         93.0%        -6.7% [-]

  Significant changes: RVV increased by 7.0pp (0.0% -> 7.0%)
\```

riscv-xray correctly identifies that the RVV binary uses vector instructions
the scalar version does not — without running on real hardware.

### Security analysis

\```
$ riscv-xray profile ./bench_rvv --security

  CFI (Control Flow Integrity): [-] Not detected
  [!] Automotive  ISO 26262 ASIL-D — CFI required but absent
  [!] Server      Shadow stack recommended but absent

  Fix: compile with -mbranch-protection=standard (GCC 14+)
\```

### Missed vectorization detection

\```
$ riscv-xray profile ./bench_rvv --check-vectorization

  Analyzed 17 functions (5 candidates)
  [!] main — HIGH: 105 instructions, 25 float/memory ops, 0 vector
\```

See `examples/` for the benchmark source code.

### Vector quality (`--vector-quality`)

```
----------------------------------------------------------
  Vector Quality Metrics
----------------------------------------------------------
  Total RVV instructions: 1,482
  Quality score:          62/100

  vsetvli ratio:      18.0%  [!]
    18% of vector instructions are vsetvli — high overhead.
    Ideal < 5%. Frequent resets indicate short, non-amortized loops.
    => Use longer loop bodies. Try: -mrvv-max-lmul=dynamic

  Vector mem ratio:   34.0%  [~]
    Workload is memory-bandwidth bound.
    => Consider data layout optimization or prefetching.
```

### Security analysis (`--security`)

```
----------------------------------------------------------
  Security Extension Analysis
----------------------------------------------------------
  CFI (Control Flow Integrity): [-] Not detected

  Zicfilp  Forward-edge CFI (landing pads)   [-]
  Zicfiss  Return CFI (shadow stack)          [-]

  Impact by market:
  [!]  Automotive     ISO 26262 ASIL-D — CFI required but absent
  [!]  Server         Production hardening — shadow stack absent
  [ ]  Embedded       CFI optional for this market

  To enable CFI: -mbranch-protection=standard  (GCC 14+ / LLVM 18+)
```

### Missed vectorization (`--check-vectorization`)

```
----------------------------------------------------------
  Missed Vectorization Opportunities  (static analysis)
----------------------------------------------------------
  Analyzed 42 functions  (7 candidates, 3 high/medium shown)

  [!]  json_parse                                    HIGH
       47 instructions, 23 float/memory ops, 0 vector instructions

  [~]  compute_hash                                  MEDIUM
       31 instructions, 9 float/memory ops, 0 vector instructions

  Note: Static analysis only. Verify with: gcc -fopt-info-vec-missed
```

### -mtune recommendation (`--mtune`)

```
----------------------------------------------------------
  Hardware Tune Target
----------------------------------------------------------
  Confidence: [+] MEDIUM

  Recommended: -mtune=sifive-p670
               (SiFive P670, 4-wide OOO, RVA23, 512-bit vector)
  Alternative: -mtune=generic-ooo

  Why:
    - High RVV usage (52.1%) — out-of-order core with wide vector units
    - Zba active — address generation unit is utilized

  Disclaimer:
    Recommendation based on static instruction mix analysis.
    Verify with actual hardware benchmarking before shipping.
```
## Custom instruction hotspot analysis

RISC-V allows you to define your own opcodes. `riscv-xray hotspot` finds
the instruction sequences in your binary that repeat often enough to be
worth fusing into a custom instruction.

### Find candidates

\```
$ riscv-xray hotspot ./bench_hotspot

  Functions analyzed:  13   Total instructions: 381
  Candidates found:    4

  [!]  saxpy    HIGH — RVV FMA kernel, 4x, 62% of function, ~75% reduction
  [!]  daxpy    HIGH — RVV FMA kernel, 4x, 59% of function, ~75% reduction
  [!]  gemv_row HIGH — RVV FMA kernel, 4x, 59% of function, ~75% reduction
\```

### Generate a C stub

\```
$ riscv-xray gen-stub ./bench_hotspot --function saxpy
  Written: ./riscv_custom_xfmak.h

$ cat riscv_custom_xfmak.h
  // __riscv_xfmak(float *out, const float *a, const float *b, size_t n)
  // Fuses: vle32 + vle32 + vfmacc + vse32 into one opcode
  // Saves ~75% of instructions in saxpy
  // Opcode space: custom-0 (0x0B)
\```

The generated `.h` file is a starting point for implementing the instruction
in CodAL, Sail, or a QEMU patch.

---

## CI integration

```yaml
# .github/workflows/riscv-compliance.yml
- name: Install riscv-xray
  run: |
    sudo apt-get install -y binutils-riscv64-linux-gnu
    pip install riscv-xray

- name: RVA23 compliance check
  run: riscv-xray lint ./build/my-service --profile rva23

- name: Automotive CFI check
  run: riscv-xray lint ./build/my-service --profile rva23 --market automotive
```

---

## Architecture

```
riscv_xray/
  backends/
    objdump_backend.py   static disassembly (Mode 1)
    perf_backend.py      perf annotate parser (Mode 3)
    __init__.py          BackendResult + router

  classifier.py          mnemonic → extension mapping
  extensions.py          RVA23 extension definitions + prefixes
  recommender.py         generates actionable recommendations
  report.py              text / HTML / JSON rendering

  profile_checker.py     RVA22/RVA23/RVA23+ai compliance scoring
  vector_quality.py      vsetvl ratio, memory ratio, quality score
  autovec.py             missed vectorization detection
  security.py            CFI analysis, market impact
  hwprobe.py             riscv_hwprobe C snippet generator
  flag_generator.py      multi-signal -mtune recommendation
  accuracy.py            static mode accuracy warnings

  plugin_loader.py       plugin discovery and merging
  plugins/
    xtheadv.py           T-Head vendor vector extension

  runner.py              QEMU execution (Mode 2)
  parser.py              QEMU log parser
  cli.py                 command-line interface
```

---

## Built on

- **QEMU** — TCG plugin API for user-mode RISC-V emulation
- **Linux perf** — hardware performance counter sampling
- **RAVE** (arxiv:2409.13639) — demonstrated the QEMU TCG plugin approach for RISC-V instruction profiling

---

## Contributing

Real-world benchmark analyses are the highest-value contributions.
If you run riscv-xray on a known workload (Embench-IoT, SPEC, LLM inference, networking stack) and get interesting results, open a PR adding it to `examples/`.

---

## License

MIT — see [LICENSE](LICENSE)
