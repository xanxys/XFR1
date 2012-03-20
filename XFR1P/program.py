#!/bin/env python3
import sys
import serial

def enter_debug(ser):
    print('entering debug mode')
    ser.write(bytes('d\r\n','UTF-8'))
    print(ser.readline())

def enter_normal(ser):
    print('entering normal mode')
    ser.write(bytes('n\r\n','UTF-8'))
    print(ser.readline())

if len(sys.argv)<=1:
    print('usage: program.py <serial port path>')
else:
    print('opening')
    ser=serial.Serial(sys.argv[1],19200)
    print(ser)

    enter_debug(ser)
    enter_normal(ser)
