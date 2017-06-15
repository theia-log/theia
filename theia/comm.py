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

  async def _open_websocket(self):
    websocket = websockets.connect(self._get_ws_url())
    self.websocket = websocket

  def connect(self):
    self.loop.run_until_complete(self._open_websocket())

  def _get_ws_url(self):
    url = 'wss://' if self.secure else 'ws://'
    url += self.host
    if self.port:
      url += str(self.port)
    if self.path:
      if self.path.startswith('/'):
        url += self.path
      else:
        url += '/' + self.path
    return url

  def send(self, message):
    return self.loop.call_soon_threadsafe(self._send, message)

  async def _send(self, message):
    await self.websocket.send(self.serializer.serialize(message))
