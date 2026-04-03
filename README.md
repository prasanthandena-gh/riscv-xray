# riscv-xray

[![CI](https://github.com/prasanthandena-gh/riscv-xray/actions/workflows/ci.yml/badge.svg)](https://github.com/prasanthandena-gh/riscv-xray/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/riscv-xray)](https://pypi.org/project/riscv-xray/)

**RISC-V extension profiler for developers targeting RVA23.**

See exactly which RVA23 extensions your binary uses, find missed vectorization, check CFI security posture, and validate compliance in CI — all from one tool.

```
$ riscv-xray lint ./my-service --profile rva23

  FAIL  2/10 mandatory extensions active (20%)
  Missing:  Zicond, Zcb, Zfa, Zvbb, Zvkng, Zvfhmin, Zicntr, Zicfiss
  Fix: -march=rv64gcv_zba_zbb_zicond_zcb_zfa_zvbb_zvkng_zvfhmin_zicntr
```

---

## Three modes — choose what you have

| Mode | Requires | Best for |
|------|----------|----------|
| **Static** (objdump) | `binutils-riscv64-linux-gnu` | CI compliance checks, any machine |
| **QEMU** | QEMU 8.0+ with plugin | Dev without hardware |
| **Hardware** (perf) | RISC-V board + Linux perf | Accurate runtime profiling |

---

## Quick Start

### Static analysis — works on any machine, no hardware needed

```bash
pip install riscv-xray
sudo apt install binutils-riscv64-linux-gnu   # provides riscv64 objdump

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
riscv-xray profile ./my-binary --output json          # machine-readable output
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

### RVA23 compliance gap (`--profile rva23`)

```
----------------------------------------------------------
  RVA23 Compliance Gap Report
----------------------------------------------------------
  Profile:  RVA23 — 2023 application processor profile

  Mandatory Extension Coverage
  --------------------------------------------------------
  RVV        Vector              52.1%   [+] Active
  Zba        Address gen          7.7%   [+] Active
  Zbb        Bit manip            1.2%   [~] Minimal (<5%)
  Zicond     Conditional ops      0.0%   [-] Missing
  Zvkng      Vector GCM           0.0%   [-] Missing

  Score: 2/10 mandatory extensions active  (20%)

  Missing extensions fix:
    -march=rv64gcv_zba_zbb_zicond_zcb_zfa_zvbb_zvkng_zvfhmin_zicntr
```

### Vector quality (`--vector-quality`)

```
----------------------------------------------------------
  Vector Quality Metrics
----------------------------------------------------------
  Total RVV instructions: 1,482
  Quality score:          62/100

  vsetvli ratio:      18.0%  [!]
    18% of vector instructions are vsetvli — high overhead.
    => Use longer loop bodies. Try: -mrvv-max-lmul=dynamic

  Vector mem ratio:   34.0%  [~]
    Workload is memory-bandwidth bound.
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

  To enable CFI:
    Compile with: -mbranch-protection=standard
    Requires:     GCC 14+ or LLVM 18+
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

  Note: Static analysis only — may have false positives.
  Verify with: gcc -fopt-info-vec-missed -O2 -march=rv64gcv
```

---

## Plugin architecture

Add support for vendor or experimental extensions without touching core code.

```python
# riscv_xray/plugins/my_vendor.py
EXTENSION_NAME = "XVendor"
PREFIXES       = ["xv.vadd", "xv.vmul"]
METADATA       = {
    "name":        "Vendor Vector",
    "description": "Vendor-specific vector extension",
    "rva23_status": "vendor",
}

def classify(mnemonic: str) -> bool:
    return any(mnemonic.startswith(p) for p in PREFIXES)

def analyze(mnemonics: list) -> dict:
    return {}
```

```bash
riscv-xray profile ./binary --plugins ./my-plugins/
```

Built-in plugin: **XTheadV** (T-Head C906/C910 vendor vector, pre-RVV).

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

## CI integration

```yaml
# .github/workflows/rva23.yml
- name: Install riscv-xray
  run: |
    sudo apt install binutils-riscv64-linux-gnu
    pip install riscv-xray

- name: RVA23 compliance check
  run: riscv-xray lint ./build/my-service --profile rva23

- name: Automotive CFI check
  run: riscv-xray lint ./build/my-service --profile rva23 --market automotive
```

---

## Built on

- **QEMU** — TCG plugin API for user-mode RISC-V emulation
- **Linux perf** — hardware performance counter sampling
- **RAVE** (arxiv:2409.13639) — demonstrated the QEMU TCG plugin approach for RISC-V profiling

---

## License

MIT
