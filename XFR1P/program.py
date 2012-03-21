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
    ser.write(bytes('r0a\r\n','UTF-8'))
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
    ser.write(bytes('r0a\r\n','UTF-8'))
    r=ser.readline()
    logging.debug(r)
    rhex=r.decode('ASCII')[1:3]
    print(rhex)
    return int(rhex,16)


def write_buffer(ser,addr,data):
    addr=int(addr,16)
    data=int(data,16)
    
    print('writing buffer offset 0x%02x'%addr)
    ser.write(bytes('s01\r\n','UTF-8'))
    logging.debug(ser.readline())
    ser.write(bytes('s%02x\r\n'%(addr&0xff),'UTF-8'))
    logging.debug(ser.readline())
    ser.write(bytes('s%02x\r\n'%(data&0xff),'UTF-8'))
    logging.debug(ser.readline())
    
    print('waiting response')
    ser.write(bytes('r0a\r\n','UTF-8'))
    r=ser.readline()
    logging.debug(r)
    rhex=r.decode('ASCII')[1:3]

def read_page(ser,addr):
    addr=int(addr,16)
    
    print('reading page 0x%04x to buffer'%addr)
    ser.write(bytes('s04\r\n','UTF-8'))
    logging.debug(ser.readline())
    ser.write(bytes('s%02x\r\n'%((addr>>8)&0xff),'UTF-8'))
    logging.debug(ser.readline())
    ser.write(bytes('s%02x\r\n'%(addr&0xff),'UTF-8'))
    logging.debug(ser.readline())
    
    print('waiting response')
    ser.write(bytes('r0a\r\n','UTF-8'))
    r=ser.readline()
    logging.debug(r)
    rhex=r.decode('ASCII')[1:3]

def write_page(ser,addr):
    addr=int(addr,16)
    
    print('writing page 0x%04x from buffer'%addr)
    ser.write(bytes('s05\r\n','UTF-8'))
    logging.debug(ser.readline())
    ser.write(bytes('s%02x\r\n'%((addr>>8)&0xff),'UTF-8'))
    logging.debug(ser.readline())
    ser.write(bytes('s%02x\r\n'%(addr&0xff),'UTF-8'))
    logging.debug(ser.readline())
    
    print('waiting response')
    ser.write(bytes('r0a\r\n','UTF-8'))
    r=ser.readline()
    logging.debug(r)
    rhex=r.decode('ASCII')[1:3]

def hash_buffer(ser):
    print('hasing buffer')
    ser.write(bytes('s03\r\n','UTF-8'))
    logging.debug(ser.readline())
    
    print('waiting response')
    ser.write(bytes('r0a\r\n','UTF-8'))
    r=ser.readline()
    logging.debug(r)
    rhex=r.decode('ASCII')[1:3]
    print(rhex)


# high-level function


def proc(args,fn):
    ser=serial.Serial(args.port,19200)
    logging.info('opened %s'%ser)

    if not args.noreset_enter:
        enter_debug(ser)
        time.sleep(0.5)
    
    fn(ser)
    
    if not args.noreset_leave:
        time.sleep(0.5)
        enter_normal(ser)

def main():
    ps=argparse.ArgumentParser(description='optical programmer')
    ps.add_argument('-P',dest='port',help='port path (typically /dev/ttyUSBn)',required=True)
    ps.add_argument('--addr',dest='addr',help='memory address to read/write (in bytes)')
    ps.add_argument('--data',dest='data')
    ps.add_argument('--noreset_enter',dest='noreset_enter',default=False,const=True,
        action='store_const',help="don't reset to debug mode when entering session")
    ps.add_argument('--noreset_leave',dest='noreset_leave',default=False,const=True,
        action='store_const',help="don't reset to normal mode when leaving session")
    ps.add_argument('command',choices=
        ['status','read','write','hash','read_page','write_page'])
    args=ps.parse_args()
    
    if args.command=='status':
        proc(args,get_power)
    # buffer manipulation
    elif args.command=='read':
        proc(args,lambda ser:read_buffer(ser,args.addr))
    elif args.command=='write':
        proc(args,lambda ser:write_buffer(ser,args.addr,args.data))
    elif args.command=='hash':
        proc(args,hash_buffer)
    # page manipulation
    elif args.command=='read_page':
        proc(args,lambda ser:read_page(ser,args.addr))
    elif args.command=='write_page':
        proc(args,lambda ser:write_page(ser,args.addr))


if __name__=='__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()


