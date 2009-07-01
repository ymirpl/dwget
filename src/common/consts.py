basePartSize = 1*1024*1024
minPartSize  = 3*128*1024
# NEW_STATE (dlThread <--> slaveMgr)
JUST_STARTED        = 0
ALLOCATING          = 1
CONNECTING          = 2
DOWNLOADING         = 3
CANCELLING          = 4
CANCELLED           = 5
FINISHED            = 6
CONNECTING_RETRYING = 7
DOWNLOADING_RETRYING= 8
FAILED              = 9
FINISHED_WRITTEN    = 10

string_states       = ['Just started', 'Allocating', 'Connecting', 'Downloading',
                       'Cancelling', 'Cancelled', 'Finished', 'Connecting - trying again',
                       'Downloading - trying again', 'FAILED']

# FAILED reasons
UNKNOWN_PROTOCOL             = 0
BAD_PORT                     = 1
SCRAMBLED_RESPONSE_CODE      = 2
WRONG_RESPONSE_CODE          = 3
ALLOCATION_FAILED            = 4
NO_RESUME_THOUGH_REQUESTED   = 5
WRITE_TO_TMP_FILE_FAILED     = 6

string_failed_reasons        = ['Unknown protocol', 'Bad port number', 
                                'Weird response code received', 'Wrong response code received', 
                                'Remote host does not provide resume support, though master said it should']

# MASTER_REQUEST
NEW_URI         = 0
UPLOAD          = 1
ABORT           = 2
KILL            = 3

string_requests = ['Requested new download', 'Requested upload of the results', 'Received ABORT request',
                   'Received KILL request'] 

# TASK_REQUEST 
NEW_TASK        = 0 

# TASK states 
TASK_NEW         = 0
TASK_DOWNLOADING = 1
TASK_MERGING     = 2
TASK_FINISHED    = 3

string_task_states        = ['New', 'Working', 'Merge', 'Finished']




#file fragment state
FF_NEW      = 0
FF_ERROR    = 1
FF_DONE     = 2   

