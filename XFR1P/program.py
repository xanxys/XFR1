#!/bin/env python3
import sys
import serial
import binascii
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
        
        # hack: cf. http://stackoverflow.com/questions/8149628/pyserial-not-talking-to-arduino
        # 2012/4/1: XFR1P is non-responding. gtkterm correctly.
        # When I opened the port in gtkterm first, then it works correctly (although the readings
        # are split in gtkterm and program.py)
        # This hack seems to solve that port initiation problem.
        ser.timeout=5
        ser.readline()
        ser.timeout=None
        
        self.serial=ser
    
    # low level function
    def _send(self,command):
        logging.debug('programmer<%s'%command)
        self.serial.write(bytes(command+'\r\n','ASCII'))
        self.serial.flush()
    
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
        logging.info('checking power')
        self.send_byte(2)
        
        logging.info('waiting response')
        v=self.recv_byte(10)
        return 1.1/(v/256)

    def read_buffer(self,addr):
        logging.info('reading buffer offset 0x%02x'%addr)
        self.send_byte(0)
        self.send_byte(addr)
        
        logging.info('waiting response')
        v=self.recv_byte(10)
        return v


    def write_buffer(self,addr,data):
        logging.info('writing buffer offset 0x%02x'%addr)
        self.send_byte(1)
        self.send_byte(addr)
        self.send_byte(data)
        
        logging.info('waiting response')
        self.recv_byte(10)

    def read_page(self,addr):
        logging.info('reading page 0x%04x to buffer'%addr)
        self.send_byte(4)
        self.send_byte((addr>>8)&0xff)
        self.send_byte(addr&0xff)
        
        logging.info('waiting response')
        self.recv_byte(255)

    def write_page(self,addr):
        logging.info('writing page 0x%04x from buffer'%addr)
        self.send_byte(5)
        self.send_byte((addr>>8)&0xff)
        self.send_byte(addr&0xff)

        logging.info('waiting response')
        self.recv_byte(100)

    def hash_buffer(self):
        logging.info('calculating hash of buffer')
        self.send_byte(3)
        
        logging.info('waiting response')
        return self.recv_byte(100)


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
        def set_offset_with_retry(ofs,d):
            retry=0
            while retry<3:
                try:
                    self.write_buffer(ofs,d)
                    return
                except IOError:
                    retry+=1
            raise IOError('too many retries. aborting page write.')
        
        print('writing page %04x'%addr)
        for i in range(128):
            set_offset_with_retry(i,data[i])
        
        hr=self.hash_buffer()
        hd=xorshift_hash(data)
        
        if hr!=hr: # data corruption
            raise IOError('hash mismatch when transferring page: '+
                'hash(dev)=%02x hash(data)=%02x'%(hr,hd))
        
        self.write_page(addr)

    # hex level (bunch of highly localized (addr,data) pairs)
    def program(self,datapath):
        pages=pack_pages(decode_intel_hex(datapath))
        print('writing %d bytes'%(len(pages)*128)) # not really correct estimate
        print('%d pages to go'%len(pages))
        
        for pa,pd in pages.items():
            # page fetch needed if pd is partial
            page=pd
            if any([v==None for v in pd]):
                page_curr=self.read_whole_page(pa)
                if len(page_curr)!=len(pd):
                    raise IOError('page size mismatch')
                
                page=bytes([pd[i] if pd[i]!=None else page_curr[i] for i in range(128)])
            
            # write page
            self.write_whole_page(pa,page)
            print('#')
    
    def verify(self,datapath):
        pages=pack_pages(decode_intel_hex(datapath))
        print('verifying %d bytes'%(len(pages)*128)) # not really correct estimate
        print('%d pages to go'%len(pages))
        
        for pa,pd in pages.items():
            page=self.read_whole_page(pa)
            if len(page)!=len(pd):
                raise IOError('page size mismatch')
            
            for i in range(128):
                if pd[i]!=None and page[i]!=pd[i]:
                    print('Error in page %04x, offset %02x'%(pa,i))
                    print('expected:%02x'%pd[i])
                    print('read:%02x'%page[i])
                    return False
        
        return True
    

# see http://en.wikipedia.org/wiki/Intel_HEX
def decode_intel_hex(path):
    def parse_line(l):
        if l[0]!=':':
            raise IOError('expected ":"')
        else:
            byte_count=int(l[1:3],16)
            address=int(l[3:7],16)
            rec_type=int(l[7:9],16)
            
            if rec_type==0:
                return {'address':address,'data':bytes.fromhex(l[9:9+2*byte_count])}
            elif rec_type==1:
                return None # EoF record
            elif rec_type==3:
                return None # start segment address record
            else:
                raise NotImplementedError('unknown record type %d'%rec_type)
    
    return list(filter(lambda x:x!=None,[parse_line(l) for l in open(path,'r') if l!='']))

def pack_pages(cs):
    '''
    Take chunks from decode_intel_hex(...).
    returns pageaddress -> [None or data]
    '''
    def align(x):
        return x&0xff80
    
    pages={}
    
    for c in cs:
        addr_st=c['address']
        for ofs,d in enumerate(c['data']):
            addr=addr_st+ofs
            pa=align(addr)
            po=addr-pa
            
            page=pages.get(pa,[None]*128)
            page[po]=d
            pages[pa]=page
    
    return pages
        
    

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
    ps.add_argument('--data',dest='data',help='hex value or path to intel hex file')
    ps.add_argument('--noreset_enter',dest='noreset_enter',default=False,const=True,
        action='store_const',help="don't reset to debug mode when entering session")
    ps.add_argument('--noreset_leave',dest='noreset_leave',default=False,const=True,
        action='store_const',help="don't reset to normal mode when leaving session")
    ps.add_argument('--debug',dest='loglevel',default=logging.WARNING,const=logging.DEBUG,
        action='store_const',help='enable very verbose logging')
    ps.add_argument('command',choices=[
        '_status','_read','_write','_hash','_read_page','_write_page', # Ring
        'read_page','write_page',
        'program','verify'
        ])
    args=ps.parse_args()
    logging.basicConfig(level=args.loglevel)
    
    ## low level interface
    if args.command=='_status':
        proc(args,lambda p:print('Vcc=%.1f V'%(p.get_power())))
    # buffer manipulation
    elif args.command=='_read':
        proc(args,lambda p:print(p.read_buffer(int(args.addr,16))))
    elif args.command=='_write':
        proc(args,lambda p:p.write_buffer(int(args.addr,16),int(args.data,16)))
    elif args.command=='_hash':
        proc(args,lambda p:print('hash=%02x'%p.hash_buffer()))
    # page manipulation
    elif args.command=='_read_page':
        proc(args,lambda p:p.read_page(int(args.addr,16)))
    elif args.command=='_write_page':
        proc(args,lambda p:p.write_page(int(args.addr,16)))
    ## high level interface
    elif args.command=='read_page':
        proc(args,lambda p:print(binascii.hexlify(p.read_whole_page(int(args.addr,16)))))
    elif args.command=='write_page':
        proc(args,lambda p:p.write_whole_page(int(args.addr,16),bytes.fromhex(args.data)))
    ## common interface
    elif args.command=='program':
        def p_and_v(p):
            p.program(args.data)
            if p.verify(args.data):
                print('programmed successfully!')
            else:
                print('program failed')
        proc(args,p_and_v)
    elif args.command=='verify':
        def v(p):
            if p.verify(args.data):
                print('verify ok!')
            else:
                print('verify failed')
        proc(args,v)

if __name__=='__main__':
    main()


