from pydispatch import dispatcher
from collections import deque
from dwgetd.threads import *
from xml.etree import ElementTree as ET
import thread

class Slave():
    '''
    Class representing a single slave used to download a specified file fragment. 
    It stores deataled key information about every slave, such as: 
        * ip address of a slave 
        * state of a slave 
        * url of a file 
        * object representing file fragment @see fileFragment.py 
        * status of a slave 
        * average downloading speed of a file fragment  
        * current downloading speed of a file fragment  
        * rating of a slave 
    '''
    ip = ''
    isActive = False
    isDead = False
    url = ''
    chunk = () # tuple containing length and offset (-1 for max length)
    status = 0
    received = 0
    avgSpeed = 0.0
    currentSpeed = 0.0
    rating = 0.0 # rating based on reports 
    rThread = None
    monitor = False
    lock = None
    
    
    slaveTalk = None
    __receivedData = '' # data received in slave Talk
    __orderQueue = deque()
    parseFunc = None # function handle to parse incoming data
    binFilename = None
    fileFragment = None
    
    def setFileFragment(self, fileFragment):
        self.binFilename = fileFragment.getFileFragment()
        self.fileFragment = fileFragment
        self.fileFragment.ip = self.ip
    
    def __init__(self, ip,driver, fileFragment = None):
        print "INIT"
        self.driver = driver
        self.__orderQueue = deque()
        self.ip = ip
        if fileFragment:
            self.fileFragment = fileFragment
            self.binFilename = fileFragment.getFileFragment()
        self.rThread = None
        self.lock=thread.allocate_lock()
        self.aborting = False
        print self.lock
        dispatcher.send('DEBUG', 'slaveObject', '__init__')
        dispatcher.connect(self.doOrder, signal = 'SLAVE_PARSE_QUEUE', sender = self)
        dispatcher.connect(self.parseSlaveReport, signal = 'PARSE_REPORT', sender = self)
        dispatcher.connect(self.binData, signal = 'PARSE_BINDATA', sender = self)   
        dispatcher.connect(self.dummyF, signal = 'DUMMY_FUNC', sender = self)       
       
    def getLock(self, string = ''):
        #print "Trying to get lock in %s, %s." % (string, self)
        res = self.lock.acquire(0)
#        if res:
#            print "Got lock."
#        else:
#            print "Locked."
        return res
    
    def releaseLock(self):
        #print "Releasing lock"
        return self.lock.release()
       
    def chatFinished(self, receivedData = 'dummyMsg'):
        """
        receivedData is slaves response, not used here
        """
        #self.receivedData = receivedData
        if receivedData[0] != '<' and self.parseFunc != 'PARSE_BINDATA':
            pass
        #print self, self.parseFunc, '\n', receivedData
        if self.slaveTalk.file_fragment_done:
            print self.fileFragment.offset, " done."
            self.fileFragment.setDone()
        #print self
        dispatcher.send(self.parseFunc, self, receivedData)
    
    def markAsProbablyDead(self):
        self.isDead = True  
        print "DEAD", self
        if self.rThread:
            self.rThread.alive = False
        self.__orderQueue.clear()
        dispatcher.send('SLAVE_DEAD', 'slaveObject', self)
                
    def doOrder(self, arg, signal, sender):
        """
        Simple monitor-like behaviour
        """
        #print "DOORDER"

        #print "KOLEJA!!!!"
        #print  len(self.__orderQueue)
        
        #print '!! jam dooooorder'
        #print self.binFilename
        
        binFilename = None # default behaviour
        
        while not self.lock:
            pass
            
        if len(self.__orderQueue) > 0 and self.slaveTalk == None:
            debugstr = self.__orderQueue[0][1]
            if self.getLock(debugstr) and len(self.__orderQueue) > 0 and self.slaveTalk == None: 
                #self.__orderQueue[0][2] = True
                #if (self.__orderQueue[0][2] != self):
                 #   print "That's not gone well... :("
                   # self.releaseLock()
                    #time.sleep(0.1)
                   # return
                (slaveData, self.parseFunc, activity) = self.__orderQueue[0]  # tuple in queue, order and proper parse fucntion
                
                if self.parseFunc == 'PARSE_BINDATA':
                    binFilename = self.binFilename
                    
                #print self, slaveData
                    
                self.slaveTalk = SlaveThread(self, self.ip, binFilename)
                self.slaveTalk.data = slaveData
                self.slaveTalk.data += '\n'
                self.slaveTalk.start()

         
        return     
        
    def updateReport(self):
        orderElement = ET.Element("Order")
        orderElement.attrib["type"] = "report"
        xmlFile = ET.tostring(orderElement, 'utf-8')
        dispatcher.send('DEBUG', 'slaveObject', xmlFile)
        
        for i in self.__orderQueue:
            if i[1] == 'PARSE_REPORT' and i[2] == self:
                return

        #print "REPORT requested",self
        self.__orderQueue.append([xmlFile, 'PARSE_REPORT', self])
        dispatcher.send('SLAVE_PARSE_QUEUE', self, '')

    def abort(self):
        orderElement = ET.Element("Order")
        orderElement.attrib["type"] = "abort"
        xmlFile = ET.tostring(orderElement, 'utf-8')
        dispatcher.send('DEBUG', 'slaveObject', xmlFile)
        self.aborting = True
        print "ABORT requested",self
        self.__orderQueue.append([xmlFile, 'DUMMY_F', self])
        dispatcher.send('SLAVE_PARSE_QUEUE', self, '')



    def parseSlaveReport(self, arg, signal, sender):
        '''
        Param: chunk[lenght, start], server w/o resume, set file length to -1 
        '''
         # parse report sent by slave here into slave class variables
       # print self, "parse report"
       
        if self.isDead == True:
            return
       
        report = ET.XML(arg)

        self.status = int(report.find("status").text)
        #print "GOT REPORT", self.status, self 
        self.received = int(report.find("received").text)
        self.avgSpeed = float(report.find("avgSpeed").text)
        self.currentSpeed = float(report.find("currentSpeed").text)

        self.__orderQueue.popleft()
        self.slaveTalk = None
#        self.__orderQueue.popleft()    
        try:
            self.releaseLock()
        except:
            #print "No lock, actually."
            pass   
        dispatcher.send('SLAVE_PARSE_QUEUE', self, '')
        
        # request binData if file completed on slave 
        if self.status == 6 and self.isActive:
            self.rThread.alive = False
            #print "RTHREAD OFF", self
            for i in self.__orderQueue:
                if i[1] == 'PARSE_REPORT' and i[2] == self:
                    self.__orderQueue.remove(i)
            print self.ip, "REQUESTING UPLOAD"
            self.requestBinData()
        
    def start(self, chunk, url, file):

        self.chunk = chunk
        self.url = url
        self.file = file[file.rindex('/')+1:]
        
        # generate proper xml file 
        
        orderElement = ET.Element("order")
        orderElement.attrib["type"] = "start"
        urlElement = ET.SubElement(orderElement, "url")
        
        sizeElement = ET.SubElement(orderElement, 'length').text = repr(chunk[0])
        startElement = ET.SubElement(orderElement, 'start').text = repr(chunk[1])
        
        urlElement.text = (self.url)
           
        xmlFile = ET.tostring(orderElement, 'utf-8')
        dispatcher.send('DEBUG', 'slaveObject', xmlFile)

        self.__orderQueue.append([xmlFile, 'DUMMY_FUNC', self])
        self.isActive = True
        dispatcher.send('SLAVE_PARSE_QUEUE', self, '')

        if not self.rThread:
            self.rThread = ReportingThread(self) 
            self.rThread.start()
        self.rThread.alive = True
        
        #print "RTHREAD ON", self
    
    
    def dummyF(self, arg, signal, sender):
        """
        Dummy fucntion passed as parseFunc, if no response reaction is needed
        Unlocks thread for next conversations
        """
        
        if self.isDead == True:
            return
        
        
        #print "DUMMY"
        if self.aborting:
            self.aborting = False
            self.isActive = False
        self.__orderQueue.popleft()
        del self.slaveTalk
        self.slaveTalk = None
#        self.__orderQueue.popleft()
        try:
            self.releaseLock()
        except:
            pass
            #print "No lock, actually."    
        dispatcher.send('SLAVE_PARSE_QUEUE', self, '')
   
#    def stop(self):
#        orderElement = ET.Element("Order")
#        orderElement.attrib["type"] = "abort"
#        xmlFile = ET.tostring(orderElement, 'utf-8')
#        dispatcher.send('DEBUG', 'slaveObject', xmlFile)
#        
#        self.__orderQueue.append([xmlFile, dummyF, False])
#        self.doOrder()
        
    def requestBinData(self):
              
        #print "UPLOAD ", self
        #print self.status 
              
        orderElement = ET.Element("Order")
        orderElement.attrib["type"] = "upload"
        xmlFile = ET.tostring(orderElement, 'utf-8')
        dispatcher.send('DEBUG', 'slaveObject', xmlFile)
        
        self.__orderQueue.append((xmlFile, 'PARSE_BINDATA', self))
        dispatcher.send('SLAVE_PARSE_QUEUE', self, '')
        
    def binData(self, arg, signal, sender):
        
        if self.isDead == True:
            return
        
        self.isActive = False
        if self.slaveTalk.downloaded == self.chunk[0]:
            self.__orderQueue.popleft()
            dispatcher.send('TASK_COMPLETE', 'slaveObject', 'dummyMsg')
            dispatcher.send('DONE_CHUNK', 'slaveObject', self.fileFragment)
            self.driver.removeDuplicates(self.fileFragment, self.ip)
            print self.ip, "UPLOAD COMPLETED"
        else:
            print self.ip, "RETRYING UPLOAD"
        del self.slaveTalk
        self.slaveTalk = None
#        self.__orderQueue.popleft()
        try:
            self.releaseLock()
        except:
            #print "No lock, actually."
            pass   
        dispatcher.send('SLAVE_PARSE_QUEUE', self, '')
        
        
        
        
        