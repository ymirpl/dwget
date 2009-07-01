            
def parseHeaders(msg):
    """
    Splits received headers into a pretty dictionary.
    
    Returns response code and headers dictionary.
    """        
    header = msg[:msg.find('\r\n\r\n')]  # Two CR-LF mean the start of file.
    header = header.split('\r\n')        # Single CR-LF separate headers
    headers = dict()
    
    code = header[0][header[0].find(' ')+1:header[0].find(' ')+4] # Get response code.
    
    for i in xrange(1, len(header)):    # Put headers into a pretty dictionary
        header[i] = header[i].lower()
        hdr = header[i].split(": ")
        headers[hdr[0]] = hdr[1]
    
    return code, headers
