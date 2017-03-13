#!/usr/bin/env python3

import socket
import sys
import hashlib
import threading
import os.path

HOST = "localhost"
PORT = int(sys.argv[1])
DIR = sys.argv[2]
WINDOWSIZE=16

class Server:

    def __init__(self,host,port,directory,windowsize):
        self.HOST=host
        self.PORT=port
        self.DIRECTORY=directory
        self.WINDOWSIZE=windowsize

    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((HOST,PORT))
            while True:         
                msg, addr = self.sock.recvfrom(516)
                opc=msg[0:2]
                
                if(opc==b'\0\1' and len(msg[2:].split(b'\0'))==5):

                    filename,mode,windowsize,blocks,tmp = msg[2:].split(b'\0')
                    blocks=int(str(blocks,'utf-8'))
                    fileExists=os.path.isfile(self.DIRECTORY+'/'+str(filename,'utf-8'))                    
                    if not fileExists:
                        msg=(b'\0\5\0\1'+b'File not found'+b'\0', addr )
                        self.sock.sendto(*msg)
                        continue

                    if(mode==b'octet' and windowsize==b'windowsize' and blocks<65536 and blocks>0):
                        blocks=min(blocks,self.WINDOWSIZE)
                        Client(addr,self.DIRECTORY,filename,blocks).start()
                    else:
                        msg=(b'\0\5\0\4'+b'Wrong message format'+b'\0', addr )
                        self.sock.sendto(*msg)
                else:
                    msg=(b'\0\5\0\4'+b'Wrong message format'+b'\0', addr )
                    self.sock.sendto(*msg)
        finally:
            self.sock.close()
        

class Client(threading.Thread):

    def __init__(self,addr,directory,f,blocks):
        super().__init__(daemon=True)
        self.ADDR=addr
        self.DIRECTORY=directory
        self.FILE=f
        self.WINDOWSIZE=blocks


    def run(self):
        try:
            self.socket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('',0))
            self.socket.settimeout(1)
            print('sending: '+self.DIRECTORY+'/'+str(self.FILE,'utf-8'))
            f = open(self.DIRECTORY+'/'+str(self.FILE,'utf-8'),'br')
            lastPackage=0
            packageNumber=1
            end=False
            messages=[]
            #window size negotiation
            counter=10
            while(True):
                if counter==0:
                    print("Negotiation failed!")
                    return
                msg=(b'\0\6'+b'windowsize\0'+str(self.WINDOWSIZE).encode()+b'\0', self.ADDR )
                self.socket.sendto(*msg)
                try:
                    msg , addr =self.socket.recvfrom(4);
                    if msg==b'\0\4\0\0':                    
                        break
                    elif msg[0:2]==b'\0\5':
                        return
                except socket.timeout:
                    counter-=1
                    self.socket.sendto(*msg)
            
            #sending data
            while(True):
                while len(messages)<self.WINDOWSIZE :
                    if(end):
                        break
                    text=f.read(512)
                    messages.append(text)
                    if(len(text)<512):
                        end=True
                        break;
                if(len(messages)==0):
                    print("The file has been send successfully!")
                    break;
                for i in range(len(messages)):            
                    msg=(b'\0\3'+((packageNumber+i)%65536).to_bytes(2, byteorder='big')+messages[i], self.ADDR )
                    self.socket.sendto(*msg)
                counter=5
                while(counter):
                    counter-=1
                    try:
                        msg , addr =self.socket.recvfrom(4);
                        ackNumber=int(int.from_bytes(msg[2:],'big'))
                        
                        if( ackNumber == lastPackage ):
                            howManyOk=0
                        else:
                            if( ackNumber>=packageNumber ):
                                howManyOk=ackNumber-packageNumber+1
                            else:
                                howManyOk=65536-packageNumber
                                howManyOk+=ackNumber+1
                        for i in range(howManyOk):
                            messages.pop(0)
                        packageNumber=ackNumber
                        break
                    except socket.timeout:
                        for i in range(len(messages)):            
                            msg=(b'\0\3'+((packageNumber+i)%65536).to_bytes(2, byteorder='big')+messages[i], self.ADDR )
                            self.socket.sendto(*msg)
                        print("again")  
                else:
                    print("Communication failed!")
                    return  

                lastPackage=packageNumber
                packageNumber=(packageNumber+1)%65536
        finally:
            self.socket.close()

server= Server(HOST,PORT,DIR,WINDOWSIZE)
server.run()
