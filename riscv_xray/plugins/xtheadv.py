"""
xtheadv.py - T-Head vendor vector extension plugin (pre-RVV).

T-Head C906/C910 chips ship a vendor vector extension that predates
the ratified RVV standard. This plugin detects those instructions.
"""

EXTENSION_NAME = "XTheadV"

PREFIXES = ["th.vsetvl", "th.vld", "th.vst", "th.vadd", "th.vmul"]

METADATA = {
    "name": "T-Head Vector",
    "full_name": "T-Head Vendor Vector Extension",
    "description": "T-Head vendor vector extension (pre-RVV, C906/C910 chips)",
    "good_for": "T-Head C906/C910 embedded boards",
    "compile_flag": "-march=rv64gcxtheadvector",
    "rva23_status": "vendor",
    "source": "plugin",
}


def classify(mnemonic: str) -> bool:
    """Return True if mnemonic belongs to this extension."""
    return any(mnemonic.startswith(p) for p in PREFIXES)


def analyze(mnemonics: list) -> dict:
    """Return extension-specific analysis beyond basic counting."""
    count = sum(1 for m in mnemonics if classify(m))
    if count == 0:
        return {}
    return {
        "xtheadv_note": (
            "T-Head vendor vector instructions detected. "
            "These are not RVV-compatible. "
            "Consider migrating to standard RVV for RVA23 compliance."
        )
    }
