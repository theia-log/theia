#!/usr/bin/env python

import asyncio
import websockets

from theia.comm import Client
from theia.model import Event

loop = asyncio.get_event_loop()
loop.set_debug(True)
print('1')
cl = Client(loop, host='localhost', port=8765,path='/pajo')
cl.connect()
print('2: cl.websocket.open: ' + str(cl.websocket.open))
cl.send(Event(id='aaa',source='test',content='pajo'))
loop.run_forever()
print('4')
