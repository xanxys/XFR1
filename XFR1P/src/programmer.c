/*************************************************************************
XFR1P: 指から文字がどんどん出てくる
optical programmer
**************************************************************************
Pin Assignment Table:
  (<MCU pin name>) <duemilanove pin> : <XFR1P pin name> (<XFR1P connector pin no.>)

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


void reset_set(uint8_t v){
    if(v)
        PORTB|=_BV(0);
    else
        PORTB&=~_BV(0);
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


char getch(){
    while(!(UCSR0A&_BV(RXC0)));
    return UDR0;
}

void putch(char ch){
    while(!(UCSR0A&_BV(UDRE0)));
    UDR0=ch;
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
        char ch=getch();
        
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

void putline(char *str){
    puts(str);
    puts("\r\n");
}

// retval: 0xff: fail
uint8_t parse_nibble(char ch){
    if('0'<=ch && ch<='9')
        return ch-'0';
    if('a'<=ch && ch<='f')
        return ch-'a'+10;
    if('A'<=ch && ch<='F')
        return ch-'A'+10;
    return 0xff;
}

int send_hex(int size,char *ptr){
    if((size&1)==1){
        putline("#hex wrong format");
        return -1;
    }
    
    if(size>128){ // 0<=payload size<=64
        putline("#too big packet");
        return -2;
    }
    
    send_sym(SYM_START);
    for(int i=0;i<size;i+=2){
        uint8_t tu=parse_nibble(ptr[i+0]);
        if(tu==0xff){
            putline("#wrong hex format");
            return -1;
        }
        
        uint8_t tl=parse_nibble(ptr[i+1]);
        if(tl==0xff){
            putline("#wrong hex format");
            return -1;
        }
        
        send_byte((tu<<4)|tl);
    }
    send_sym(SYM_STOP);
    
    return 0;
}

int main(){
    init();
    
    // enter recv-exec-send loop
    while(1){
        char buffer[BUFFER_LENGTH];
        int size=getline(BUFFER_LENGTH,buffer);
        
        if(size<0){
            // overflow
            putline("#command too long");
        }
        else{
            // run command
            // response
            // "#" prefix -> human readable
            // "!" prefix -> failure (machine readable)
            // "-" prefix -> success (machine readable)
            
            if(buffer[0]=='v'){ // show version
                putline("#version(epoch) " TIMESTAMP);
                putline("-" TIMESTAMP);
            }
            else if(buffer[0]=='d'){ // enter debug mode
                tx_set(1);
                reset_set(1);
                _delay_ms(100);
                reset_set(0);
                _delay_ms(100);
                tx_set(0);
                putline("-");
            }
            else if(buffer[0]=='n'){ // enter normal mode
                tx_set(0);
                reset_set(1);
                _delay_ms(100);
                reset_set(0);
                _delay_ms(100);
                putline("-");
            }
            else if(buffer[0]=='s'){ // send packet
                if(send_hex(size-1,&buffer[1])==0)
                    putline("-");
                else
                    putline("!");
            }
            else if(buffer[0]=='r'){ // receive packet
                putline("-");
            }
            else{
                putline("#unknown command");
            }
        }
    }
}

