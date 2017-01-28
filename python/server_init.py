# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
print = lambda x: sys.stdout.write("%s\n" % x)
from websocket_server import WebsocketServer

PORT = 9000
server = WebsocketServer(PORT, '127.0.0.1')
agents = 0
simulation = {}
cur_clients = {}
cur_state = {}
cur_actions = {}
cur_data = ""
progress = False
valid_receipt = {}

def start_server():
    server.set_fn_new_client(new_client)
    server.set_fn_client_left(client_left)
    server.set_fn_message_received(message_received)
    server.run_forever()

def message_received(client, server, message):
    global agents, simulation, cur_clients, cur_actions, cur_state, progress, cur_data, valid_receipt
    if len(message) == 0: return
    if message[0] == 'e':
        #This is a debug message
        print('Debug: ', message[1:])
    elif message[0] == 's':
        #This is a setup message - (s{client or unity}:{unity - num agents OR client - cur_id})
        msg_lst = message[1:].split(':')
        if msg_lst[0] == "unity":
            simulation = client
            agents = int(msg_lst[1])
            generate_valid_receipt(True)
            print('Log: Unity simulation connected! ' + str(client['id']) + ' Expected #agents: ' + str(agents))
        elif msg_lst[0] == "client":
            if (int(msg_lst[1]) <= (agents - 1)):
                cur_clients[msg_lst[1]] = client 
                print('Client ' + str(msg_lst[1]) +' connected! ' + str(client['id'])+ ' Current #connections: ' + str(len(cur_clients)))
                if len(cur_clients) == agents and len(simulation) > 0:
                    progress = True
                    print('Log: All clients connected, can now start data bridge')
            else:
                print('Client Error: Client connect request ignored - net id too high')
    elif message[0] == 'd':
        #This is a simulation data message - Updates message stored on server (in sync)
        #d{message_incoming}
        if 'id' in simulation:
            if progress:
                if client['id'] == simulation['id']:
                    if check_valid_receipt():
                        cur_data = message[1:]
                        # print("Log: Server received this from simulation: " + cur_data)
                        generate_valid_receipt(False)
                        for cur in cur_clients:
                            server.send_message(cur_clients[cur], cur_data)
                    else:
                        print('Send Error: Server has not received message receipt from all nets')
                        print(valid_receipt)
                else:
                    print('Send Error: Incorrect sender - sender was not Unity simulator')
            else:
                print('Send Error: All clients have not connected')
    elif message[0] == 'c':
        #This is a client data message representing AN ACTION (c{client_id}:{client_action})
        msg_lst = message[1:].split(':')
        cur_actions[int(msg_lst[0])] = msg_lst[1]
        cur_data = "" #Reset current data as the state is 
        if len(cur_actions) == agents and progress:
            #Send data back to simulation ({action_0}...{action_[agent-1]})
            # print('Log: Sending following data back to simulation *asynchronously*')
            # print(cur_actions)
            msg = str(cur_actions[0])
            for i in range(agents): 
                if i == 0: continue
                msg = msg + ':' + str(cur_actions[i])
            server.send_message(simulation, msg)
            cur_data = "" #Reset current data
            cur_actions = {}
    elif message[0] == 'r':
        #This is a data request (to serve states to clients) - (r{client_id})
        net_id = message[1:]
        #Need to send data to clients
        if (not cur_data == "") and progress:
            server.send_message(cur_clients[net_id], cur_data) #Sent to client requesting data
            for i in range(agents):
                valid_receipt[i] = False
    elif message[0] == 'k':
        #This a received data response
        net_id = message[1:]
        valid_receipt[int(net_id)] = True
        server.send_message(cur_clients[net_id],'k')
        # print(valid_receipt)

def client_left(client, server):
    global agents, simulation, cur_clients, cur_state, progress
    if 'id' in simulation:
        if client['id'] == simulation['id']:
            print('Connect Error: Unity simulation has lost connection with server')
            progress = False
            simulation = {}
            cur_state = ""
            return
    for cur in cur_clients:
        if cur_clients[cur]['id'] == client['id']:
            progress = False
            del cur_clients[cur]
            print('Connect Error: Client ' + cur + ' disconnected! ' + str(client['id']))
            cur_state = ""
            return

def check_valid_receipt():
    global valid_receipt, agents
    # print('Message receipts')
    # print(valid_receipt)
    chk = True
    if not len(valid_receipt) == agents: return False
    for i in range(agents):
        if i in valid_receipt:
            if valid_receipt[i] == False:
                chk = False
                break
    return chk

def generate_valid_receipt(init_val):
    global valid_receipt, agents
    for i in range(agents):
        valid_receipt[i] = init_val

def new_client(client, server):
    pass

if __name__ == "__main__":
    start_server()