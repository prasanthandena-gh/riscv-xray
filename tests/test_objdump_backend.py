"""Tests for backends/objdump_backend.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from riscv_xray.backends.objdump_backend import parse_objdump, get_mnemonics

_SAMPLE = """\
my-binary:     file format elf64-littleriscv


Disassembly of section .text:

0000000000012340 <json_parse>:
   12340:	addi	sp,sp,-48
   12344:	sd	ra,40(sp)
   12348:	vadd.vv	v8,v8,v16
   1234c:	vsetvli	t0,a2,e32,m1,tu,mu
   12350:	sd	a0,32(sp)

0000000000013000 <hash_compute>:
   13000:	fadd.s	fa0,fa1,fa2
   13004:	fmul.s	fa1,fa2,fa3
   13008:	add	a0,a1,a2
   1300c:	sd	a0,0(sp)
"""


def test_parse_functions():
    parsed = parse_objdump(_SAMPLE)
    assert "json_parse" in parsed["functions"]
    assert "hash_compute" in parsed["functions"]


def test_parse_mnemonics():
    parsed = parse_objdump(_SAMPLE)
    assert "vadd.vv" in parsed["mnemonics"]
    assert "addi" in parsed["mnemonics"]
    assert "fadd.s" in parsed["mnemonics"]


def test_parse_total_count():
    parsed = parse_objdump(_SAMPLE)
    assert parsed["total_instructions"] == 9


def test_function_instruction_count():
    parsed = parse_objdump(_SAMPLE)
    assert parsed["functions"]["json_parse"]["instruction_count"] == 5
    assert parsed["functions"]["hash_compute"]["instruction_count"] == 4


def test_skip_section_headers():
    parsed = parse_objdump(_SAMPLE)
    # "Disassembly of section .text:" should not appear as a function
    assert "Disassembly of section .text" not in parsed["functions"]


def test_get_mnemonics_flat():
    parsed = parse_objdump(_SAMPLE)
    flat = get_mnemonics(parsed)
    assert isinstance(flat, list)
    assert len(flat) == parsed["total_instructions"]


def test_backend_field():
    parsed = parse_objdump(_SAMPLE)
    assert parsed["backend"] == "objdump-static"
    assert parsed["is_weighted"] is False


def test_empty_input():
    parsed = parse_objdump("")
    assert parsed["total_instructions"] == 0
    assert parsed["mnemonics"] == []
    assert parsed["functions"] == {}
