/*
 * Minimal qemu-plugin.h for QEMU 4.2+ (plugin API version 0)
 * Bundled for builds where system dev headers are not available.
 * Based on the public QEMU source (GPL-2.0).
 * Source: https://gitlab.com/qemu-project/qemu
 */

#ifndef QEMU_PLUGIN_H
#define QEMU_PLUGIN_H

#include <inttypes.h>
#include <stdbool.h>
#include <stddef.h>

#define QEMU_PLUGIN_VERSION 0

#define QEMU_PLUGIN_EXPORT __attribute__((visibility("default")))

typedef uint64_t qemu_plugin_id_t;

/**
 * qemu_info_t - system information for the plugin
 */
typedef struct {
    /** @target_name: string describing the target architecture */
    const char *target_name;
    /** @version: minimum and current plugin API level */
    struct {
        uint32_t min;
        uint32_t cur;
    } version;
    /** @system_emulation: is this a system emulation? */
    bool system_emulation;
    union {
        /** @smp_vcpus: number of vCPUs (system emulation only) */
        int smp_vcpus;
    };
} qemu_info_t;

/* Opaque types */
struct qemu_plugin_tb;
struct qemu_plugin_insn;

/**
 * enum qemu_plugin_cb_flags - type of callback
 */
typedef enum {
    QEMU_PLUGIN_CB_NO_REGS  = 0,
    QEMU_PLUGIN_CB_R_REGS   = 1,
    QEMU_PLUGIN_CB_RW_REGS  = 2,
} qemu_plugin_cb_flags;

/* Callback typedefs */
typedef void (*qemu_plugin_vcpu_tb_trans_cb_t)(qemu_plugin_id_t id,
                                                struct qemu_plugin_tb *tb);
typedef void (*qemu_plugin_vcpu_udata_cb_t)(unsigned int vcpu_index,
                                             void *userdata);
typedef void (*qemu_plugin_atexit_cb_t)(qemu_plugin_id_t id,
                                         void *userdata);

/* ----- Registration API ----- */

void qemu_plugin_register_vcpu_tb_trans_cb(
    qemu_plugin_id_t id,
    qemu_plugin_vcpu_tb_trans_cb_t cb);

void qemu_plugin_register_vcpu_insn_exec_cb(
    struct qemu_plugin_insn *insn,
    qemu_plugin_vcpu_udata_cb_t cb,
    qemu_plugin_cb_flags flags,
    void *udata);

void qemu_plugin_register_atexit_cb(
    qemu_plugin_id_t id,
    qemu_plugin_atexit_cb_t cb,
    void *userdata);

/* ----- Translation block API ----- */

size_t qemu_plugin_tb_n_insns(const struct qemu_plugin_tb *tb);

struct qemu_plugin_insn *qemu_plugin_tb_get_insn(
    const struct qemu_plugin_tb *tb,
    size_t idx);

/* ----- Instruction API ----- */

/**
 * qemu_plugin_insn_disas() - disassemble instruction
 * Returns a string allocated with g_malloc — caller must g_free it.
 */
char *qemu_plugin_insn_disas(const struct qemu_plugin_insn *insn);

/* g_free from GLib (used to free disas strings) */
extern void g_free(void *mem);

/* ----- Plugin entry point ----- */

/**
 * qemu_plugin_install - plugin entry point (must be exported)
 */
QEMU_PLUGIN_EXPORT int qemu_plugin_install(qemu_plugin_id_t id,
                                             const qemu_info_t *info,
                                             int argc, char **argv);

#endif /* QEMU_PLUGIN_H */
