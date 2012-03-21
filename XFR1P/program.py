#!/bin/env python3
import sys
import serial
import argparse
import time

def enter_debug(ser):
    print('entering debug mode')
    ser.write(bytes('d\r\n','UTF-8'))
    print(ser.readline())

def enter_normal(ser):
    print('entering normal mode')
    ser.write(bytes('n\r\n','UTF-8'))
    print(ser.readline())

def get_power(ser):
    print('checking power')
    print('sending request')
    ser.write(bytes('s02\r\n','UTF-8'))
    print(ser.readline())
    
    print('waiting response')
    ser.write(bytes('r\r\n','UTF-8'))
    r=ser.readline()
    print(r)
    rs=r.decode('ASCII')
    if rs[0]=='-':
        v=int(rs[1:],16)
        print('Vcc=%.1f V'%(1.1/(v/256)))

def read_addr(ser):
    print('reading address 0x0000')
    ser.write(bytes('s00\r\n','UTF-8'))
    print(ser.readline())
    ser.write(bytes('s70\r\n','UTF-8'))
    print(ser.readline())
    ser.write(bytes('s00\r\n','UTF-8'))
    print(ser.readline())
    
    print('waiting response')
    ser.write(bytes('r\r\n','UTF-8'))
    r=ser.readline()
    print(r)
    



def show_usage():
    print('usage: program.py [-P <serial port path>] <command>')



def proc(port_path,fn):
    print('opening')
    ser=serial.Serial(port_path,19200)
    print(ser)

    enter_debug(ser)
    time.sleep(0.5)
    fn(ser)
    time.sleep(0.5)
    enter_normal(ser)

def main():
    ps=argparse.ArgumentParser(description='optical programmer')
    ps.add_argument('-P',dest='port',help='port path')
    ps.add_argument('command',choices=['status','read'])
    args=ps.parse_args()
    
    if args.command=='status':
        proc(args.port,get_power)
    elif args.command=='read':
        proc(args.port,read_addr)


if __name__=='__main__':
    main()


