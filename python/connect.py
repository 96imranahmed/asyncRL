from __future__ import division
from websocket import create_connection
import sys
import time

def send_message_sync(msg, ws):
    ws.send(msg)
    result = None
    count = 0
    return result


ws = create_connection("ws://localhost:9000")
ws.settimeout(0.05)
while True:
    try:
        msg = raw_input()
        send_message_sync(msg, ws)
    except KeyboardInterrupt:
        ws.close()
        sys.exit()
