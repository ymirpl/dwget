from pydispatch import dispatcher 
from common import http
from dwgetd.threads import *
import socket
from common.consts import * 
from dwgetd.fileFragment import * 
from common.ftp import *

'''
Created on 2009-05-20

@author: ymir
'''


# TODO pass error message (value)
class BadConnect(Exception):
    '''
    Class representing exception thrown in several situation such as: 
    - there are problems with connection to the server which stores a file
    - if the file requested by the user does not exist on given server 
    '''
    def __init__(self, msg):
        self.value = msg;
    def __repr__(self):
        return self.value

class Task(object):
    '''
    Class representing a file to be downloaded. 
    It stores a list of slaves that are assigned to the task. 
    Every slave is only responsible for a part of a file specified in a task. 
    A part can also be a whole file if a server hosting the file does not support resuming.  
    The class contains information such as: 
        * url of the file to be downloaded 
        * handle to file in the local filesystem 
        * size of the file 
        * handles to every fragment of a downloaded file 
        * status of a task
    '''
    
    url = ''
    file = '' # filename got from url
    size = 0
    supportsResume = True 
    fileFragments = [] 
    status = -1 
    slaveDrv = None

    def __init__(self, url, slaveDrv):
        '''
        Constructor
        '''
        self.url = url 
        self.slaveDrv = slaveDrv
        self.status = TASK_NEW 
        self.fileFragments = []
        self.supportsResume=True
        self.size = 0
        self.file = ''
        try:
            self.checkHttpServer() 
            dispatcher.send('TASK_REQUEST', self, (NEW_TASK))
        except:
             print sys.exc_info()
             dispatcher.send('TASK_FAILED', self, (NEW_TASK))
             raise BadConnect
              
    def checkHTTP(self, sock, port): 
        host = self.url[self.url.find('//') + 2 : ] 
        self.file = host[host.find('/') : ]
        host = host[ : host.find('/')]
               
        message = u'GET %s HTTP/1.1\r\nHost: %s:%d\r\nRange:bytes=%d-%d\r\n\r\n' % (self.file, host, port, 0, 1024)
        
        try:
            sock.connect((host, port))
        except:
             dispatcher.send('ERROR', 'TaskClass.chceckHttpServer', 'Unable to connect, check url?')
             raise BadConnect('Can\'t connect to %s' % host)
        sent = 0
        while sent < len(message):
            sent += sock.send(message[sent:])
        
               
        httpHeader = ''
        while True:
            data = sock.recv(512)
            httpHeader = httpHeader + data
            if httpHeader.find('\r\n\r\n') is not -1: break
            
            
        code, headers = http.parseHeaders(httpHeader)
        
        if int(code) != 206:           # clue of this too long method
            self.supportsResume = False
            dispatcher.send('DEBUG', 'TaskClass', 'Server not supporting resume')
        if int(code) == 404 or int(code) == 302:           
            dispatcher.send('ERROR', 'TaskClass', 'Error 404')
            raise BadConnect('404')
        
            
        
               
        sock.close()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        try:
            sock.connect((host, port))
        except:
             dispatcher.send('ERROR', 'TaskClass.chceckHttpServer', 'Unable to connect, check url?')
             raise BadConnect('Can\'t connect to %s' % host)

        # TODO, might be more elegant maybe?    
        message = u'GET %s HTTP/1.1\r\nHost: %s:%d\r\n\r\n' % (self.file, host, port)
        sent = 0
        while sent < len(message):
            sent += sock.send(message[sent:])

        httpHeader = ''
        while True:
            data = sock.recv(512)
            httpHeader = httpHeader + data
            if httpHeader.find('\r\n\r\n') is not -1: break
        
        code, headers = http.parseHeaders(httpHeader)
        print code,headers
       
        self.size = int(headers['content-length']) 
        sock.close()
        
    def checkFTP(self,sock,port):
        host = self.url[self.url.find('//') + 2 : ] 
        self.file = host[host.find('/') : ]
        host = host[ : host.find('/')]
        
        try:
            sock.connect((host, port))
        except:
             dispatcher.send('ERROR', 'TaskClass.chceckHttpServer', 'Unable to connect, check url?')
             raise BadConnect('Can\'t connect to %s' % host)
                 
        if getLastCode(sock)[0] != 220:
            raise BadConnect('666')
        
        # Anonymous login
        sendMessage(sock, "USER anonymous\n")
        lastCode, msg = getLastCode(sock)
        if lastCode == 331:
            sendMessage(sock, "PASS dwget@dwget.pl")
            lastCode, msg = getLastCode(sock) 
        if lastCode != 230:
            raise BadConnect('%d'%(lastCode))

        # Find the proper file
        sendMessage(sock, "SIZE %s\n"%(self.file[1:]))
        code, msg = getLastCode(sock) 
        if code != 213:
            raise BadConnect('666')
        self.size = int(msg)
        sendMessage(sock, "REST 0\n")
        if getLastCode(sock)[0] == 350:
            self.supportsResume = True
        else:
            self.supportsResume = False
        
        print self.size, self.supportsResume
        
        sock.close()
        return
        
    def checkHttpServer(self):
        '''
        Checking whether server supports resume
        '''
  
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        sock.settimeout(30)
        if sock : 
            dispatcher.send('DEBUG', 'TaskClass', 'Socket creation succeded...') 
        else :
            dispatcher.send('ERROR', 'TaskClass', 'Socket creation failed...')  
        
        protocol = self.url[:self.url.find(':')]  
        if protocol == 'http' : 
            port = 80   
            self.checkHTTP(sock,port)            
        elif protocol == 'ftp' : 
            port = 21
            self.checkFTP(sock,port)            
        else : 
            dispatcher.send('ERROR', 'TaskClass', 'Unkown protocol...')
            dispatcher.send('STATE_CHANGE', self, (FAILED, UNKNOWN_PROTOCOL))
            return
        

        
    def start(self):
        pass
            
    def addFileFragment(self, offset, length = -1, ip = ''): 
        newFileFragment = fileFragment(offset, length, ip)
        self.fileFragments.append(newFileFragment) 
        return newFileFragment 
    
    def getState(self): 
        return self.status 
    
    def mergeFile(self): 
        self.status = TASK_MERGING
        mergingThread(self).start()
            
            
class mergingThread(Thread):
    def __init__(self, task):
        Thread.__init__(self)
        self.setDaemon(True)
        self.task = task
        
    def run(self):
        print "MERGING ", self.task.file
        completeFile = file(self.task.file[self.task.file.rfind('/')+1:len(self.task.file)], 'wb') 
        for i in self.task.fileFragments: 
            frag = i.getFileFragment()
            try:
                frag.seek(0)
            except:
                print "Error in: ", frag.name 
            while True: 
                data = frag.read(65536) 
                if not data: 
                    break 
                completeFile.write(data) 
            frag.close() 
        completeFile.close()
        print "MERGING DONE"
        self.task.slaveDrv.taskCompleted(self.task)       