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
    print(ser.readline())

def show_usage():
    print('usage: program.py [-P <serial port path>] <command>')



def proc(port_path):
    print('opening')
    ser=serial.Serial(port_path,19200)
    print(ser)

    enter_debug(ser)
    time.sleep(0.5)
    get_power(ser)
    time.sleep(0.5)
  #  enter_normal(ser)

def main():
    ps=argparse.ArgumentParser(description='optical programmer')
    ps.add_argument('-P',dest='port',help='port path')
    args=ps.parse_args()
    
    proc(args.port)

if __name__=='__main__':
    main()


