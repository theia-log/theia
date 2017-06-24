"""
Client
------
 - Can connect to a server (two-way channel)

Server
-----
 - Can handle multiple connections from clients
 - Can route actions
"""

from theia.model import EventSerializer
import websockets
import asyncio

class Client:

  def __init__(self, loop, host, port, secure=False, path=None, recv=None):
    self.loop = loop
    self.host = host
    self.port = port
    self.secure = secure
    self.path = path
    self.recv_handler = recv
    self.serializer = EventSerializer()
    self.websocket = None
    self._is_open = False

  async def _open_websocket(self):
    websocket = await websockets.connect(self._get_ws_url(), loop=self.loop)
    self.websocket = websocket

  def connect(self):
    self.loop.run_until_complete(self._open_websocket())
    self._is_open = True
  
  def close(self):
    self._is_open = False

  def _get_ws_url(self):
    url = 'wss://' if self.secure else 'ws://'
    url += self.host
    if self.port:
      url += ':' + str(self.port)
    if self.path:
      if self.path.startswith('/'):
        url += self.path
      else:
        url += '/' + self.path
    print('URL: %s' %url)
    return url

  def send(self, event):
    return asyncio.run_coroutine_threadsafe(self.websocket.send(message), self.loop)
  
  def send_event(self, event):
    message = self.serializer.serialize(message)
    return self.send(message)

class Server:
  
  def __init__(self, host='localhost', port=4479):
    self.host = host
    self.port = port
  
  def start(self):
    pass
  
  def stop(self):
    pass


