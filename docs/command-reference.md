# riscv-xray Command Reference

## profile

Profile a binary or parse a perf file.

```bash
riscv-xray profile <binary>
riscv-xray profile --from-perf <profile.txt>
```

| Flag | Default | Description |
|------|---------|-------------|
| `--from-perf FILE` | — | Parse perf annotate output (real hardware) |
| `--args "..."` | — | Arguments to pass to binary |
| `--output` | text | Output format: `text`, `html`, `json` |
| `--timeout N` | 60 | Execution timeout (seconds) |
| `--verbose` | off | Show top 20 mnemonics |
| `--profile` | — | RVA profile gap: `rva22`, `rva23`, `rva23+ai` |
| `--vector-quality` | off | vsetvl ratio, memory ratio, quality score |
| `--security` | off | CFI extension analysis + market impact |
| `--mtune` | off | -mtune recommendation with confidence |
| `--check-vectorization` | off | Missed vectorization (static analysis) |
| `--show-hwprobe` | off | riscv_hwprobe C snippets for missing extensions |
| `--plugins DIR` | — | Load plugins from extra directory |

## lint

CI pass/fail compliance check. Exits 0 on pass, 1 on fail.

```bash
riscv-xray lint <binary> [--profile rva23] [--threshold 100] [--market automotive]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--profile` | rva23 | Target profile: `rva22`, `rva23`, `rva23+ai` |
| `--threshold N` | 100 | Min % of mandatory extensions required |
| `--market` | — | Market CFI check: `automotive`, `server`, `embedded`, `desktop` |
| `--timeout N` | 60 | Execution timeout |

## compare

Side-by-side extension delta between two binaries.

```bash
riscv-xray compare <binary1> <binary2> [--function-diff]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--output` | text | Output format: `text`, `json` |
| `--timeout N` | 60 | Per-binary timeout |
| `--function-diff` | off | Per-function extension breakdown (needs objdump) |

## record

Collect perf profile on real RISC-V hardware.

```bash
riscv-xray record <binary> [--output profile.txt]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--args "..."` | — | Arguments for the binary |
| `--output FILE` | profile.txt | Output file |
| `--timeout N` | 120 | perf record timeout |

Requires: RISC-V hardware + Linux perf. Prints instructions for next step.

## check

Show which modes are available on the current machine.

```bash
riscv-xray check
```

No flags. Checks objdump (Mode 1), QEMU + plugin (Mode 2), perf + arch (Mode 3).

---

## Profiles

| Name | Mandatory extensions |
|------|---------------------|
| `rva22` | RVV, Zba, Zbb |
| `rva23` | RVV, Zba, Zbb, Zicond, Zcb, Zfa, Zvbb, Zvkng, Zvfhmin, Zicntr |
| `rva23+ai` | rva23 + Zvfh, Zvfbfmin, Zvfbfwma |

## Markets

| Name | CFI requirement |
|------|-----------------|
| `automotive` | Required (ISO 26262 ASIL-D) |
| `server` | Required (production hardening) |
| `embedded` | Optional |
| `desktop` | Optional |

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success / PASS |
| 1 | FAIL (lint) or error |
