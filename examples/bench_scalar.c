#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define N 4096

void vec_scale(float *restrict out, const float *restrict in, float s, int n) {
    for (int i = 0; i < n; i++) out[i] = in[i] * s;
}

void vec_add(float *restrict out, const float *restrict a, const float *restrict b, int n) {
    for (int i = 0; i < n; i++) out[i] = a[i] + b[i];
}

void vec_fma(float *restrict out, const float *restrict a, const float *restrict b, const float *restrict c, int n) {
    for (int i = 0; i < n; i++) out[i] = a[i] * b[i] + c[i];
}

void matmul64(float *restrict C, const float *restrict A, const float *restrict B) {
    int n = 64;
    for (int i = 0; i < n; i++)
        for (int k = 0; k < n; k++) {
            float aik = A[i*n+k];
            for (int j = 0; j < n; j++)
                C[i*n+j] += aik * B[k*n+j];
        }
}

void threshold(unsigned char *restrict out, const unsigned char *restrict in, unsigned char t, int n) {
    for (int i = 0; i < n; i++) out[i] = in[i] > t ? 255 : 0;
}

int main() {
    float *a   = calloc(N, sizeof(float));
    float *b   = calloc(N, sizeof(float));
    float *c   = calloc(N, sizeof(float));
    float *out = calloc(N, sizeof(float));
    float *M1  = calloc(64*64, sizeof(float));
    float *M2  = calloc(64*64, sizeof(float));
    float *M3  = calloc(64*64, sizeof(float));
    unsigned char *img_in  = calloc(N, 1);
    unsigned char *img_out = calloc(N, 1);

    for (int i = 0; i < N; i++) {
        a[i] = (float)i * 0.001f;
        b[i] = (float)(N-i) * 0.001f;
        c[i] = (float)i;
        img_in[i] = (unsigned char)(i % 256);
    }
    for (int i = 0; i < 64*64; i++) {
        M1[i] = (float)(i % 100) * 0.01f;
        M2[i] = (float)((i*7) % 100) * 0.01f;
    }

    vec_scale(out, a, 2.5f, N);
    vec_add(out, out, b, N);
    vec_fma(out, a, b, c, N);
    matmul64(M3, M1, M2);
    threshold(img_out, img_in, 128, N);

    printf("scale=%.4f add=%.4f fma=%.4f matmul=%.4f thresh=%d\n",
           out[0], out[1], out[2], M3[0], img_out[200]);

    free(a); free(b); free(c); free(out);
    free(M1); free(M2); free(M3);
    free(img_in); free(img_out);
    return 0;
}