# extensions.py - RVA23 Extension Definitions

EXTENSIONS = {
    "RVV": {
        "name": "Vector",
        "full_name": "RISC-V Vector Extension",
        "prefixes": [
            "vadd", "vsub", "vmul", "vdiv", "vle", "vse",
            "vlse", "vsse", "vluxei", "vsuxei", "vset",
            "vmv", "vf", "vw", "vn", "vm", "vr", "vs"
        ],
        "description": "SIMD vector processing",
        "good_for": "AI workloads, media processing, data analytics",
        "compile_flag": "-march=rv64gcv"
    },
    "Zba": {
        "name": "Address generation",
        "full_name": "Zba Bit Manipulation",
        "prefixes": ["sh1add", "sh2add", "sh3add"],
        "description": "Fast address calculation",
        "good_for": "Pointer-heavy code, array indexing",
        "compile_flag": "-march=rv64gc_zba"
    },
    "Zbb": {
        "name": "Bit manipulation",
        "full_name": "Zbb Base Bit Manipulation",
        "prefixes": [
            "clz", "ctz", "cpop", "andn", "orn", "xnor",
            "min", "max", "sext", "zext", "rol", "ror",
            "rev8", "orc"
        ],
        "description": "Efficient bit operations",
        "good_for": "Compilers, algorithms, networking",
        "compile_flag": "-march=rv64gc_zbb"
    },
    "Zbc": {
        "name": "Carry-less multiply",
        "full_name": "Zbc Carry-less Multiplication",
        "prefixes": ["clmul", "clmulh", "clmulr"],
        "description": "Hardware CRC and polynomial math",
        "good_for": "Checksums, CRCs, cryptographic operations",
        "compile_flag": "-march=rv64gc_zbc"
    },
    "Zbkx": {
        "name": "Crypto crossbar",
        "full_name": "Zbkx Crossbar Permutations",
        "prefixes": ["xperm4", "xperm8"],
        "description": "Hardware encryption acceleration",
        "good_for": "AES, SHA, encryption workloads",
        "compile_flag": "-march=rv64gc_zbkx"
    },
    "Zicntr": {
        "name": "Counters",
        "full_name": "Zicntr Performance Counters",
        "prefixes": ["rdcycle", "rdtime", "rdinstret"],
        "description": "Hardware performance monitoring",
        "good_for": "Performance measurement, profiling",
        "compile_flag": "-march=rv64gc_zicntr"
    },
    "Base": {
        "name": "Scalar base",
        "full_name": "RV64I Base Integer",
        "prefixes": [],  # catches everything else
        "description": "Standard integer instructions",
        "good_for": "General computation",
        "compile_flag": "-march=rv64gc"
    }
}

# Thresholds for recommendations
THRESHOLDS = {
    "heavy_use": 50,      # > 50% = heavy use
    "light_use": 10,      # 10-50% = in use
    "minimal_use": 1,     # 1-10% = light use
    "unused": 0           # 0% = unused
}

# RVA23 recommended compiler flag (full profile)
RVA23_FLAG = "-march=rv64gcv_zba_zbb_zbc_zbkx_zicntr"

# Extension check order (specific before Base)
EXTENSION_ORDER = ["RVV", "Zba", "Zbb", "Zbc", "Zbkx", "Zicntr", "Base"]
