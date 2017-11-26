#!/usr/bin/env python

import asyncio
import websockets
from threading import Thread
from uuid import uuid4


from theia.comm import Client
from theia.model import Event

loop = asyncio.get_event_loop()
loop.set_debug(True)
print('1')


def recv(msg):
    print('RECEIVED: ', msg)


cl = Client(loop, host='localhost', port=8765, path='/event', recv=recv)
cl.connect()


def do_send():
    while True:
        msg = input('>')
        id = str(uuid4())
        cl.send_event(Event(id=id, source='repl-test', content=msg))
        print(' >>%s:%s' % (id, msg))


Thread(target=do_send).start()
loop.run_forever()
