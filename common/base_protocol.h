/* base protocol for firmware rewriting. blocking implementation.
half-duplex 500bps packet based
*/
#pragma once
#include <stdint.h>

#define SYM_START 3 // 11
#define SYM_D0 1 // 01
#define SYM_D1 2 // 10
#define SYM_STOP 0 // 00

// depends on
// F_CPU
void tx_set(uint8_t v);
uint8_t rx_check();

// expose
uint8_t xorshift_hash(uint8_t sz,uint8_t *ptr);

void send_sym(uint8_t sym);
void send_byte(uint8_t v);
void send_data(uint16_t size,uint8_t *ptr);

int16_t recv_packet(uint8_t sz,uint8_t *ptr);

