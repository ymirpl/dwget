#!/usr/bin/python
# coding=utf8
from pydispatch import dispatcher
from common.consts import *
from dwgetds.threads import * 
from dwgetds.talkerThread import *   
from dwgetds.slaveMgr import *

import sys
import time

import socket

def main():
    logger = Logger('dwgetds', 2000, '', True)
    slaveMgr = slaveManager()
    logger.addStuff(slaveMgr)
    tThread = talkerThread(slaveMgr, '') 
    tThread.start() 
    dispatcher.send('DEBUG', 'dwgetds', 'Started dwget slave daemon.')
#    dispatcher.send('MASTER_REQUEST', 'test', (NEW_URI, 'http://dfn.dl.sourceforge.net/sourceforge/sevenzip/7z465.exe', 0, 128000))
#    time.sleep(10) For profiling
    
def profile_main():
     import cProfile, pstats
     prof = cProfile.Profile()
     prof = prof.runctx("main()", globals(), locals())
     print "<pre>"
     stats = pstats.Stats(prof)
     stats.sort_stats("time")  # Or cumulative
     stats.print_stats(80)  # 80 = how many to print
     # The rest is optional.
     # stats.print_callees()
     # stats.print_callers()
     print "</pre>"
     dispatcher.send('MASTER_REQUEST', 'test', (KILL,))

if __name__ == '__main__':
    main()
    #http://imagecache.allposters.com/images/pic/VAS/0000-0594-4~Grosser-Preis-von-Deutschland-Posters.jpg # TODO REGEXP NOT PASSING THIS URL
    #http://www.museumofworldwarii.com/Images2005/02DeutschlandErwachelge.gif
#    dispatcher.send('MASTER_REQUEST', 'test', (NEW_URI, 'http://download.living-e.com/MAMP/releases/1.7.2/MAMP_1.7.2.dmg', 0, 1024))
#    time.sleep(4)
#    dispatcher.send('MASTER_REQUEST', 'test', (ABORT,))
#    dispatcher.send('MASTER_REQUEST', 'test', (NEW_URI, 'http://download.living-e.com/MAMP/releases/1.7.2/MAMP_1.7.2.dmg', 0, -1))
#    time.sleep(4)
#    dispatcher.send('MASTER_REQUEST', 'test', (ABORT,))
#    time.sleep(4)
    #dispatcher.send('MASTER_REQUEST', 'test', (NEW_URI, 'http://dfn.dl.sourceforge.net/sourceforge/sevenzip/7z465.exe', 0, 1024))
#    time.sleep(5)
#    dispatcher.send('MASTER_REQUEST', 'test', (KILL,))
#    dispatcher.send('MASTER_REQUEST', 'test', (KILL,))
#    dispatcher.send('MASTER_REQUEST', 'test', (NEW_URI, 'http://dfn.dl.sourceforge.net/sourceforge/sevenzip/7z465.exe', 0, 939956))
#    dispatcher.send('MASTER_REQUEST', 'test', (NEW_URI, 'http://dfn.dl.sourceforge.net/sourceforge/sevenzip/7z465.exe', 0, 939956))
#    dispatcher.send('MASTER_REQUEST', 'test', (NEW_URI, 'http://dfn.dl.sourceforge.net/sourceforge/sevenzip/7z465.exe', 0, 939956))
#    time.sleep(8)
#    dispatcher.send('MASTER_REQUEST', 'test', (NEW_URI, 'http://download.living-e.com/MAMP/releases/1.7.2/MAMP_1.7.2.dmg', 0, 1024))
#    print slaveMgr.getReport()
#    dispatcher.send('MASTER_REQUEST', 'test', (NEW_URI, 'http://dfn.dl.sourceforge.net/sourceforge/sevenzip/7z465.exe', 0, 939956))
#    time.sleep(8)
#    print slaveMgr.getReport()
#    slaveMgr.die()
    