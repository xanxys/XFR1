/*************************************************************************
XFR1: 指から文字がどんどん出てくる
application
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

**************************************************************************/
#include <util/delay.h>
#include <avr/io.h>
#include <avr/wdt.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include "common/base_protocol.h"


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

int main(){
    while(1);
}

