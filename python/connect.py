from __future__ import division
from __future__ import print_function
print = lambda x: sys.stdout.write("%s\n" % x)
from websocket import create_connection
import sys
import time

NUM_GOALS = 20
NUM_AGENTS = 4


def send_message_sync(ws, message, id_in):
    ws.send(message)
    result = None
    count = 0
    while result is None:
        try:
            ws.send('r'+id_in)
            result =  ws.recv()
            if result == 'k':
                result = None
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

count = 0
def state(result_data, id_in):
    global count
    arr = result_data.split(':')
    arr = [float(i) for i in arr]
    next_state = arr[int(id_in):int(id_in)+4]
    next_state = [float(i) for i in next_state]
    done = False
    if id_in == 0:
        count += int(arr[-1])
        if count == NUM_GOALS:
            count = 0
            done = True
    reward = (arr[-1]) * 100
    if reward <= 0:
        reward = -1
    new = []
    for i in range(len(arr)):
        if i%4 < 2 and i < (NUM_AGENTS*4):
            new.append(arr[i])
        elif i >= (NUM_AGENTS*4):
            new.append(arr[i])
    next_state.extend(new[:-1])
    return next_state, reward, done 