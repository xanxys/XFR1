#include "base_protocol.h"
#include <util/delay.h>

void send_sym(uint8_t sym){
    tx_set(sym&2);
    _delay_ms(1);
    tx_set(sym&1);
    _delay_ms(1);
}

void send_byte(uint8_t v){
    for(uint8_t i=0;i<8;i++,v<<=1){
        if(v&0x80)
            send_sym(SYM_D1);
        else
            send_sym(SYM_D0);
    }
}

void send_data(uint16_t size,uint8_t *ptr){
    for(uint16_t i=0;i<size;i++)
        send_byte(ptr[i]);
}

uint8_t xorshift_hash(uint8_t sz,uint8_t *ptr){
    uint8_t h=0;
    for(uint8_t i=0;i<sz;i++)
        h=((h<<1)|(h>>7))^ptr[i];
    return h;
}


int16_t recv_packet(uint8_t sz,uint8_t *ptr){
    uint8_t ok=0;
    for(uint8_t i=0;i<100;i++){
        for(uint8_t j=0;j<10;j++){
            if(rx_check()){
                _delay_ms(0.45);
                break;
            }
            _delay_ms(0.05);
        }
        
        _delay_ms(1.0);
        if(rx_check()){
            ok=1;
            break;
        }
    }
    
    if(!ok) return -1;
    _delay_ms(1);

    uint8_t n=0;
    while(1){
        uint8_t v=0;
        for(uint8_t i=0;i<8;i++){
            v<<=1;
            uint8_t s0=rx_check();
            _delay_ms(1.0);
            uint8_t s1=rx_check();
            _delay_ms(1.0);
            
            if(s0&&s1) return -2; // error
            if(s0) v|=1; // 1
            if(!(s0||s1)) return n; // success
        }
        
        if(n<sz)
            ptr[n]=v;
        n++;
    }
    
}

