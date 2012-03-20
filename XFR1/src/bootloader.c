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

uint8_t rx_check(){
    return !(PIND&0x20);
}


/***************************************************************************
 body
***************************************************************************/

void do_read(uint16_t addr,uint8_t size){
    if(addr>ROM_USER_LAST || addr+size>ROM_USER_LAST){
        send_sym(SYM_START);
        send_byte(1); // out of range
        send_sym(SYM_STOP);
    }
    else{
        // read
        uint8_t data[64];
        for(uint8_t i=0;i<size;i++)
            data[i]=pgm_read_byte(addr+size);
        
        uint8_t hash=xorshift_hash(size,data);
        
        // send
        send_sym(SYM_START);
        send_byte(0);
        send_data(size,data);
        send_byte(hash);
        send_sym(SYM_STOP);
    }
}

// See http://www.atmel.com/Images/doc1644.pdf
void do_write(uint16_t addr,uint8_t size,uint8_t *data){
    if(addr>ROM_USER_LAST || addr+size>ROM_USER_LAST){
        send_sym(SYM_START);
        send_byte(1);
        send_sym(SYM_STOP);
    }
    else{
        uint16_t start_addr=addr,end_addr=addr+size; // original address range
        addr=(addr>>PAGE_BYTES_N)<<PAGE_BYTES_N; // page-align address
        
        // page-by-page write
        while(addr<end_addr){
            uint16_t page_addr=addr;
            
            // page load word by word (little endian)
            for(uint8_t i=0;i<(1<<PAGE_BYTES_N);i+=2){
                // decide word to write
                uint8_t lb;
                if(start_addr<=addr && addr<end_addr)
                    lb=data[addr-start_addr];
                else
                    lb=pgm_read_byte(addr);
                addr++;
                
                uint8_t hb;
                if(start_addr<=addr && addr<end_addr)
                    hb=data[addr-start_addr];
                else
                    hb=pgm_read_byte(addr);
                addr++;
                
                // write to temporary page buffer
                __asm__ __volatile__(
                    // set data
                    "mov r0,%0\n"
                    "mov r1,%1\n"
                    // set SPMCSR
                    "ldi %0, 1\n" // here we're resuing %0
                    "out 0x37, %0\n" // SPMCSR
                    "spm"
                    :
                    :"r"(lb), "r"(hb),"z"(page_addr)
                    :"r0","r1"
                    );
            }
            
            // page erase
            SPMCSR=0x03;
            __asm__ __volatile__("spm"::"z"(page_addr));
            
            // page write
            SPMCSR=0x05;
            __asm__ __volatile__("spm"::"z"(page_addr));
        }

        // send
        send_sym(SYM_START);
        send_byte(0);
        send_sym(SYM_STOP);
    }
}

void do_power(){
    // run ADC to get voltage ratio
    uint8_t result=23;
    PRR&=~_BV(PRADC);
    
    PRR|=_BV(PRADC);
    
    // send result
    send_sym(SYM_START);
    send_byte(result);
    send_sym(SYM_STOP);
}


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
    init();
    PORTD|=_BV(6);
//    tx_set(1);
    while(1);
    
    void (*userland)()=0;
    
    if(0){ // PIND&0x20){
        _delay_ms(200); // protect
        while(1)
            userland();
    }
    else{
        _delay_ms(200); // protect
        while(1)
            do_power();
//            session();
    }
}

