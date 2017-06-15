#!/usr/bin/env python

import asyncio
import websockets

from theia.comm import Client

loop = asyncio.get_event_loop()

cl = Client(loop, host='localhost', port=8765,path='/pajo')
cl.connect()

cl.send('pajo')

loop.run_forever()
