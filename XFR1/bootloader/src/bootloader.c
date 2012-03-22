/*************************************************************************
XFR1: 指から文字がどんどん出てくる
bootloader
**************************************************************************
Pin Assignment

PB0: -
PB1: -
PB2: -
PB3: ISP MOSI
PB4: ISP MISO
PB5: ISP SCK
PB6: XTAL1
PB7: XTAL2

PC0: -
PC1: -
PC2: -
PC3: -
PC4: -
PC5: -
PC6: #RESET
PC7: -

PD0: -
PD1: -
PD2: -
PD3: -
PD4: -
PD5: RX signal input
PD6: TX (LED anode)
PD7: RX Vcc output

**************************************************************************
Fuse
efuse

default(0xff)
it read as 0x07 … well, upper 5 bits are undefined, so it can be a mistake in datasheet.
hfuse

BOOTSZ1=0
BOOTSZ0=0 -> 2048 word boot loader
BOOTRST:=0 start at boot loader
default(0xd9) -> 0xd8
lfuse

CKDIV8:=1 disable CKDIV8
CKSEL3:=1
CKSEL2:=1
CKSEL1:=0
CKSEL0:=0
SUT1:=0
SUT0:=0
(6MHz low power osc, fast start-up for ceramic)
default(0x62) -> 0xcc
**************************************************************************/
#include <util/delay.h>
#include <avr/io.h>
#include <avr/wdt.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/boot.h>
#include <avr/pgmspace.h>
#include "common/base_protocol.h"

#define ROM_USER_LAST 0x37ff
#define PAGE_BYTES_N 7 // 128B


/***************************************************************************
 HW wrapper
***************************************************************************/
void init(){
    wdt_disable();
    
    // shutdown most peripherals
    /*
    PRR=
        _BV(PRTWI)|_BV(PRSPI)|_BV(PRUSART0)|_BV(PRADC)|
        _BV(PRTIM2)|_BV(PRTIM1);
        */
    
    // output:{RXVcc,LED} input:others
    DDRD=_BV(7)|_BV(6);
    
    // Timer 0: Mode 7 (Fast PWM)
    TCCR0A=_BV(WGM01)|_BV(WGM00); // OC0A
    TCCR0B=_BV(WGM02)|_BV(CS00); // no scaling (6MHz)
    OCR0A=78; // 6MHz/(1+OCR0A)/2=38kHz
    
//    sei();
}

void tx_set(uint8_t v){
    if(v)
        TCCR0A|=_BV(COM0A0);
    else{
        TCCR0A&=~_BV(COM0A0);
        PORTD&=~0x40;
    }
}

void rx_enable(uint8_t v){
    if(v)
        PORTD|=_BV(7);
    else
        PORTD&=~_BV(7);
}

uint8_t rx_check(){
    return !(PIND&0x20);
}


/***************************************************************************
 body
***************************************************************************/

void do_power(){
    // run ADC to get voltage ratio
    PRR&=~_BV(PRADC);
    ADMUX=_BV(REFS0)|0xe; // V=Vbg/Vcc
    ADCSRA=_BV(ADEN)|_BV(ADSC)|0x7; // 16MHz/128=125kHz
    
    // wait until conversion ends
    while(ADCSRA&_BV(ADSC));
    uint8_t val=ADC;
    
    // shutdown ADC
    PRR|=_BV(PRADC);
    
    // send result
    send_byte(val);
}


void session(uint8_t *buffer){
    while(!rx_check());
    int16_t c=recv_byte(10);
    
    // read page buffer
    if(c==0){
        c=recv_byte(10);
        if(c<0) return;
        if(c>=(1<<PAGE_BYTES_N)) return; // out of range
        _delay_ms(10);
        send_byte(buffer[c]);
        
        return;
    }
    
    // write page buffer
    if(c==1){
        uint8_t addr;
        c=recv_byte(10);
        if(c<0) return;
        if(c>=(1<<PAGE_BYTES_N)) return; // out of range
        addr=c;
        
        c=recv_byte(10);
        if(c<0) return;
        buffer[addr]=c;
                
        _delay_ms(10);
        send_byte(c);
        
        return;
    }
    
    // status
    if(c==2){
        _delay_ms(10);
        do_power();
        return;
    }
    
    // hash
    if(c==3){
        _delay_ms(10);
        send_byte(xorshift_hash(1<<PAGE_BYTES_N,buffer));
        return;
    }
    
    // fill buffer from ROM
    if(c==4){
        uint16_t addr;
        c=recv_byte(10);
        if(c<0) return;
        addr=c<<8;
        c=recv_byte(10);
        if(c<0) return;
        addr|=c;
        
        // read byte-by-byte
        addr&=~((1<<PAGE_BYTES_N)-1); // align to page
        for(int i=0;i<(1<<PAGE_BYTES_N);i++)
            buffer[i]=pgm_read_byte(addr+i);
        
        _delay_ms(10);
        send_byte(1<<PAGE_BYTES_N);
    }
    
    // write buffer to ROM
    if(c==5){
        uint16_t addr;
        c=recv_byte(10);
        if(c<0) return;
        addr=c<<8;
        c=recv_byte(10);
        if(c<0) return;
        addr|=c;
        if(addr>=0x7000) return; // out of range
        
        addr&=~((1<<PAGE_BYTES_N)-1); // align to page
        for(int i=0;i<(1<<PAGE_BYTES_N);i+=2){
            uint16_t v=buffer[i]|(buffer[i+1]<<8);
            boot_page_fill(addr+i,v);
        }
        
        boot_page_erase_safe(addr);
        boot_page_write_safe(addr);
        
        send_byte(1<<PAGE_BYTES_N);
    }
}


int main(){
    init();
    rx_enable(1);
    _delay_ms(5);
    
    void (*userland)()=0;
    
    if(rx_check()){
        _delay_ms(200); // protect
        uint8_t page_buffer[1<<PAGE_BYTES_N];
        while(1)
            session(page_buffer);
    }
    else{
        _delay_ms(200); // protect
        while(1)
            userland();
    }
}

