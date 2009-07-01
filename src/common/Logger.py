# coding=utf8
from pydispatch import dispatcher

import sys
from time import gmtime, strftime
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import *
from socket import * 
from threading import Thread 

class LoggerThread(Thread): 
    sock = None
    logger = None 
    interface = ''
    port = 2000

    def initSocket(self): 
        self.sock = socket(AF_INET, SOCK_STREAM) 
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, True)  
        self.sock.bind((self.interface, self.port)) 
        self.sock.listen(5)
        
    def waitForConnection(self): 
        self.client, self.address = self.sock.accept() 
        
    def __init__(self, logger, interface,  port): 
        Thread.__init__(self) 
        self.interface = interface
        self.port = port
        self.logger = logger
    
    def run(self): 
        self.initSocket()
        while True :             
            self.waitForConnection()
            
            msg = self.logger.generateWWWXML()
            sent = 0
            while sent < len(msg) : 
                sent += self.client.send(msg[sent:])            
            self.client.send('\n')
            
            self.client.close() 
        self.sock.close()

class Logger():
    ___signal = []
    ___sender = []
    ___arg = []
    ___time = []
    __name = ''
    stuffs = []
    printLog = False
    
    def __init__( self, name = "set_log_name", port=2000, interface = '', printLog = True):
        self.__name = name
        self.printLog = printLog
        LoggerThread(self, interface, port).start()
        dispatcher.connect(self.__log, signal = dispatcher.Any, sender = dispatcher.Any)
        
    def __log(self, arg, signal, sender): 
        if signal == "CHAT_FINISHED": return
        self.___signal.append(repr(signal))
        self.___sender.append(repr(sender))
        self.___arg.append(repr(arg))
        self.___time.append(strftime("%a, %d %b %Y %H:%M:%S", gmtime()))
        if self.printLog:
            print strftime("%a, %d %b %Y %H:%M:%S", gmtime()) + u' Logged: '+ repr(signal) + repr(sender) + repr(arg)
    
    def addStuff(self, stuff):
        self.stuffs.append(stuff)
    
    def generateWWWXML(self):
        msg = ''
        for i in self.stuffs:
            msg = msg + i.generateXML()
            
        return msg
    
    def generateXML(self):
        doc = Element("Log")
        
        for i in xrange(len(self.___signal)):
            SubElement(doc, u'Entry%d' % (i), id=u'%d'%(i), signal=self.___signal[i], sender=self.___sender[i], time=self.___time[i]).text = self.___arg[i]        
        
        return doc
        
    def writeLogFile(self):
        try:
            ElementTree(self.generateXML()).write("%s.xml" % (self.__name))
        except:
            print "[FATAL]: Cannot write the log file."
            print sys.exc_info()