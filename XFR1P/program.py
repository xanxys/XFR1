#!/bin/env python3
import sys
import serial
import argparse
import time
import logging

# utility
def xorshift_hash(data):
    h=0
    for byte in data:
        h=((h<<1)|(h>>7))^byte
    return h

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
        self.send_byte(2)
        
        print('waiting response')
        v=self.recv_byte(10)
        print('Vcc=%.1f V'%(1.1/(v/256)))

    def read_buffer(self,addr):
        print('reading buffer offset 0x%02x'%addr)
        self.send_byte(0)
        self.send_byte(addr)
        
        print('waiting response')
        v=self.recv_byte(10)
        print('%02x'%v)
        return v


    def write_buffer(self,addr,data):
        print('writing buffer offset 0x%02x'%addr)
        self.send_byte(1)
        self.send_byte(addr)
        self.send_byte(data)
        
        print('waiting response')
        self.recv_byte(10)

    def read_page(self,addr):
        print('reading page 0x%04x to buffer'%addr)
        self.send_byte(4)
        self.send_byte((addr>>8)&0xff)
        self.send_byte(addr&0xff)
        
        print('waiting response')
        self.recv_byte(255)

    def write_page(self,addr):
        print('writing page 0x%04x from buffer'%addr)
        self.send_byte(5)
        self.send_byte((addr>>8)&0xff)
        self.send_byte(addr&0xff)

        print('waiting response')
        self.recv_byte(100)

    def hash_buffer(self):
        print('hasing buffer')
        self.send_byte(3)
        
        print('waiting response')
        v=self.recv_byte(100)
        print('%02x'%v)


# expose flash/buffer of Ring
class RingMemory(Ring):
    # page level
    def read_whole_page(self,addr):
        def get_offset_with_retry(ofs):
            retry=0
            while retry<3:
                try:
                    return self.read_buffer(ofs)
                except IOError:
                    retry+=1
            raise IOError('too many retries. aborting page read.')
            
        print('reading page %04x'%addr)
        self.read_page(addr)
        vs=[get_offset_with_retry(i) for i in range(128)]
        
        hr=self.hash_buffer()
        hd=xorshift_hash(vs)

        if hr!=hr: # data corruption
            raise IOError('hash mismatch when transferring page: '+
                'hash(dev)=%02x hash(data)=%02x'%(hr,hd))
        
        return bytes(vs)
    
    def write_whole_page(self,addr,data):
        print('writing page %04x'%addr)
        for i in range(128):
            self.write_buffer(i,data[i])
        
        hr=self.hash_buffer()
        hd=xorshift_hash(data)
        
        if hr!=hr: # data corruption
            raise IOError('hash mismatch when transferring page: '+
                'hash(dev)=%02x hash(data)=%02x'%(hr,hd))
        
        self.write_page(addr)
        
        
    

def proc(args,fn):
    prog=RingMemory(args.port)

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
    ps.add_argument('command',choices=[
        '_status','_read','_write','_hash','_read_page','_write_page', # Ring
        'read_page','write_page'
        ])
    args=ps.parse_args()
    
    ## low level interface
    if args.command=='_status':
        proc(args,lambda p:p.get_power())
    # buffer manipulation
    elif args.command=='_read':
        proc(args,lambda p:p.read_buffer(int(args.addr,16)))
    elif args.command=='_write':
        proc(args,lambda p:p.write_buffer(int(args.addr,16),int(args.data,16)))
    elif args.command=='_hash':
        proc(args,lambda p:p.hash_buffer())
    # page manipulation
    elif args.command=='_read_page':
        proc(args,lambda p:p.read_page(int(args.addr,16)))
    elif args.command=='_write_page':
        proc(args,lambda p:p.write_page(int(args.addr,16)))
    ## high level interface
    elif args.command=='read_page':
        proc(args,lambda p:p.read_whole_page(int(args.addr,16)))


if __name__=='__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()


