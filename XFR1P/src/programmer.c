/*************************************************************************
XFR1P: 指から文字がどんどん出てくる
optical programmer
**************************************************************************
Pin Assignment: Arduino duemilanove

(PB0) digital 8: RST (2)
(PB1/OC1A) digital 9: TX (3)
(PB2) digital 10: RX (4)

**************************************************************************/
#include <util/delay.h>
#include <avr/io.h>
#include <avr/wdt.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/pgmspace.h>
#include "common/base_protocol.h"

#define BUFFER_LENGTH 128

/***************************************************************************
 HW wrapper
***************************************************************************/
void init(){
    wdt_disable();
    
    // port direction
    DDRB=_BV(0)|_BV(1); // RST+TX as output
    
    // configure IR LED port
    TCCR1A=_BV(WGM11)|_BV(WGM10);
    TCCR1B=_BV(WGM13)|_BV(WGM12)|_BV(CS10);
    OCR1A=210; // 16MHz/(1+OCR1A)/2=38kHz
    
    // serial port
    UBRR0=51; // 19.2kbaud/s
    
    sei();
}

void tx_set(uint8_t v){
    if(v)
        TCCR1A|=_BV(COM1A0);
    else{
        TCCR1A&=~_BV(COM1A0);
        PORTB&=~_BV(1);
    }
}

uint8_t rx_check(){
    return !(PINB&_BV(2));
}


/***************************************************************************
 body
***************************************************************************/


void session(){
/*
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
*/
}

// return: positive: length excluding CR or LF
// return negative: somehow failed
// this will ignore empty string
int getline(int size,char *ptr){
    int n=0;
    while(n<size){
        while(!(UCSR0A&_BV(RXC0)));
        char ch=UDR0;
        
        if(ch=='\r' || ch=='\n'){
            if(n>0) return n;
        }
        else
            ptr[n++]=ch;
    }
    return -1;
}

void puts(char *str){
    while(*str){
        while(!(UCSR0A&_BV(UDRE0)));
        UDR0=*str;
        str++;
    }
}

int main(){
    init();
    
    // activate reset
    PORTB|=_BV(0);
    

    while(1){
        char buffer[BUFFER_LENGTH];
        int size=getline(BUFFER_LENGTH,buffer);
        
        if(size<0){
            // overflow
            puts("overflow\r\n");
        }
        else{
            // run command
            puts("success\r\n");
        }
    }
}

