from __future__ import division
from __future__ import print_function
print = lambda x: sys.stdout.write("%s\n" % x)
from websocket import create_connection
import sys
import time

NUM_GOALS = 20

def send_message_sync(ws, message, id_in):
    ws.send(message)
    result = None
    count = 0
    while result is None:
        try:
            ws.send('r'+id_in)
            result =  ws.recv()
        except:
            count+=1
    receipt = None
    while receipt is None:
        try:
            ws.send('k'+id_in)
            receipt =  ws.recv()
        except:
            pass
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

def state(result_data, id_in):
    arr = result_data.split(':')
    arr = [float(i) for i in arr]
    done = (int(arr[-1]) == NUM_GOALS)
    reward = (arr[-1]) * 500
    if reward <= 0:
        reward = -0.2
    next_state = [float(100*id_in)]
    next_state.extend(arr[:-1])
    return next_state, reward, done 