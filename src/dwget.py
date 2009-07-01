# coding=utf8

import sys
import re
from optparse import OptionParser
from socket import *
import os, os.path


def sendAndConfirm (options):
    socketFileName = 'stefan' # nazwa pliku w tempie - check czy w dwgetd/threads.py jest ten sam
    msg = u''
    s = socket(AF_UNIX, SOCK_STREAM) # tutaj bedziemy wysylac polecenia do deamona dwgetd
        
    if not s:
        print 'ERROR - Can\'t open UNIX socket in /tmp'
        s.close()
        sys.exit()
    
    s.connect("/tmp/"+socketFileName)

    if options.ipAdd != None :
        s.send('NEW_SLAVE '+options.ipAdd+'\n')
        print 'trying to add slave with ip: ', options.ipAdd
    elif options.ipDel != None :
        s.send('DEL_SLAVE '+options.ipDel+'\n')
        print 'trying to delete slave with ip: ', options.ipDel
    elif options.address != None :
        s.send('NEW_DOWNLOAD '+opt.address+'\n')
        print 'trying to start the download of: "'+options.address+'"'
    elif options.slaveList == True :
        s.send('LIST_SLAVES dummy_arg'+'\n')
        print 'listing slaves..'
        options.slaveList = False
    elif options.taskList == True :
        s.send('LIST_TASKS dummy_arg'+'\n')
        print 'listing current tasks..'
        options.taskList = False
        
    # czekamy na informacje zwrotna    
    receivedData = ''
    
    while 1:
        data = s.recv(1024)
        receivedData = receivedData + data
        if  data[-1] == '\n' : break
        
    # ładne drukowanie
    receivedData = receivedData.replace('& ', '\n')
    print receivedData.strip()
    
    s.close()

if __name__ == '__main__':
    # obsluga wejscia z konsoli
    parser = OptionParser()
    parser.add_option("-a", dest="ipAdd", help="add IP of a new slave")
    parser.add_option("-d", dest="ipDel", help="delete slave with given IP")
    parser.add_option("-n", dest="address", help="new file to download")
    parser.add_option("-s", dest="slaveList", action="store_true", default=False, help="view the list of slaves")
    parser.add_option("-l", dest="taskList", action="store_true", default=False, help="view the list of current tasks")
    (opt, args) = parser.parse_args()

    ip_pattern = re.compile('^[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}$')
    http_pattern = re.compile(r"""
        ^
        ((ftp|http)s?://)
        ?(([0-9a-zA-Z_!~*'().&=+$%-]+: )?[0-9a-zA-Z_!~*'().&=+$%-]+@)?
        (([0-9]{1,3}\.){3}[0-9]{1,3}
        |
        ([0-9a-zA-Z_!~*'()-]+\.)*
        ([0-9a-zA-Z][0-9a-zA-Z-]{0,61})?[0-9a-zA-Z]\.
        [a-zA-Z]{2,6})
        (:[0-9]{1,4})?
        ((/?)|
        (/[0-9a-zA-Z_!~*'().;?:@&=+$,%#-]+)+/?)$ 
        """, re.VERBOSE)
    
    # czy mamy co parsować?
    if (opt.ipAdd != None) or (opt.ipDel != None) or (opt.address != None) :
        if opt.ipAdd != None :
            if re.match(ip_pattern, opt.ipAdd) != None : # wysyłamy bo dobry
                sendAndConfirm (opt)
                opt.ipAdd = None
            else :
                print 'IPv4 address: "'+opt.ipAdd+'" is incorrect!'
                opt.ipAdd = None 
        if opt.ipDel != None :
            if re.match(ip_pattern, opt.ipDel) != None : # wysyłamy bo dobry
                sendAndConfirm (opt)
                opt.ipDel = None
            else :
                print 'IPv4 address: : "'+opt.ipDel+'" is incorrect!'
                opt.ipDel = None 
        if opt.address != None :
            if re.match(http_pattern, opt.address) != None :
                # print opt.address
                sendAndConfirm (opt)
                opt.address = None
            else :
                print 'http address: "'+opt.address+'" is incorrect!'
                opt.address = None      
    else :
        if (opt.slaveList == True) or (opt.taskList == True) :
            sendAndConfirm (opt) # nie było -a -d -n ale moglo byc -s -l 
        
        sys.exit()