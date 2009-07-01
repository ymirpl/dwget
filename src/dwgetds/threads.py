# coding=utf8
from pydispatch import dispatcher

import time
import sys
from threading import Thread, Timer
from socket import socket, AF_INET, SOCK_STREAM
from tempfile import NamedTemporaryFile  
from common.consts import *
from common.http import parseHeaders
from common.ftp import *
from collections import deque

class BadResponseCode(Exception):
    pass
class WriteToTmpFileFailed(Exception):
    pass
class NoResumeSupportThoughRequested(Exception):
    pass
class AbortDownloadException(Exception):
    pass
class IncompleteFileException(Exception):
    pass

class IncorrectFTPResponse(Exception):
    pass

class speedThread(Thread):
    """
    Thread responsible for measuring current and average speed for a chosen
    downloadThread. 
    
    average - over the course of the last 5 seconds
    """
    dThread = None
    
    def __init__(self, dThread):
        Thread.__init__(self)
        self.setDaemon(True)
        self.dThread = dThread
        self.stopped = True
        self.alive = True
    
    def startTimer(self):
        """
        Restarts measurement.
        """
        self.stopped = False
    
    def stopTimer(self):
        """
        Stops measurement.
        """
        self.stopped = True
        
    def kill(self):
        """
        Kills the thread.
class IncompleteFileException(Exception):
    pass
        """
        self.alive = False
        
    def run(self):
        while self.alive:
            if not self.stopped:
                s= 1.0
                self.dThread.speed = (self.dThread.received - self.dThread.lastReceived)/s
                self.dThread.lastReceived = self.dThread.received 
                self.dThread.speedDeque.appendleft(self.dThread.speed)
                self.dThread.speedDeque.pop()
                dispatcher.send('DLTHREAD_SPEED', self, self.dThread.speed)
                speed5s = 0.
                for i in self.dThread.speedDeque:
                    speed5s += i
                speed5s /= 5.
                self.dThread.speed5s = speed5s
                dispatcher.send('DLTHREAD_5s_SPEED', self, speed5s)
            time.sleep(1)

class downloadThread(Thread):
    """
    Thread responsible for downloading a file from
    the chosen location.
    
    It retries connection infinitely in 3-second intervals, if needed,
    unless there's a fatal error (FAILED state).
    """    
    # @TODO: After retry, it should resume at the position it last failed, not start from the beginning.
    # @DONE: Has to be able to download the whole file (use the usual GET request, wait for 200 code).
    # @PROBABLYNOTNEEDED: Has to implement chunked downloading (some servers might do that, have to find one by the way).
    # @DEFERRED: Reconsider socket timeout (3s so far).
    # @REVERTED: End of connection might actually mean that the network inteface went down, not that we received whole file. Check if self.received == self.length.
    
    url = ''
    host = ''
    protocol= 'http'
    port = 80
    file = None
    begin = 0
    beginResume = 0
    written = 0
    length = 0
    
    received = 0
    lastReceived = 0
    speedDeque = deque()
    speed = 0
    speed5s = 0
    tempFile = None
    
    timer = None
    
    kill = False
            
    def __init__(self, url, begin, length, tempFile):
        self.kill = False
        self.tempFile = tempFile
        
        Thread.__init__(self)
        self.url = url
        self.begin = begin
        self.beginResume = begin
        self.length = length
        dispatcher.send('DEBUG', 'downloadThread', '__init__')
        
        self.timer = speedThread(self)
        self.timer.start()
        self.daemon = True
        
    def __del__(self):
        dispatcher.send('DEBUG', 'downloadThread', '__del__')
        if self.tempFile:
            self.tempFile.close()
            
    def cancel(self):
        """
        Kills the thread and underlying speed measurement thread.
        """        
        dispatcher.send('DEBUG', 'downloadThread', 'Cancelling...')
        dispatcher.send('STATE_CHANGE', self, (CANCELLING,))
        self.__killChildren()
        
    def __killChildren(self):
        """
        Kills the thread and underlying speed measurement thread.
        """        
        dispatcher.send('DEBUG', 'downloadThread', 'Killing children...')
        self.kill = True
        self.timer.kill()
                
    def zero(self):
        """
        Clears all counters.
        """
        self.lastReceived = 0
        #self.received = 0
        if self.written != 0:
            self.received = self.written
            self.beginResume = self.begin + self.written
        if self.length == -1:
            self.received = 0
            self.written = 0
            self.beginResume = 0
        self.speed = 0.
        self.speedDeque.clear()
        self.timer.stopTimer()
        for i in xrange(5):
            self.speedDeque.append(0.)
        
    def run(self):
        self.zero()
        self.tempFile.seek(self.written)
        # inicjowanie socketa 
        self.sock = socket(AF_INET, SOCK_STREAM) 
        self.sock.settimeout(3)
        if self.sock : 
            dispatcher.send('DEBUG', 'downloadThread.socket', 'Socket creation succeded...') 
        else :
            dispatcher.send('ERROR', 'downloadThread.socket', 'Socket creation failed...')  
        
        self.protocol = self.url[:self.url.find(':')]
        if self.protocol == 'http' : 
            self.port = 80               
        elif self.protocol == 'ftp' : 
            self.port = 21          
        else : 
            dispatcher.send('ERROR', 'downloadThread.socket', 'Unkown protocol...')
            dispatcher.send('STATE_CHANGE', self, (FAILED, UNKNOWN_PROTOCOL))
            return
        self.host = self.url[self.url.find('//') + 2 : ] 
        self.file = self.host[self.host.find('/') : ]
        self.host = self.host[ : self.host.find('/')]
        if self.host.find(':') is not -1:
            try:
                self.port = int(self.host[self.host.find(':')+1:])
            except:
                dispatcher.send('ERROR', 'downloadThread.url', 'Weird port: %s' % (self.host[self.host.find(':')+1:]))
                dispatcher.send('STATE_CHANGE', self, (FAILED, BAD_PORT))
                return
            self.host = self.host[:self.host.find(':')] 
         
        while 1:
            dispatcher.send('STATE_CHANGE', self, (CONNECTING,))
            self.tempFile.seek(self.written)
            try: 
                if self.kill:
                    dispatcher.send('STATE_CHANGE', self, (CANCELLED,))
                    return
                dispatcher.send('DEBUG', 'downloadThread.socket', 'Connecting to %s on port %d...'% (self.host, self.port))
                self.sock.connect((self.host, self.port))
            except:
                self.zero()
                print sys.exc_info()
                dispatcher.send('STATE_CHANGE', self, (CONNECTING_RETRYING,))
                dispatcher.send('ERROR', 'downloadThread.socket', 'Unable to connect, retrying after 3 seconds...')
                time.sleep(3)
                continue                
            try:    
                dispatcher.send('STATE_CHANGE', self, (DOWNLOADING,))
                if self.protocol == 'http':
                    self.getByHTTP()
                elif self.protocol == 'ftp':
                    self.getByFTP()
                else : 
                    dispatcher.send('ERROR', 'downloadThread.socket', 'Unknown protocol...')
                    dispatcher.send('STATE_CHANGE', self, (FAILED, UNKNOWN_PROTOCOL))
                    return
                    
                break
            except AbortDownloadException:
                return
            except NoResumeSupportThoughRequested:
                return
            except WriteToTmpFileFailed:
                return
            except:
                self.zero()
                print sys.exc_info()
                print sys.exc_traceback
                print "%d(%d)/%d" %(self.received, self.written, self.length)
                dispatcher.send('ERROR', 'downloadThread.download', 'Failed to communicate, retrying after 3 seconds...')
                self.sock.close()
                self.sock = socket(AF_INET, SOCK_STREAM) 
                self.sock.settimeout(3)
                dispatcher.send('STATE_CHANGE', self, (DOWNLOADING_RETRYING,))
                time.sleep(3)
                continue
                    
    def getByHTTP(self):
        """
        Implements the HTTP protocol.
        """                
        # Start measurement timer.
        self.timer.startTimer() 
        # Prepare HTTP request
        if self.length != -1:
            # If resume requested... 
            # @TODO: Connection: close
            message = u'GET %s HTTP/1.1\r\nHost: %s:%d\r\nRange:bytes=%d-%d\r\n\r\n' % (self.file, self.host, self.port, self.beginResume, self.begin+self.length-1)
        else:
            # ...and if not.
            message = u'GET %s HTTP/1.1\r\nHost: %s:%d\r\n\r\n' % (self.file, self.host, self.port)
            
        print message
            
        # Send whole message
        dispatcher.send('DEBUG', 'downloadThread.socket', 'Sending HTTP GET request...')
        sent = 0
        while sent < len(message):
            sent += self.sock.send(message[sent:])
        # Receive response 
        dispatcher.send('DEBUG', 'downloadThread.socket', 'Receiving HTTP response...')
        msg = ''
        self.received = self.written # CHANGED!!!! from 0
        self.realReceived = 0
        self.tempFile.seek(self.written)
        responseCode = None
        while 1:                      
            data = self.sock.recv(65536)
            self.received += len(data)
            if responseCode is None:                                # If we haven't yet received headers, 
                if msg.find('\r\n\r\n') is not -1:                  # check if the headers are fully sent.
                    msg += data
                    responseCode, headers = parseHeaders(msg)       # If so, parse them.
                    print headers                                   # @DEBUG
                    # Check the response code.
                    # Has to be 206 if used Range:bytes=%d-%d.
                    try:
                        responseCode = int(responseCode)
                    except:
                        dispatcher.send('ERROR', 'downloadThread.HTTP', 'Received weird HTTP code: %s' % (responseCode))
                        dispatcher.send('STATE_CHANGE', self, (DOWNLOADING_RETRYING,SCRAMBLED_RESPONSE_CODE))
                        raise BadResponseCode()
                    
                    # if resume support requested
                    if self.length != -1 and responseCode == 200:
                        dispatcher.send('ERROR', 'downloadThread.HTTP', 'No resume support found, but requested(%d).' % (responseCode))
                        dispatcher.send('STATE_CHANGE', self, (FAILED, NO_RESUME_THOUGH_REQUESTED))
                        self.__killChildren()
                        raise NoResumeSupportThoughRequested()
                    if (self.length != -1 and responseCode != 206) or (self.length == -1 and responseCode != 200):
                        dispatcher.send('ERROR', 'downloadThread.HTTP', 'Received wrong HTTP code: %d' % (responseCode))
                        dispatcher.send('STATE_CHANGE', self, (DOWNLOADING_RETRYING,WRONG_RESPONSE_CODE))
                        raise BadResponseCode()
                    
                    if self.length == -1 and 'Content-Length' in headers:
                        self.length = int(headers['Content-Length'])
                    
                    # Write the bit we received after the headers to the tmp file.
                    self.received -= msg.find('\r\n\r\n')+4 # Don't need to count headers.
                    msg = msg[msg.find('\r\n\r\n')+4:]
                    
                    try:
                        self.tempFile.write(msg)
                        self.written += len(msg)
                    except:
                        print sys.exc_info()
                        dispatcher.send('ERROR', 'downloadThread.tmpfile', 'Failure while writing to local tmp file.')
                        dispatcher.send('STATE_CHANGE', self, (DOWNLOADING_RETRYING,WRITE_TO_TMP_FILE_FAILED))
                        self.__killChildren()
                        raise WriteToTmpFileFailed()
                    
                else:   
                    msg = msg + data      # If the headers haven't been fully received yet. 
            else:
                self.tempFile.write(data) # Next chunk of downloaded file goes to the tmp file.
                self.written += len(data)
   
            if not data: break                      # Connection broken, which should mean - end of the file.
            if self.written == self.length: break  # Transfer finished, but not closed by the remote host for some reason or another.
            if self.kill:                           # Received a request for the thread to be killed.
                dispatcher.send('STATE_CHANGE', self, (CANCELLED,))
                raise AbortDownloadException()
        
#        if self.received != (self.length-self.begin):
#            dispatcher.send('ERROR', 'downloadThread.HTTP', 'Connection broken, meant to receive: %d, received: %d.' % ((self.length-self.begin), self.received))
#            raise IncompleteFileException       # Will be raised if connection was closed by the remote site, but transfer has not yet been completed.
        
        self.realReceived = self.tempFile.tell() # @DEBUG, I presume
        self.tempFile.seek(0)                    
        dispatcher.send('STATE_CHANGE', self, (FINISHED,))
        self.sock.close()
        self.timer.stopTimer()
        self.tempFile.flush()
        print "Received: %d, Written: %d, Should be equal %d.\n" %(self.received, self.written, self.length)
            
    def estabilishDataConnection(self, IP, port):
        sock = socket(AF_INET, SOCK_STREAM) 
        sock.settimeout(3)
        sock.connect((IP, port))
        
        return sock

    def getByFTP(self):
        """
        Implements the anonymous FTP protocol.
        """                
        # Start measurement timer.
        self.timer.startTimer()
        # Grab the welcome 
        if getLastCode(self.sock)[0] != 220:
            raise IncorrectFTPResponse()
        
        # Anonymous login
        sendMessage(self.sock, "USER anonymous\n")
        lastCode, msg = getLastCode(self.sock)
        if lastCode == 331:
            sendMessage(self.sock, "PASS dwget@dwget.pl")
            lastCode, msg = getLastCode(self.sock) 
        if lastCode != 230:
            raise IncorrectFTPResponse()

        # Find the proper directory
        directories = self.file.split('/')
        file = directories[-1]
        directories = directories[1:-1]
        for dir in directories:
            sendMessage(self.sock, "CWD %s\n"%(dir))
            if getLastCode(self.sock)[0] != 250:
                raise IncorrectFTPResponse()
        
        # Start passive mode, estabilish data connection
        sendMessage(self.sock, "PASV\n")
        lastCode, msg = getLastCode(self.sock)
        if lastCode != 227:
            raise IncorrectFTPResponse()
        msg = msg[msg.find('(')+1:msg.rfind(')')]
        msg = msg.split(',')
        dataIP = "%s.%s.%s.%s"%(msg[0],msg[1],msg[2],msg[3])
        dataPort = int(msg[4])*256+int(msg[5])
        
        dataSocket = self.estabilishDataConnection(dataIP, dataPort)
        
        # Send RETRIEVE file request
        sendMessage(self.sock, "TYPE I\n")        # binary mode
        if getLastCode(self.sock)[0] != 200:
            dataSocket.close()
            raise IncorrectFTPResponse()
        if self.length == -1:
            position = 0
        else:
            position = self.beginResume
        sendMessage(self.sock, "REST %d\n" % (position))  # Start at 'position' byte.
        if getLastCode(self.sock)[0] != 350:
            dataSocket.close()
            raise IncorrectFTPResponse()
        sendMessage(self.sock, "RETR %s\n" % (file))      # Start the transfer
        if getLastCode(self.sock)[0] != 150:
            dataSocket.close()
            raise IncorrectFTPResponse()
            
        dispatcher.send('DEBUG', 'downloadThread.ftpDataSocket', 'Receiving FTP response...')
        msg = ''
        self.received = self.written # CHANGED!!!! from 0
        self.realReceived = 0
        self.tempFile.seek(self.written)
        while 1:                    
            toRead = min(65536, self.length - self.written)  # @TODO: length MUST NOT BE UNKNOWN !!!
            data = dataSocket.recv(toRead)
            self.received += len(data)
            self.written += len(data)
            self.tempFile.write(data)   # Next chunk of downloaded file goes to the tmp file.
            if not data: break                      # Connection broken, which should mean - end of the file.
            if self.written == self.length: break  # Transfer finished, but not closed by the remote host for some reason or another.
            if self.kill:                           # Received a request for the thread to be killed.
                dispatcher.send('STATE_CHANGE', self, (CANCELLED,))
                dataSocket.close()
                raise AbortDownloadException()

        try:
            dataSocket.close()
        except:
            dispatcher.send('DEBUG', 'downloadThread.FTP', 'Some problems closing data socket...')

        self.realReceived = self.tempFile.tell() # @DEBUG, I presume
        self.tempFile.seek(0)                    
        dispatcher.send('STATE_CHANGE', self, (FINISHED,))
        self.sock.close()
        self.timer.stopTimer()
        self.tempFile.flush()
        print "Received: %d(%d), Written: %d, Should be equal %d.\n" %(self.received, self.realReceived, self.written, self.length)
        