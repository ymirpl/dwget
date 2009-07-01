'''
Created on May 28, 2009

@author: tk
'''
# coding=utf8
from common.consts import *
from dwgetd.Slave import *
from pydispatch import dispatcher
from math import floor
import thread

from xml.etree import ElementTree as ET
from xml.etree.ElementTree import *

class Slavedriver():
    '''
    Class which task is managing all of the slaves that are assigned to the master.
    It handles the global slave list and it adds new slaves, removes slaves,
    controls the slaves that has been disconnected or have been timeouted.
    It checks whether the slaves are still connected. It counts the slave downloading
    rates.
    '''
    __slaveList = []
    __taskList = []
    __lock = None

    def getLock(self):
        res = self.__lock.acquire(1)
        return res
    
    def releaseLock(self):
        return self.__lock.release()

    def __init__(self):
        self.__lock=thread.allocate_lock()
        dispatcher.connect(self.parseRequest, signal = 'TASK_REQUEST', sender = dispatcher.Any)
        dispatcher.connect(self.fragmentCompleted, signal = 'TASK_COMPLETE', sender = dispatcher.Any)
        dispatcher.connect(self.removeDeadSlave, signal='SLAVE_DEAD', sender = dispatcher.Any)
        #dispatcher.connect(self.removeDuplicates, signal='DONE_CHUNK', sender = dispatcher.Any)

    def removeDeadSlave(self, arg, signal, sender):
        self.removeSlave(arg.ip)
        self.doVoodoo() 
        
    def removeDuplicates(self, arg, ip):
        for slave in self.__slaveList:
            if slave.fileFragment == arg:
                if slave.isActive and slave.ip != ip:
                    print "FOUND DUPLICATED CHUNK TO ABORT ", slave.ip , slave.isActive
                    print arg.offset
                    print slave.fileFragment.offset
                    slave.abort()
                    self.doVoodoo()
        
    def addSlave(self, ip):
        # @TODO should doVoodoo.
        findList = [slave for slave in self.__slaveList if slave.ip == ip]
        if not len(findList):
            self.__slaveList.append(Slave(ip, self))
            self.doVoodoo()
            return 0
        else:
            dispatcher.send('ERROR', 'dwgetd', 'Slave: %s already exists' % (ip))
            return -1
            
    def removeSlave(self, ip):
        toDelList = [slave for slave in self.__slaveList if slave.ip == ip]
        for slave in self.__slaveList: 
            print slave.ip
        if len(toDelList):
            # @TODO: dispatch slaves task to other slaves.
            print "!!!!!!!!!!!!!!!!!!!!!!!"
            print "!!!!!!!!!!!!!!!!!!!!!!!"
            print toDelList[0].ip 
            print ip 
            print "!!!!!!!!!!!!!!!!!!!!!!!"
            print "!!!!!!!!!!!!!!!!!!!!!!!"
            print toDelList[0] in self.__slaveList 
            self.__slaveList.remove(toDelList[0])
            print "Po usunieciu: "
            for slave in self.__slaveList: 
                print slave.ip 
            return 0
        else:
            dispatcher.send('ERROR', 'dwgetd', 'Can\'t delete: there is no slave with ip: %s' % (ip))
            return -1

    def listSlaves(self):
        return self.__slaveList

    def listTasks(self):
        return self.__taskList
    
    def parseRequest(self, arg, signal, sender):
        if arg == NEW_TASK:
            self.newTask(sender)
        else:
            dispatcher.send('ERROR', 'slavedriver', 'Unknown request.')

    def rateSpeed(self): 
        #print "Oceny dla slave'ow:" 
        for i in self.__slaveList: 
            #print "average speed: &f" %i.avgSpeed 
            slavesCnt = 0 
            avgSpeed = 0 
            #i.rating = 0.0 
            for j in self.__slaveList: 
                if i.url == j.url: 
                    #i.rating += j.avgSpeed 
                    slavesCnt += 1 
                    avgSpeed += j.avgSpeed
            if slavesCnt > 0 and avgSpeed > 0: 
                i.rating = i.avgSpeed / (avgSpeed / slavesCnt) 
            else:
                i.rating = 1.
            #print i.url + " %f" %i.rating 
        #print "Koniec ocen dla slave'ow..." 

    def newTask(self, task):
        # @TODO: remove duplicates
        # @TODO: start task
        dispatcher.send('DEBUG', 'slavedriver', 'New task started.')
        self.__taskList.append(task)
        self.doVoodoo()

    def fragmentCompleted(self, arg, signal, sender):
        self.doVoodoo()
        
    def taskCompleted(self, task):
        task.status = TASK_FINISHED
        #self.__taskList.remove(task)
    
    def doVoodoo(self):
                
        while not self.__lock: # waiting for lock initialization
            pass
        
        #print "RECALCULATING ENVIRONMENT"
        self.getLock()
        
        self.rateSpeed()
        
        for task in self.__taskList: 
            if task.status > 1: 
                continue 
            for chunk in task.fileFragments:
                if chunk.done != 0: continue # don't waste time on not-being-downloaded chunks 
                ip = chunk.ip
                if len([slave for slave in self.__slaveList if slave.ip == ip]) == 0 : # using dead slave
                    print task.url, chunk.ip, chunk.offset, "FAILED"
                    chunk.setRetry()
            
        for slave in self.__slaveList:
            if not slave.isActive and not slave.isDead:
                for task in self.__taskList:
                    if task.status > 1:             # Don't waste time thinking about a completed task.
                        continue
                    if task.fileFragments:          # Any to be retried after slave failure?
                        for chunk in task.fileFragments:
                            if chunk.isToBeDownloaded():    # == FF_ERROR || FF_NEW
                                print task.url, slave.ip, chunk.offset, " IS BEING DOWNLOADED"
                                slave.setFileFragment(chunk)
                                slave.start((chunk.length+1, chunk.offset-1), task.url, task.file)
                                chunk.ip = slave.ip
                                
                                # @TODO: self.doVoodoo() if it starts locking.
                                self.releaseLock()
                                self.doVoodoo()
                                return

                    offset = 0
                    if task.fileFragments:
                        for chunk in task.fileFragments:
                            offset = max(offset, chunk.offset+chunk.length) # Last chunks offset.
                            
                    if (offset+1) < task.size:                              # If last chunk happens to be outside the file.
                        print task.url, task.supportsResume
                        if task.supportsResume:
                            chunk = task.addFileFragment(offset+1, min(max(int(floor(slave.rating*basePartSize)), minPartSize), task.size-offset-1), slave.ip)
                            print task.url, slave.ip, chunk.offset,  chunk.length, " IS BEING DOWNLOADED"
                            slave.setFileFragment(chunk)
                            slave.start((chunk.length+1, chunk.offset-1), task.url, task.file)
                        else:
                            slave.setFileFragment(task.addFileFragment(0, task.size, slave.ip))
                            slave.start((task.size, 0), task.url, task.file)
                            print task.url, slave.ip, chunk.offset, " IS BEING DOWNLOADED"
                            
                        self.releaseLock()
                        self.doVoodoo()
                        return
                        #continue
                    else:
                        allDone = True
                        if task.fileFragments:
                            print task.url, task.size
                            for chunk in task.fileFragments:
                                if not chunk.done:
                                    allDone = False
                                print chunk.offset, chunk.done

                        if allDone and (task.status != TASK_MERGING):
                            # @TODO in a different thread!
                            task.mergeFile()
                            continue
                        #sys.exit(0)
               # slave.start(())
               
               # If we're here, we don't have anything to do. Can't let that happen, can we...
               # 
               
#                ratingToBeat = slave.rating
#                worstTask = None
#                worstChunk = None
#                worstRank = 0               
#                for task in self.__taskList:
#                    if task.status > 1:             # Don't waste time thinking about a completed task.
#                        continue
#                    if task.fileFragments:          # Any to be retried after slave failure?
#                        for chunk in task.fileFragments:
#                            if chunk.done != 0:
#                                continue
#                            
#                            remaining = 0
#                            avgSpeed = 0
#                            rating = 0
#                            
#                            for slave in self.__slaveList:
#                                if chunk.ip == slave.ip:
#                                    remaining = chunk.length - slave.received  
#                                    avgSpeed = slave.avgSpeed
#                                    rating = slave.rating
#                                    
#                            rank = remaining*avgSpeed*rating
#                            
#                            if rank > worstRank:
#                                worstRank = rank
#                                worstTask = task
#                                worstChunk = chunk
#                    
#                    print task.url, slave.ip, chunk.offset,  chunk.length, "IS BEING DUPLICATED (TAKEN OVER FROM", chunk.ip, ")."
#                    slave.setFileFragment(chunk)
#                    slave.start((chunk.length+1, chunk.offset-1), task.url, task.file)
#               
        self.releaseLock()
        
    def generateXML(self):
        '''
        Method generates the XML report of everything for Django frontend.        
        
        @return ready XML string
        '''
        
        doc = Element("DWGETD")
        tasks = SubElement(doc, 'TASKS')
        for tsk in self.__taskList:
            task = SubElement(tasks, 'TASK')
            SubElement(task, u'url').text = '%s' % (tsk.url)
            SubElement(task, u'size').text = '%d' % (tsk.size)
            SubElement(task, u'status').text = '%d' % (tsk.status)            
            if tsk.fileFragments:
                chunks = SubElement(task,'CHUNKS')
                for chnk in tsk.fileFragments:
                    chunk = SubElement(chunks,'CHUNK')
                    SubElement(chunk, u'offset').text = '%d' % (chnk.offset)
                    SubElement(chunk, u'length').text = '%d' % (chnk.length)
                    SubElement(chunk, u'ip').text = '%s' % (chnk.ip)
                    SubElement(chunk, u'done').text = '%d' % (chnk.done)
        
        return ET.tostring(doc, 'utf-8')
        