from pydispatch import dispatcher

def ftpGetLine(sock):
    #response = [<thereIsNoMoreToCome, <code>]
    msg = ''
    data = ' '
    while data[-1] != '\n':
        data = sock.recv(1)
        msg += data
    
    if len(msg) < 4:
        raise IncorrectFTPResponse()
    
    if msg[3] == ' ':
        return True, int(msg[0:3]), msg[4:]
    else:
        return False, int(msg[0:3]), msg[4:]

def getLastCode(sock):
    serverFinished = False
    while not serverFinished:
        serverFinished, code, msg = ftpGetLine(sock)
        dispatcher.send('DEBUG', 'downloadThread.FTP', 'Got code %d.' % (code))  
    return code, msg

def sendMessage(sock, msg):
    sent = 0
    while sent < len(msg):
        sent += sock.send(msg[sent:])