from django.db import connection
from django.template import Context, loader
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render_to_response
from socket import * 
from math import floor
import sys

from xml.etree import ElementTree as ET
from xml.etree.ElementTree import *

from consts import *

def commit(cursor):
    try:
        cursor.execute("COMMIT;")
    except:
        pass

def ipFormatChk(ip_str):
    
     if len(ip_str) < 7:
         return False
    
     ipList = ip_str.split('.')

     print ipList

     if len(ipList) == 4:
         for i, item in enumerate(ipList):
             try:
                 ipList[i] = int(item)
             except:
                 print 'b'
                 return False
             if not isinstance(ipList[i], int):
                 print 'c'
                 return False
         if max(ipList) < 256:
             return True
         else:
             print 'd'
             return False
     else:
         print 'e'
         return False
    
def getLog(IP, port):
    sock = socket(AF_INET, SOCK_STREAM) 
    sock.settimeout(3)
    
    response = ""
    
    try:
        sock.connect((IP, port))
        while 1:
            data = sock.recv(65536)
            response += data
            if data[-1] == '\n': break
        sock.close()
    except:
        print sys.exc_info()
        return "Failed to connect."
    
    return response
    
def index(request):
    cursor = connection.cursor()
    cursor.execute("SELECT * from Hosts;")
    response = cursor.fetchall()
    log = []
    XML = []
    t = []
    s = []
    
    for machine in response:
        l = getLog(machine[0], int(machine[1]))
#        log.append((machine, l))
        
        try:
            xml = ET.XML(l)
            
            if xml.tag == 'DWGETD':
                tasks = xml.find('TASKS')
                for task in tasks:
                    element = [task.find('url').text, int(task.find('size').text), int(task.find('status').text)]
                    chunks = task.find('CHUNKS')
                    c = []
                    for chunk in chunks:
                        element2 = [chunk.find('ip').text, int(chunk.find('offset').text), int(chunk.find('length').text), int(chunk.find('done').text)]
                        c.append(element2)
                    element.append(c)
                    t.append(element)
            elif xml.tag == 'Report':
                element = [machine[0], xml.find('url').text, int(xml.find('status').text), int(xml.find('received').text), float(xml.find('currentSpeed').text), float(xml.find('avgSpeed').text)]
                s.append(element)
        except:
            pass
    
    for task in t:
        dl = 0
        if len(task) >= 4:
            for chunk in task[3]:
                if chunk[3]:
                    dl += chunk[2]+1
                for slave in s:
                    if not chunk[3] and chunk[0] == slave[0] and task[0] == slave[1]:
                        dl += slave[3]
                        chunk.append(slave)
        task.append(sizeof_fmt(dl))
        task.append(floor(100.*dl/task[1]))
        print ((task[0], dl), "%d"%floor(100.*dl/task[1]))
        log.append(((task[0], dl), "%d"%floor(100.*dl/task[1])))
    for task in t:
        print 'TASK:'
        print task[0:2]
        print len(task)
        if len(task) > 4:
            print task[4:len(task)]
        if len(task) >= 4:
            print 'Chunks:'
            start = [0, False]
            for chunk in task[3]:
                if not chunk[3] and not start[1]:
                    print '\t', chunk
                elif not chunk[3] and start[1]:
                    print start[0], '-', chunk[1]-1, ' done.'
                    print '\t', chunk
                    start[1] = False
                elif chunk[3] and start[1]:
                    pass
                else:
                    start = [chunk[1], True] 
                    
                pass
        task[1] = sizeof_fmt(task[1])
        task.append(2 * task[5]) # in task.6 progressBar
        
        
        if type(slave[3]) == type(int()):
            for slave in s:
                slave[3] = sizeof_fmt(slave[3]) 
                slave[4] = sizeof_fmt(slave[4])
                slave[5] = sizeof_fmt(slave[5])
            
        
    return render_to_response("index.html", {'logs': log, 'tasks': t, 'slaves': s})

def listQueried(request):    
    cursor = connection.cursor()
    cursor.execute("SELECT * from Hosts;")
    response = cursor.fetchall()

    return render_to_response('hosts_list.html', {
            'hosts': response,
    })
    
def listAdd(request):
    if not request.POST or 'ip' not in request.POST:
        return HttpResponse("Failed.")
    
    IP = request.POST['ip']
    port = request.POST['port']
    print ipFormatChk(IP)

    if not ipFormatChk(IP):
        return HttpResponse("Failed.")        

    try:
        port = int(port)
    except:
        return HttpResponse("Failed.")
    
    cursor = connection.cursor()
    cursor.execute("INSERT INTO Hosts VALUES(%s, %s);", [IP, port])
    commit(cursor)
    
    return HttpResponseRedirect("/manage/list")

def sizeof_fmt(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.1f%s" % (num, x)
        num /= 1024.0


    
def listRemove(request, IP, port):
#    cursor = connection.cursor()
#    cursor.execute("SELECT * from Hosts WHERE IP=%s AND port=%s;", [IP, port])
#    response = cursor.fetchall()
#    print len(response)
#    if not response:
#        return HttpResponse("Not found.")

    cursor = connection.cursor()
    cursor.execute("DELETE from Hosts WHERE IP=%s AND port=%s;", [IP, port])

    commit(cursor)
        
    return HttpResponseRedirect("/manage/list")
