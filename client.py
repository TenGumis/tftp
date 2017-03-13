#!/usr/bin/env python3

import socket
import sys
import hashlib
from random import random
from time import sleep

HOST = sys.argv[1]
PORT = int(sys.argv[2])
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.5)
windowsize=16
filename = sys.argv[3]
lastPackage=0
packageNumber=1
packageCounter=0
res=[]
recive=True

#read request
exc=b'\0\1'+filename.encode()+b'\0'+b'octet'+b'\0'+b'windowsize\0'+str(windowsize).encode()+b'\0', (HOST, PORT)
sock.sendto(*exc)

#window size negotiation
while True:
    try:
        msg, addr = sock.recvfrom(516)
    except socket.timeout:
        sock.sendto(*exc)
        continue

    if msg[0:2] == b'\0\6' and len(msg[2:].split(b'\0'))>2:
        windowsize=int(msg[2:].split(b'\0')[1])
        exc=(b'\0\4\0\0', addr)
        sock.sendto(*exc)
        break

    if msg[0:2] == b'\0\5':
        recive=False
        print('Error with code: '+str(int.from_bytes(msg[2:4],'big'))+' '+msg[4:].decode())
        break
        
#reciving data
while recive:
    try:
        msg, addr = sock.recvfrom(516)
    except socket.timeout:
        exc=(b'\0\4'+lastPackage.to_bytes(2, byteorder='big'), addr)
        sock.sendto(*exc)
        continue

    if msg[0:2] == b'\0\3':
        ack=False
        recivedNumber=int.from_bytes(msg[2:4],'big')
        if recivedNumber == packageNumber:
            packageCounter+=1
            res.append(msg[4:])
            lastPackage=packageNumber
            packageNumber=(packageNumber+1)%65536                
            if packageCounter==windowsize or len(msg[4:])<512:
                ack=True
                packageCounter=0

        elif recivedNumber>packageNumber:
            ack=True
            packageCounter=0
            
        elif recivedNumber < (packageNumber+windowsize)%65536 and packageNumber+windowsize>65536 :
            ack=True
            packageCounter=0

        if ack:
            exc=(b'\0\4'+lastPackage.to_bytes(2, byteorder='big'), addr)
            sock.sendto(*exc)
            packageCounter=0
            
        if len(msg[4:])<512:
            break

    if msg[0:2] == b'\0\5':
        print('Error with code: '+str(int.from_bytes(msg[2:4],'big'))+' '+msg[4:].decode())
        break

if(recive):
    m = hashlib.md5()
    res=b''.join(res)
    print('file size:',len(res),'bytes')
    m.update(res)
    print ('file md5 hash:',m.hexdigest())
    f = open(filename, 'bw')
    f.write(res)
    
