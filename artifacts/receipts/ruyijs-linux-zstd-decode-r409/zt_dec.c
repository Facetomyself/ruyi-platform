#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stddef.h>
#include "zstd.h"

static const unsigned char k_compressed[] = {
#include "zpayload.inc"
};

int main(void) {
  const char *expect = "hello zstd from an independent encoder";
  unsigned long long outsize = ZSTD_getFrameContentSize(k_compressed, sizeof k_compressed);
  if (outsize == ZSTD_CONTENTSIZE_ERROR || outsize == ZSTD_CONTENTSIZE_UNKNOWN) {
    printf("frame size unknown\n"); return 1;
  }
  void *out = malloc((size_t)outsize + 1);
  size_t got = ZSTD_decompress(out, (size_t)outsize, k_compressed, sizeof k_compressed);
  if (ZSTD_isError(got)) { printf("decompress failed: %s\n", ZSTD_getErrorName(got)); return 1; }
  ((char *)out)[got] = 0;
  printf("decoded %zu bytes: %s\n", got, (char *)out);
  if (strcmp((char *)out, expect) != 0) { printf("MISMATCH\n"); return 1; }
  printf("DECODE_OK\n");
  return 0;
}
