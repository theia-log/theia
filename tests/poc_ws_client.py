#!/usr/bin/env python

import asyncio
import websockets
from threading import Thread


from theia.comm import Client
from theia.model import Event

loop = asyncio.get_event_loop()
loop.set_debug(True)
print('1')

def recv(msg):
  print('RECEIVED: ', msg)

cl = Client(loop, host='localhost', port=8765,path='/pajo', recv=recv)
cl.connect()
print('2: cl.websocket.open: ' + str(cl.websocket.open))

def do_send():
  cl.send_event(Event(id='aaa',source='test',content='pajo'))
Thread(target=do_send).start()
loop.run_forever()
print('4')
