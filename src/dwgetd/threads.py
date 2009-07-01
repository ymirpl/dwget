# coding=utf8
from pydispatch import dispatcher
from threading import Thread
import sys
import time
import socket 
import os, os.path


class MainThread(Thread):
    '''
    Class which task is communication between user interface (system console)
    and other parts of the dwget.
    '''   
    __socketFileName = 'stefan' # nazwa pliku w tempie
    __msg = u''
  
  
    # TODO lapac wyjatki o socketow
    def setupSocket(self):
        if os.path.exists("/tmp/"+self.__socketFileName): os.remove("/tmp/"+self.__socketFileName)
        
        self.__server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) # tutaj bedziemy sluchac na polecenia od konsoli
        
        if not self.__server:
            dispatcher.send('ERROR', 'masterMainThread', 'Can\'t open UNIX socket in /tmp')

        self.__server.bind("/tmp/"+self.__socketFileName)
                
        self.__server.listen(1)
                    
    def __init__ (self):
        Thread.__init__(self)
        dispatcher.send('DEBUG', 'masterMainThread', '__init__')
        self.setupSocket()
        self.daemon = True
        
        
           
    def run(self):
        
        while True:
            connection, address = self.__server.accept()     
            while True: 
                data = connection.recv(1024) 
                self.__msg = self.__msg + data
                
                if data and data[-1] == '\n': break 
               
            self.__msg = self.__msg.strip();
            

            [command, arg] = self.__msg.split(' ')
 
            dispatcher.send(command, 'masterMainThread', arg)
            dispatcher.send('REPLY_SOCKET', 'masterMainThread', connection)
            self.__msg = ''

    def __del__(self):
        self.__server.close()
        
class SlaveThread(Thread):
    '''
    Class representing a thread fired when there is a need to communicate with 
    specified slave. An instance of this class is created when there is need to send
    information. After reciveing confirmation or error message the instance of class
    is removed.
    '''
    
    __ip = '' 
    __sock = None
    data = None
    receivedData = None
    parent = None
    file_fragment_done = False   
    
    def __init__(self, parent, ip, binFilename = None):
        self.__ip = ip
        self.__binFilename = binFilename
        self.parent = parent
        self.downloaded = False
        
        Thread.__init__(self)
        dispatcher.send('DEBUG', 'SlaveThread', '__init__')
        self.daemon = True
        self.isAlive = True
    
    def setup__socket(self):
        self.__sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.__sock.settimeout(10)
        
        if not self.__sock:
            dispatcher.send('ERROR', 'SlaveThread', 'Can\'t open __socket in slaveThread')
    
    def run(self):
        dispatcher.send('DEBUG', 'SlaveThread', 'Sending data...')
        
        triedCounter = 0
        
        while 1:
            try:
                self.setup__socket()
                self.__sock.connect((self.__ip, 6678)) # port na sztywno poki co # DEBUG
         
                sent = 0
                while sent < len(self.data):
                    sent += self.__sock.send(self.data[sent:])
                dispatcher.send('DEBUG', 'SlaveThread', 'Data sent...')        
                
                
                #print '!!!!!!!!!!!!!!!!!'
                #print self.__binFilename
                
                if not self.__binFilename:
                    dispatcher.send('DEBUG', 'SlaveThread', 'XML mode')        
                
                    self.receivedData = ''
                    while 1:
                        data = self.__sock.recv(1024)
                        if not data: break
                        self.receivedData = self.receivedData + data
                else:
                     dispatcher.send('DEBUG', 'SlaveThread', 'Binary mode')
                     # TODO Co uzywa dispatcher.self.receivedData
                     self.receivedData = 'binary data: ..010010001110010...'        

                     self.__binFilename.seek(0)
                     debug = 0
                     while 1:
                        data = self.__sock.recv(128000)
                        debug += len(data)
                        self.__binFilename.write(data)
                        if not data: break
                     self.__binFilename.flush()
                     self.downloaded = self.__binFilename.tell()
                     self.file_fragment_done = True
#                     print "ŁÓÓÓÓÓÓÓÓÓÓÓÓÓ!!!!!!!!!!"
#                     print "%d %d" % (self.__binFilename.tell(), debug)
#                     print "ŁÓÓÓÓÓÓÓÓÓÓÓÓÓ!!!!!!!!!!"
                
                break
            except:
                  print sys.exc_info()
                  dispatcher.send('ERROR', 'SlaveThread', 'Connection to slave %s timed out' % (self.__ip))
                  dispatcher.send('CONN_TIMEOUT', 'SlaveThread', self)
                  print "TAJMAUT"
                  self.__sock.close()
                  #time.sleep(1)
                  triedCounter += 1
                  if triedCounter > 3:
                      print "SLAVE DEAD", self
                      self.parent.markAsProbablyDead()
                      triedCounter = 0
                      self.isAlive = False
                      self.__sock.close()
                      return
                  
                  continue            
          
        #dispatcher.send('CHAT_FINISHED', 'SlaveThread', self.receivedData)
        if self.receivedData:
            self.parent.chatFinished(self.receivedData)
        self.isAlive = False
        self.__sock.close()
        # TODO might need more attention, where to close __socket
        
    def __del__(self):
        self.__sock.close()
        
        
class ReportingThread(Thread):
    '''
    Class representing a thread which purpose is to ask for a report from the slave
    once in every 2 seconds.
    Every instance of slave class handles its own reporting thread which is asking
    for a report.
    '''
        
    def __init__(self, slave):
        Thread.__init__(self)
        self.setDaemon(True)
        self.alive = True
        self.slave = slave
        
    def run(self):
        while 1:
            if self.alive:
                self.slave.updateReport()
            time.sleep(2)
            
        


        
        
    
                
            