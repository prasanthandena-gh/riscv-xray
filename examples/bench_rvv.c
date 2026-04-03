#include <stdio.h>
#include <stdlib.h>
#include <riscv_vector.h>

#define N 4096

/* Scalar version — no RVV */
void vec_fma_scalar(float *out, const float *a,
                    const float *b, const float *c, int n) {
    for (int i = 0; i < n; i++)
        out[i] = a[i] * b[i] + c[i];
}

/* RVV version — explicit vector intrinsics */
void vec_fma_rvv(float *out, const float *a,
                 const float *b, const float *c, int n) {
    for (int i = 0; i < n; ) {
        size_t vl = __riscv_vsetvl_e32m4(n - i);
        vfloat32m4_t va = __riscv_vle32_v_f32m4(a + i, vl);
        vfloat32m4_t vb = __riscv_vle32_v_f32m4(b + i, vl);
        vfloat32m4_t vc = __riscv_vle32_v_f32m4(c + i, vl);
        vfloat32m4_t vr = __riscv_vfmacc_vv_f32m4(vc, va, vb, vl);
        __riscv_vse32_v_f32m4(out + i, vr, vl);
        i += vl;
    }
}

/* RVV threshold — image processing */
void threshold_rvv(unsigned char *out, const unsigned char *in,
                   unsigned char t, int n) {
    for (int i = 0; i < n; ) {
        size_t vl = __riscv_vsetvl_e8m4(n - i);
        vuint8m4_t v   = __riscv_vle8_v_u8m4(in + i, vl);
        vbool2_t   gt  = __riscv_vmsgtu_vx_u8m4_b2(v, t, vl);
        vuint8m4_t res = __riscv_vmerge_vxm_u8m4(
                             __riscv_vmv_v_x_u8m4(0, vl),
                             255, gt, vl);
        __riscv_vse8_v_u8m4(out + i, res, vl);
        i += vl;
    }
}

/* RVV dot product */
float dot_rvv(const float *a, const float *b, int n) {
    vfloat32m4_t acc = __riscv_vfmv_v_f_f32m4(0.0f,
                           __riscv_vsetvlmax_e32m4());
    for (int i = 0; i < n; ) {
        size_t vl = __riscv_vsetvl_e32m4(n - i);
        vfloat32m4_t va = __riscv_vle32_v_f32m4(a + i, vl);
        vfloat32m4_t vb = __riscv_vle32_v_f32m4(b + i, vl);
        acc = __riscv_vfmacc_vv_f32m4(acc, va, vb, vl);
        i += vl;
    }
    size_t vl = __riscv_vsetvlmax_e32m4();
    vfloat32m1_t s = __riscv_vfredusum_vs_f32m4_f32m1(
                         acc,
                         __riscv_vfmv_v_f_f32m1(0.0f, 1), vl);
    return __riscv_vfmv_f_s_f32m1_f32(s);
}

int main() {
    float *a   = calloc(N, sizeof(float));
    float *b   = calloc(N, sizeof(float));
    float *c   = calloc(N, sizeof(float));
    float *out = calloc(N, sizeof(float));
    unsigned char *img_in  = calloc(N, 1);
    unsigned char *img_out = calloc(N, 1);

    for (int i = 0; i < N; i++) {
        a[i] = (float)i * 0.001f;
        b[i] = (float)(N - i) * 0.001f;
        c[i] = (float)i * 0.1f;
        img_in[i] = (unsigned char)(i % 256);
    }

    vec_fma_rvv(out, a, b, c, N);
    threshold_rvv(img_out, img_in, 128, N);
    float d = dot_rvv(a, b, N);

    printf("fma=%.4f thresh=%d dot=%.4f\n",
           out[0], img_out[200], d);

    free(a); free(b); free(c); free(out);
    free(img_in); free(img_out);
    return 0;
}