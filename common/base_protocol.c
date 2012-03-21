#include "base_protocol.h"
#include <util/delay.h>


uint8_t xorshift_hash(uint8_t sz,uint8_t *ptr){
    uint8_t h=0;
    for(uint8_t i=0;i<sz;i++)
        h=((h<<1)|(h>>7))^ptr[i];
    return h;
}


void send_byte(uint8_t v){
    // START
    tx_set(1);
    _delay_ms(1);
    
    // data
    for(uint8_t i=0;i<8;i++,v<<=1){
        tx_set(v&0x80);
        _delay_ms(1);
    }
    
    // STOP
    tx_set(0);
    _delay_ms(1);
}

int16_t recv_byte(uint8_t timeout){
    // START
    uint8_t sync=0;
    for(uint8_t t=0;t<timeout;t++){
        for(uint8_t i=0;i<10;i++){
            if(rx_check()){
                _delay_ms(0.5);
                sync=1;
                break;
            }
            _delay_ms(0.1);
        }
        if(sync) break;
    }
    if(!sync) return -1;
    _delay_ms(1);
    
    // data
    uint8_t v=0;
    for(uint8_t i=0;i<8;i++){
        v<<=1;
        if(rx_check()) v|=1;
        _delay_ms(1.0);
    }
    
    // STOP
    if(rx_check()){
        while(rx_check());
        return -2; // out of sync
    }
    
    return v;
}

