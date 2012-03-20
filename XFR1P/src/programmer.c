/*************************************************************************
XFR1P: 指から文字がどんどん出てくる
optical programmer
**************************************************************************
Pin Assignment: Arduino duemilanove
**************************************************************************/
#include <util/delay.h>
#include <avr/io.h>
#include <avr/wdt.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/pgmspace.h>
#include "common/base_protocol.h"

/***************************************************************************
 HW wrapper
***************************************************************************/
void init(){
    wdt_disable();
    
    // shutdown most peripherals
    PRR=
        _BV(PRTWI)|_BV(PRSPI)|_BV(PRUSART0)|_BV(PRADC)|
        _BV(PRTIM2)|_BV(PRTIM1);
    
    // output:{RXVcc,LED} input:others
    DDRD=_BV(7)|_BV(6);
    
    // Timer 0: Mode 7 (Fast PWM)
    TCCR0A=_BV(WGM01)|_BV(WGM00); // OC0A
    TCCR0B=_BV(WGM02)|_BV(CS00); // no scaling (6MHz)
    OCR0A=78; // 6MHz/(1+OCR0A)/2=38kHz
    
    sei();
}

void tx_set(uint8_t v){
    if(v)
        TCCR0A|=_BV(COM0A0);
    else{
        TCCR0A&=~_BV(COM0A0);
        PORTD&=~0x40;
    }
}

uint8_t rx_check(){
    return !(PIND&0x20);
}


/***************************************************************************
 body
***************************************************************************/


void session(){
    uint8_t p_buffer[255];
    uint16_t p_size=recv_packet(255,p_buffer);
    
    // read
    if(p_buffer[0]==0 && p_size==4){
        uint16_t addr=(p_buffer[1]<<8)|p_buffer[2];
        uint8_t size=p_buffer[3];
        
        // check error
        if(size>64) return;
        
        do_read(addr,size);
        return;
    }
    
    // write
    if(p_buffer[0]==1 && p_size>=7){
        uint16_t addr0=(p_buffer[1]<<8)|p_buffer[2];
        uint8_t size=p_buffer[3];
        
        uint8_t *data=&p_buffer[4];
        uint16_t addr1=(p_buffer[4+size]<<8)|p_buffer[4+size+1];
        uint8_t hash=p_buffer[4+size+2];
        
        // check error
        if(size>64) return;
        if(addr0!=addr1) return;
        if(xorshift_hash(size,data)!=hash) return;
        
        // do_write(addr0,size,data);
        return;
    }
    
    // power
    if(p_buffer[0]==2 && p_size==1){
        do_power();
        return;
    }
}


int main(){
    while(1){
    }
}

