"""parser.py - Parse raw QEMU/plugin output into structured mnemonic lists."""


def parse_xray_output(raw_output: str) -> list:
    """
    Parse raw output containing XRAY_INSN: lines.

    Returns a list of mnemonic strings.
    """
    mnemonics = []
    for line in raw_output.splitlines():
        line = line.strip()
        if line.startswith("XRAY_INSN:"):
            mnemonic = line[len("XRAY_INSN:"):]
            if mnemonic:
                mnemonics.append(mnemonic)
        elif line == "XRAY_DONE":
            break
    return mnemonics


def parse_log_file(path: str) -> list:
    """Read a log file and extract mnemonics."""
    try:
        with open(path, "r") as f:
            return parse_xray_output(f.read())
    except FileNotFoundError:
        raise FileNotFoundError(f"Log file not found: {path}")
