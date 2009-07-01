'''
Created on 2009-05-28

@author: wimi
'''
from tempfile import NamedTemporaryFile 
from common.consts import * 
from common.Logger import Logger 
from pydispatch import dispatcher 

class fileFragment(): 
    '''
    Class representing single fragment of a file being currently downloded. 
    It is used to store needed information about the file frament: 
        * length of the fragment 
        * position of the fragment in the original file 
        * file handle in local filesystem 
        * ip of the slave which is downloading the fragment 
        * information whether all data in the fragment has been downloaded 
    '''
    offset = -1 
    length = -1 
    file = None  
    ip = ''
    done = 0 # status 

    def __init__(self, offset, length = -1, ip = ''): 
        '''
        Constructor
        '''
        self.offset = offset 
        self.length = length 
        self.ip = ip
        
        self.file = NamedTemporaryFile(suffix = '.dwgetds') 
        dispatcher.send('DEBUG', 'fileFragment', 'fileFragment created...') 
        dispatcher.send('DEBUG', 'fileFragment', 'Created file %s...' % (self.file.name)) 
        self.done = FF_NEW
        
    def getFileFragment(self): 
        return self.file 
    
    def setDone(self):
        self.done = FF_DONE

    def setRetry(self):
        self.done = FF_ERROR
        
    def isToBeDownloaded(self):
        return (self.done == FF_ERROR)