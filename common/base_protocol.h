/* base protocol for firmware rewriting. blocking implementation.
half-duplex 1000bps UART
*/
#pragma once
#include <stdint.h>

// depends on
// F_CPU
void tx_set(uint8_t v);
uint8_t rx_check();

// expose
uint8_t xorshift_hash(uint8_t sz,uint8_t *ptr);

void send_byte(uint8_t v);
int16_t recv_byte();

