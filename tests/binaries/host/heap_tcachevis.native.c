#include <stdio.h>
#include <stdlib.h>

#define SIZE_A 0x20
#define COUNT_A 3
#define SIZE_B 0x40
#define COUNT_B 5
#define SIZE_C 0x80
#define COUNT_C 1

// for export only
const size_t size_a = SIZE_A;
const size_t count_a = COUNT_A;
const size_t size_b = SIZE_B;
const size_t count_b = COUNT_B;
const size_t size_c = SIZE_C;
const size_t count_c = COUNT_C;

void *chunks_a[COUNT_A];
void *chunks_b[COUNT_B];
void *chunks_c[COUNT_C];

void break_here() {}

int main() {
    setbuf(stdout, NULL);

    for (int i = 0; i < COUNT_A; i++)
        chunks_a[i] = malloc(SIZE_A);
    for (int i = 0; i < COUNT_B; i++)
        chunks_b[i] = malloc(SIZE_B);
    for (int i = 0; i < COUNT_C; i++)
        chunks_c[i] = malloc(SIZE_C);

    break_here(); // tcache is empty here

    for (int i = 0; i < COUNT_A; i++)
        free(chunks_a[i]);
    for (int i = 0; i < COUNT_B; i++)
        free(chunks_b[i]);
    for (int i = 0; i < COUNT_C; i++)
        free(chunks_c[i]);

    break_here(); // tcache has COUNT_A/COUNT_B/COUNT_C chunks per bucket here

    return 0;
}
