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
import json

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
    self._is_open = True
    asyncio.ensure_future(self._recv(), loop=self.loop)
    #self._recv()
  def connect(self):
    self.loop.run_until_complete(self._open_websocket())

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

  def send(self, message):
    return self.loop.call_soon_threadsafe(self.call_send, message)

  def call_send(self, message):
    asyncio.ensure_future(self.websocket.send(message), loop=self.loop)

  def send_event(self, event):
    message = self.serializer.serialize(event)
    return self.send(message)

  async def _recv(self):
    print('1')
    while self._is_open:
      print('2>')
      try:
        message = await self.websocket.recv()
        print(' *** message>', message)
        await self._process_message(message)
      except Exception as e:
        print('Error:', e)
        self._is_open = False

  async def _process_message(self, message):
    if self.recv_handler:
      self.recv_handler(message)


class Server:

  def __init__(self, loop, host='localhost', port=4479):
    self.loop = loop
    self.host = host
    self.port = port
    self.websockets = set()
    self._started = False
    self.actions = {}

  def on_action(self, path, cb):
    actions = self.actions.get(path)
    if not actions:
      actions = self.actions[path] = []
    actions.append(cb)

  async def _on_client_connection(self, websocket, path):
    self.websockets.add(websocket)
    try:
      while self._started:
        message = await websocket.recv()
        resp = await self._process_req(path, message, websocket)
        await websocket.send(resp)
    except Exception as e:
      self._remove_websocket(websocket)

  def _remove_websocket(self, websocket):
    self.websockets.remove(websocket)

  async def _process_req(self, path, message, websocket):
    resp = ''
    for reg_path, actions in self.actions.items():
      if reg_path == path:
        try:
          for action in actions:
            resp = action(path, message, websocket, resp)
        except Exception as e:
          return json.dumps({"error": str(e)})
        break
    return resp

  def start(self):
    start_server = websockets.serve(self._on_client_connection, self.host, self.port)
    self.loop.run_until_complete(start_server)
    self._started = True

  def stop(self):
    pass
