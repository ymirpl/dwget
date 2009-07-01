# coding=utf8
from pydispatch import dispatcher

from common.Logger import Logger
from threading import Thread as th
from dwgetd.threads import *
from dwgetd.Slave import *
from dwgetd.Task import *
from dwgetd.Slavedriver import *
from collections import deque
from common import consts
import socket, sys, time



class TaskAlreadyExists(Exception):
    pass


class Dwgetd(object):
    

    taskList = []
    taskQueue = deque()
    __thread = None 
    __driver = Slavedriver()
    replyMsg = ''
    
    def __init__(self):
        
        # init loggging
        logger = Logger('dwgetd',2001, '127.0.0.1', True)
        logger.addStuff(self.__driver)
    
        dispatcher.connect(self.newSlave, signal = 'NEW_SLAVE', sender = 'masterMainThread')
        dispatcher.connect(self.delSlave, signal = 'DEL_SLAVE', sender = 'masterMainThread')
        dispatcher.connect(self.newDownload, signal = 'NEW_DOWNLOAD', sender = 'masterMainThread')
        dispatcher.connect(self.__reply, signal = 'REPLY_SOCKET', sender = 'masterMainThread')
        dispatcher.connect(self.listSlaves, signal = 'LIST_SLAVES', sender = 'masterMainThread')
        dispatcher.connect(self.listTasks, signal = 'LIST_TASKS', sender = 'masterMainThread')
        self.__thread = MainThread()
        self.__thread.start()
        
    def __reply(self, reply_sock, signal, sender):
        self.replyMsg += '\n'
        sent = 0
        while sent < len(self.replyMsg):
            sent += reply_sock.send(self.replyMsg[sent:])
            
    def newSlave(self, ip, signal, sender):
        
        if not self.__driver.addSlave(ip):
            self.replyMsg = 'Slave: %s added' % (ip)
        else:
            self.replyMsg = 'Slave: %s already exists' % (ip)
            dispatcher.send('ERROR', 'dwgetd', 'Slave: %s already exists' % (ip))
        
        
    def delSlave(self, ip, signal, sender):
        
        if not self.__driver.removeSlave(ip):
            self.replyMsg = 'Slave %s deleted form slave list' % (ip)
        else:
            self.replyMsg = 'No such slave: %s' % (ip)
            dispatcher.send('ERROR', 'dwgetd', 'Can\'t delete: there is no slave with ip: %s' % (ip))
    
    def listSlaves(self, dummyArg):
        
        self.replyMsg = ''
        for slave in self.__driver.listSlaves():
            self.replyMsg += (slave.ip + ' & ')
 
            
    def listTasks(self, dummyArg):
        self.replyMsg = ''
        for task in self.__driver.listTasks():
            self.replyMsg += (task.url + ' & ')

    def __newTask(self, url):
        findList = [task for task in self.taskList if task.url == url]
        if not len(findList):
            try: 
                task = Task(url, self.__driver)
                self.taskList.append(task)
                self.replyMsg = 'Task: %s added' % (url)
            except:
                 # TODO pass exception message (value) in python 2.5
                 print sys.exc_info()
                 print sys.exc_traceback
                 self.replyMsg = 'Task: %s not added, maybe wrong url?' % (url)
                 dispatcher.send('ERROR', 'dwgetd', 'Task: %s' % (url))
                 raise BadConnect
                
        else:
            self.replyMsg = 'Task: %s already exists' % (url)
            dispatcher.send('ERROR', 'dwgetd', 'Task: %s already exists' % (url))
            raise TaskAlreadyExists
        
        
    
    def newDownload(self, url, signal, sender):
        try:
            newTask = self.__newTask(url)
            self.taskQueue.append(newTask)
            #self.slaveList[0].start((-1,0), url, self.taskList[0].file);
            #time.sleep(5)
            #self.slaveList[0].updateReport();
            #time.sleep(10)
            #self.slaveList[0].updateReport();
            #self.slaveList[0].requestBinData();

        except:
            print sys.exc_info()
            print sys.exc_traceback
            dispatcher.send('ERROR', 'dwgetd', 'Problems with new download %s' % (url))

if __name__ == '__main__':

    dwgetd = Dwgetd()

    
    
        