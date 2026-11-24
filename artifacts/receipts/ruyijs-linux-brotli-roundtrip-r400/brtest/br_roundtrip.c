/* Prove libbrotlidec decodes a real brotli stream it did not produce. */
#include <brotli/decode.h>
#include <stdio.h>
#include <string.h>

/* "hello brotli" compressed at quality 5 window 22, produced by the browser
   side encoder in the pinned build; see the hex in the runner. */
static const unsigned char k_compressed[] = {
#include "payload.inc"
};

int main(void) {
  unsigned char out[4096];
  size_t out_size = sizeof out;
  BrotliDecoderResult rc = BrotliDecoderDecompress(
      sizeof k_compressed, k_compressed, &out_size, out);
  if (rc != BROTLI_DECODER_RESULT_SUCCESS) {
    fprintf(stderr, "decode failed rc=%d\n", (int)rc);
    return 1;
  }
  out[out_size] = 0;
  printf("decoded %zu bytes: %s\n", out_size, (char *)out);
  if (strcmp((char *)out, "hello brotli from an independent encoder") != 0) {
    fprintf(stderr, "payload mismatch\n");
    return 1;
  }
  return 0;
}
