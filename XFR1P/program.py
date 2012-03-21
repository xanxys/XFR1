#!/bin/env python3
import sys
import serial
import argparse
import time
import logging

# representing real programmer (arduino) interface
# bit like RPC over serial
class Programmer:
    def __init__(self,serial_path):
        ser=serial.Serial(serial_path,19200)
        logging.info('opened %s'%ser)
        self.serial=ser
    
    # low level function
    def _send(self,command):
        logging.debug('programmer<%s'%command)
        self.serial.write(bytes(command+'\r\n','ASCII'))
    
    def _receive(self):
        while True:
            s=self.serial.readline().decode('ASCII').rstrip()
            if s[0]=='#':
                logging.debug('programmer:%s'%s)
            elif s[0]=='-':
                logging.debug('programmer:%s'%s)
                return s[1:]
            elif s[0]=='!':
                raise IOError('programmer failed to complete the command for some reason')
            else:
                raise NotImplementedError(
                    'unknown status %s. Maybe firmware and driver code is not in sync'%s)
        
    # exposed methods
    def version(self):
        self._send('v')
        self._receive()
    
    def enter_debug(self):
        self._send('d')
        self._receive()
    
    def enter_normal(self):
        self._send('n')
        self._receive()
    
    def send_byte(self,data):
        self._send('s%02x'%data)
        self._receive()
    
    def recv_byte(self,timeout):
        self._send('r%02x'%int(timeout))
        return int(self._receive()[0:2],16)



# expose ring(XFR1) debug mode functionality via Programmer
class Ring(Programmer):
    def get_power(self):
        print('checking power')
        print('sending request')
        self.send_byte(2)
        
        print('waiting response')
        v=self.recv_byte(10)
        print('Vcc=%.1f V'%(1.1/(v/256)))

    def read_buffer(self,addr):
        addr=int(addr,16)
        
        print('reading buffer offset 0x%02x'%addr)
        self.send_byte(0)
        self.send_byte(addr)
        
        print('waiting response')
        v=self.recv_byte(10)
        print('%02x'%v)


    def write_buffer(self,addr,data):
        addr=int(addr,16)
        data=int(data,16)
        
        print('writing buffer offset 0x%02x'%addr)
        self.send_byte(1)
        self.send_byte(addr)
        self.send_byte(data)
        
        print('waiting response')
        self.recv_byte(10)

    def read_page(self,addr):
        addr=int(addr,16)
        
        print('reading page 0x%04x to buffer'%addr)
        self.send_byte(4)
        self.send_byte((addr>>8)&0xff)
        self.send_byte(addr&0xff)
        
        print('waiting response')
        self.recv_byte(10)

    def write_page(self,addr):
        addr=int(addr,16)
        
        print('writing page 0x%04x from buffer'%addr)
        self.send_byte(5)
        self.send_byte((addr>>8)&0xff)
        self.send_byte(addr&0xff)

        print('waiting response')
        self.recv_byte(10)

    def hash_buffer(self):
        print('hasing buffer')
        self.send_byte(3)
        
        print('waiting response')
        v=self.recv_byte(10)
        print('%02x'%v)


# high-level function


def proc(args,fn):
    prog=Ring(args.port)

    if not args.noreset_enter:
        prog.enter_debug()
        time.sleep(0.5)
    
    fn(prog)
    
    if not args.noreset_leave:
        time.sleep(0.5)
        prog.enter_normal()

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
        proc(args,lambda p:p.get_power())
    # buffer manipulation
    elif args.command=='read':
        proc(args,lambda p:p.read_buffer(args.addr))
    elif args.command=='write':
        proc(args,lambda p:p.write_buffer(args.addr,args.data))
    elif args.command=='hash':
        proc(args,lambda p:p.hash_buffer())
    # page manipulation
    elif args.command=='read_page':
        proc(args,lambda p:p.read_page(args.addr))
    elif args.command=='write_page':
        proc(args,lambda p:p.write_page(args.addr))


if __name__=='__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()


