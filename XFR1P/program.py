#!/bin/env python3
import sys
import serial
import argparse
import time
import logging

# real low level communication (serial port)

# protocol-level
def enter_debug(ser):
    print('entering debug mode')
    ser.write(bytes('d\r\n','UTF-8'))
    logging.debug(ser.readline())

def enter_normal(ser):
    print('entering normal mode')
    ser.write(bytes('n\r\n','UTF-8'))
    logging.debug(ser.readline())

def get_power(ser):
    print('checking power')
    print('sending request')
    ser.write(bytes('s02\r\n','UTF-8'))
    logging.debug(ser.readline())
    
    print('waiting response')
    ser.write(bytes('r\r\n','UTF-8'))
    r=ser.readline()
    logging.debug(r)
    rs=r.decode('ASCII')
    if rs[0]=='-':
        v=int(rs[1:],16)
        print('Vcc=%.1f V'%(1.1/(v/256)))

def read_buffer(ser,addr):
    addr=int(addr,16)
    
    print('reading buffer offset 0x%02x'%addr)
    ser.write(bytes('s00\r\n','UTF-8'))
    logging.debug(ser.readline())
#    ser.write(bytes('s%02x\r\n'%((addr>>8)&0xff),'UTF-8'))
#    logging.debug(ser.readline())
    ser.write(bytes('s%02x\r\n'%(addr&0xff),'UTF-8'))
    logging.debug(ser.readline())
    
    print('waiting response')
    ser.write(bytes('r\r\n','UTF-8'))
    r=ser.readline()
    logging.debug(r)
    rhex=r.decode('ASCII')[1:3]
    print(rhex)
    return int(rhex,16)


def write_addr(ser,addr,data):
    print('writing buffer offset 0x%02x'%addr)
    ser.write(bytes('s01\r\n','UTF-8'))
    logging.debug(ser.readline())
    ser.write(bytes('s%02x\r\n'%(addr&0xff),'UTF-8'))
    logging.debug(ser.readline())
    ser.write(bytes('s%02x\r\n'%(data&0xff),'UTF-8'))
    logging.debug(ser.readline())
    
    print('waiting response')
    ser.write(bytes('r\r\n','UTF-8'))
    r=ser.readline()
    logging.debug(r)
    rhex=r.decode('ASCII')[1:3]

def read_page(ser,addr):
    print('reading page 0x%04x to buffer'%addr)
    ser.write(bytes('s04\r\n','UTF-8'))
    logging.debug(ser.readline())
    ser.write(bytes('s%02x\r\n'%((addr>>8)&0xff),'UTF-8'))
    logging.debug(ser.readline())
    ser.write(bytes('s%02x\r\n'%(addr&0xff),'UTF-8'))
    logging.debug(ser.readline())
    
    print('waiting response')
    ser.write(bytes('r\r\n','UTF-8'))
    r=ser.readline()
    logging.debug(r)
    rhex=r.decode('ASCII')[1:3]

def write_page(ser,addr):
    print('writing page 0x%04x from buffer'%addr)
    ser.write(bytes('s05\r\n','UTF-8'))
    logging.debug(ser.readline())
    ser.write(bytes('s%02x\r\n'%((addr>>8)&0xff),'UTF-8'))
    logging.debug(ser.readline())
    ser.write(bytes('s%02x\r\n'%(addr&0xff),'UTF-8'))
    logging.debug(ser.readline())
    
    print('waiting response')
    ser.write(bytes('r\r\n','UTF-8'))
    r=ser.readline()
    logging.debug(r)
    rhex=r.decode('ASCII')[1:3]

def hash_buffer(ser):
    print('hasing buffer')
    ser.write(bytes('s03\r\n','UTF-8'))
    logging.debug(ser.readline())
    
    print('waiting response')
    ser.write(bytes('r\r\n','UTF-8'))
    r=ser.readline()
    logging.debug(r)
    rhex=r.decode('ASCII')[1:3]
    print(rhex)


# high-level function


def proc(port_path,fn):
    ser=serial.Serial(port_path,19200)
    logging.info('opened %s'%ser)

    enter_debug(ser)
    time.sleep(0.5)
    fn(ser)
    time.sleep(0.5)
    enter_normal(ser)

def main():
    ps=argparse.ArgumentParser(description='optical programmer')
    ps.add_argument('-P',dest='port',help='port path (typically /dev/ttyUSBn)',required=True)
    ps.add_argument('--addr',dest='addr',help='memory address to read/write (in bytes)')
    ps.add_argument('command',choices=['status','read'])
    args=ps.parse_args()
    
    if args.command=='status':
        proc(args.port,get_power)
    elif args.command=='read':
        proc(args.port,lambda ser:read_addr(ser,args.addr))
    elif args.command=='write':
        pass


if __name__=='__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()


