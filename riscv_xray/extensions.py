# extensions.py - RVA23 Extension Definitions (Phase 2)

EXTENSIONS = {
    # ── Mandatory RVA23 ──────────────────────────────────────────────────────
    "RVV": {
        "name": "Vector",
        "full_name": "RISC-V Vector Extension",
        "prefixes": [
            "vadd", "vsub", "vmul", "vdiv", "vle", "vse",
            "vlse", "vsse", "vluxei", "vsuxei", "vset",
            "vmv", "vw", "vn", "vm", "vs",
            # Float ops — explicit to avoid stealing Zvfhmin/Zvfbfwma mnemonics
            "vfadd", "vfsub", "vfmul", "vfdiv", "vfsqrt",
            "vfmacc", "vfmadd", "vfmsac", "vfmsub",
            "vfnmacc", "vfnmadd", "vfnmsac", "vfnmsub",
            "vfwmacc.", "vfwmsac", "vfwnmacc", "vfwnmsac",
            "vfmin", "vfmax", "vfclass", "vfcvt",
            "vfmv", "vfmerge", "vfsgn",
            "vfredosum", "vfredusum", "vfredmax", "vfredmin",
            "vfslide", "vfncvt.r",
            # Integer ops — explicit to avoid stealing Zvbb mnemonics (vrev8, vrol, vror)
            "vrg", "vred", "vrs",
        ],
        "description": "SIMD vector processing",
        "good_for": "AI workloads, media processing, data analytics",
        "compile_flag": "-march=rv64gcv",
        "rva23_status": "mandatory",
    },
    "Zba": {
        "name": "Address gen",
        "full_name": "Zba Address Generation Bit Manipulation",
        "prefixes": ["sh1add", "sh2add", "sh3add"],
        "description": "Fast address calculation",
        "good_for": "Pointer-heavy code, array indexing",
        "compile_flag": "-march=rv64gc_zba",
        "rva23_status": "mandatory",
    },
    "Zbb": {
        "name": "Bit manip",
        "full_name": "Zbb Base Bit Manipulation",
        "prefixes": [
            "clz", "ctz", "cpop", "andn", "orn", "xnor",
            "min", "max", "sext", "zext", "rol", "ror",
            "rev8", "orc"
        ],
        "description": "Efficient bit operations",
        "good_for": "Compilers, algorithms, networking",
        "compile_flag": "-march=rv64gc_zbb",
        "rva23_status": "mandatory",
    },
    "Zicond": {
        "name": "Conditional ops",
        "full_name": "Zicond Integer Conditional Operations",
        "prefixes": ["czero.eqz", "czero.nez"],
        "description": "Branchless conditional zero operations",
        "good_for": "Replacing branch-heavy patterns, reducing branch mispredictions",
        "compile_flag": "-march=rv64gc_zicond",
        "rva23_status": "mandatory",
    },
    "Zcb": {
        "name": "Compressed ops",
        "full_name": "Zcb Compressed Basic Bit Manipulation",
        "prefixes": [
            "c.lbu", "c.lh", "c.lhu", "c.sb", "c.sh",
            "c.zext.b", "c.zext.h", "c.sext.b", "c.sext.h",
            "c.zext.w", "c.not", "c.mul"
        ],
        "description": "16-bit compressed instruction variants",
        "good_for": "Code size reduction, cache efficiency",
        "compile_flag": "-march=rv64gc_zcb",
        "rva23_status": "mandatory",
    },
    "Zfa": {
        "name": "Float additions",
        "full_name": "Zfa Additional Floating-Point Instructions",
        "prefixes": [
            "fli", "fminm", "fmaxm", "fround", "froundnx",
            "fcvtmod", "fmvh", "fmvp", "fleq", "fltq"
        ],
        "description": "Additional IEEE 754-2019 floating-point operations",
        "good_for": "Float precision, IEEE compliance",
        "compile_flag": "-march=rv64gc_zfa",
        "rva23_status": "mandatory",
    },
    "Zvbb": {
        "name": "Vector bitmanip",
        "full_name": "Zvbb Vector Bit Manipulation",
        "prefixes": ["vbrev8", "vrev8", "vandn", "vrol", "vror"],
        "description": "Vector bit manipulation for crypto data preparation",
        "good_for": "Cryptographic operations, data preprocessing",
        "compile_flag": "-march=rv64gcv_zvbb",
        "rva23_status": "mandatory",
    },
    "Zvkng": {
        "name": "Vector GCM",
        "full_name": "Zvkng Vector GCM/GHASH + AES",
        "prefixes": [
            "vghsh", "vgmul",
            "vaesdf", "vaesef", "vaesem", "vaesdm",
            "vaeskf1", "vaeskf2", "vaesz"
        ],
        "description": "Vector AES and GCM/GHASH acceleration",
        "good_for": "AES encryption, TLS/HTTPS, authenticated encryption",
        "compile_flag": "-march=rv64gcv_zvkng",
        "rva23_status": "mandatory",
    },
    "Zvfhmin": {
        "name": "Vector FP16 cvt",
        "full_name": "Zvfhmin Vector Half-Precision Float Conversion",
        "prefixes": ["vfncvt.f.f.w", "vfwcvt.f.f.v"],
        "description": "Vector FP16/FP32 conversion operations",
        "good_for": "AI/ML inference, memory-bandwidth-limited float workloads",
        "compile_flag": "-march=rv64gcv_zvfhmin",
        "rva23_status": "mandatory",
    },
    "Zicntr": {
        "name": "Counters",
        "full_name": "Zicntr Performance Counters",
        "prefixes": ["rdcycle", "rdtime", "rdinstret"],
        "description": "Hardware performance monitoring",
        "good_for": "Performance measurement, profiling",
        "compile_flag": "-march=rv64gc_zicntr",
        "rva23_status": "mandatory",
    },

    # ── Optional RVA23 ────────────────────────────────────────────────────────
    "Zbc": {
        "name": "Carry-less mul",
        "full_name": "Zbc Carry-less Multiplication",
        "prefixes": ["clmul", "clmulh", "clmulr"],
        "description": "Hardware CRC and polynomial math",
        "good_for": "Checksums, CRCs, cryptographic operations",
        "compile_flag": "-march=rv64gc_zbc",
        "rva23_status": "optional",
    },
    "Zvfh": {
        "name": "Vector FP16",
        "full_name": "Zvfh Vector Half-Precision Floating-Point",
        "prefixes": ["vfadd", "vfsub", "vfmul", "vfmacc"],
        "description": "Full FP16 vector arithmetic",
        "good_for": "AI inference, signal processing",
        "compile_flag": "-march=rv64gcv_zvfh",
        "rva23_status": "optional",
    },
    "Zvfbfmin": {
        "name": "Vector BF16 cvt",
        "full_name": "Zvfbfmin Vector BF16 Conversion",
        "prefixes": ["vfncvtbf16", "vfwcvtbf16"],
        "description": "BF16 (brain float) to FP32 conversion",
        "good_for": "LLM inference, ML training data pipelines",
        "compile_flag": "-march=rv64gcv_zvfbfmin",
        "rva23_status": "optional",
    },
    "Zvfbfwma": {
        "name": "Vector BF16 mac",
        "full_name": "Zvfbfwma Vector BF16 Widening Multiply-Add",
        "prefixes": ["vfwmaccbf16"],
        "description": "Hardware BF16 multiply-accumulate for LLMs",
        "good_for": "Transformer inference, matrix multiplication in LLMs",
        "compile_flag": "-march=rv64gcv_zvfbfwma",
        "rva23_status": "optional",
    },
    "Zvksg": {
        "name": "Vector SM crypto",
        "full_name": "Zvksg Vector SM3/SM4 Crypto",
        "prefixes": ["vsm4k", "vsm4r", "vsm3me", "vsm3c"],
        "description": "Vector SM4 block cipher and SM3 hash (Chinese standards)",
        "good_for": "Chinese cryptographic standards compliance",
        "compile_flag": "-march=rv64gcv_zvksg",
        "rva23_status": "optional",
    },

    # ── Security (optional, expansion) ────────────────────────────────────────
    "Zicfilp": {
        "name": "Forward CFI",
        "full_name": "Zicfilp Landing Pads",
        "prefixes": ["lpad"],
        "description": "Forward-edge control flow integrity via landing pads",
        "good_for": "Security hardening, ROP prevention",
        "compile_flag": "-mbranch-protection=standard",
        "rva23_status": "optional",
        "security_relevant": True,
    },
    "Zicfiss": {
        "name": "Return CFI",
        "full_name": "Zicfiss Shadow Stack",
        "prefixes": ["sspush", "sspopchk", "ssrdp", "ssamoswap"],
        "description": "Return-edge CFI via shadow stack",
        "good_for": "Return-oriented programming prevention",
        "compile_flag": "-mbranch-protection=standard",
        "rva23_status": "optional",
        "security_relevant": True,
    },

    # ── Base (catch-all) ──────────────────────────────────────────────────────
    "Base": {
        "name": "Scalar base",
        "full_name": "RV64I Base Integer",
        "prefixes": [],
        "description": "Standard integer instructions",
        "good_for": "General computation",
        "compile_flag": "-march=rv64gc",
        "rva23_status": "mandatory",
    },
}

# Extension check order — specific before Base
# Mandatory RVA23 first, then optional, then security, then Base
EXTENSION_ORDER = [
    # Mandatory
    "RVV", "Zba", "Zbb", "Zicond", "Zcb", "Zfa",
    "Zvbb", "Zvkng", "Zvfhmin", "Zicntr",
    # Optional
    "Zbc", "Zvfh", "Zvfbfmin", "Zvfbfwma", "Zvksg",
    # Security
    "Zicfilp", "Zicfiss",
    # Catch-all
    "Base",
]

# Thresholds for recommendations
THRESHOLDS = {
    "heavy_use":   50,   # > 50%
    "light_use":   10,   # 10-50%
    "minimal_use":  1,   # 1-10%
    "unused":       0,   # 0%
}

# Full RVA23 mandatory march flag
RVA23_FLAG = (
    "-march=rv64gcv_zba_zbb_zicond_zcb_zfa_zvbb_zvkng_zvfhmin_zicntr"
)

# RVA23+AI march flag
RVA23_AI_FLAG = (
    "-march=rv64gcv_zba_zbb_zicond_zcb_zfa_zvbb_zvkng_zvfhmin_zicntr"
    "_zvfh_zvfbfmin_zvfbfwma"
)
