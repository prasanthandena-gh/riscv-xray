/*
 * xray_plugin.c - QEMU TCG plugin for RISC-V instruction tracing
 *
 * Hooks into every instruction QEMU executes and prints the mnemonic
 * to stdout with the prefix XRAY_INSN:<mnemonic>
 *
 * Compatible with QEMU 4.2+ (plugin API v0)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
/* Use bundled header — works with QEMU 4.2+ where system header is absent */
#include "qemu-plugin.h"

QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION;

static int is_hex_char(char c)
{
    return (c >= '0' && c <= '9') ||
           (c >= 'a' && c <= 'f') ||
           (c >= 'A' && c <= 'F');
}

/*
 * Extract the mnemonic from a disassembly string.
 *
 * QEMU 8.x prepends the hex opcode bytes to the disassembly:
 *   "0d07f757  vsetvli a5,a3,e32,m1,ta,ma"
 *   "c29c  sw  a5,0(a3)"
 *
 * Older QEMU returns just the mnemonic + operands:
 *   "vsetvli a5,a3,e32,m1,ta,ma"
 *
 * We detect the hex prefix (exactly 4 or 8 hex chars followed by whitespace)
 * and skip it to reach the actual mnemonic.
 */
static const char *skip_hex_prefix(const char *disas)
{
    size_t hex_len = 0;
    while (is_hex_char(disas[hex_len])) {
        hex_len++;
    }
    /* Opcode dumps are exactly 4 (16-bit) or 8 (32-bit) hex chars */
    if ((hex_len == 4 || hex_len == 8) &&
        (disas[hex_len] == ' ' || disas[hex_len] == '\t')) {
        const char *p = disas + hex_len;
        while (*p == ' ' || *p == '\t') p++;
        /* Only skip if we landed on a real mnemonic (letter) */
        if (*p >= 'a' && *p <= 'z') {
            return p;
        }
    }
    return disas;
}

static void vcpu_insn_exec(unsigned int vcpu_index, void *userdata)
{
    const char *disas = (const char *)userdata;
    if (disas == NULL) {
        return;
    }

    const char *p = skip_hex_prefix(disas);

    /* Extract just the mnemonic (first whitespace-delimited word) */
    char mnemonic[64];
    size_t i = 0;
    while (p[i] && p[i] != ' ' && p[i] != '\t' && i < sizeof(mnemonic) - 1) {
        mnemonic[i] = p[i];
        i++;
    }
    mnemonic[i] = '\0';

    if (i > 0) {
        fprintf(stdout, "XRAY_INSN:%s\n", mnemonic);
        fflush(stdout);
    }
}

static void vcpu_tb_trans(qemu_plugin_id_t id, struct qemu_plugin_tb *tb)
{
    size_t n = qemu_plugin_tb_n_insns(tb);

    for (size_t i = 0; i < n; i++) {
        struct qemu_plugin_insn *insn = qemu_plugin_tb_get_insn(tb, i);

        char *disas = qemu_plugin_insn_disas(insn);
        if (disas == NULL) {
            continue;
        }

        /* Store a copy of the disassembly string as userdata */
        char *disas_copy = strdup(disas);
        g_free(disas);

        if (disas_copy == NULL) {
            continue;
        }

        qemu_plugin_register_vcpu_insn_exec_cb(
            insn, vcpu_insn_exec,
            QEMU_PLUGIN_CB_NO_REGS,
            (void *)disas_copy
        );
    }
}

static void plugin_exit(qemu_plugin_id_t id, void *p)
{
    fprintf(stdout, "XRAY_DONE\n");
    fflush(stdout);
}

QEMU_PLUGIN_EXPORT int qemu_plugin_install(qemu_plugin_id_t id,
                                             const qemu_info_t *info,
                                             int argc, char **argv)
{
    qemu_plugin_register_vcpu_tb_trans_cb(id, vcpu_tb_trans);
    qemu_plugin_register_atexit_cb(id, plugin_exit, NULL);
    return 0;
}
