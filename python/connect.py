from __future__ import division
from __future__ import print_function
print = lambda x: sys.stdout.write("%s\n" % x)
from websocket import create_connection
import sys
import time

# agents = [0,0,0,0]

def send_message_sync(ws, message, id_in, lock):
    # global agents
    #lock.acquire()
    print('Requesting thread: ' + str(id_in) + ' ' + message)
    ws.send(message)
    # agents[int(id_in)] = 1
    # print(agents)
    result = None
    count = 0
    # relock = False
    # if not all_synced():
    #     lock.release()
    #     relock = True
    # while not all_synced():
    #     pass
    # if relock: 
    #     lock.acquire()
    #     agents = [0,0,0,0]
    while result is None:
        try:
            ws.send('r'+id_in)
            result =  ws.recv()
            pass
        except:
            count+=1
    ws.send('k'+id_in)
    # print(result)
    # lock.release() 
    return result

def all_synced():
    global agents
    for item in agents:
        if item == 0:
            return False
    return True

def create_socket(connect_message):
    ws = create_connection("ws://localhost:9000")
    ws.settimeout(0.05)
    ws.send(connect_message)
    try:
        _ = ws.recv()
    except:
        pass
    return ws

def state(result_data):
    return result_data