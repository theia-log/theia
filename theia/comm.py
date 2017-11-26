"""
Client
------
 - Can connect to a server (two-way channel)

Server
-----
 - Can handle multiple connections from clients
 - Can route actions
"""

import asyncio
import json
import logging
import websockets

from theia.model import EventSerializer


class Client:
    """Client represents a client connection to a theia server.
    """

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
        print('connected')

    def connect(self):
        self.loop.run_until_complete(self._open_websocket())

    def close(self, reason=None):
        self._is_open = False
        self.websocket.close(code=1000, reason=reason or 'normal close')

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
        print('URL: %s' % url)
        return url

    def send(self, message):
        print('call soon')
        return self.loop.call_soon_threadsafe(self.call_send, message)

    def call_send(self, message):
        asyncio.ensure_future(self.websocket.send(message), loop=self.loop)
        print('scheduled to send')

    def send_event(self, event):
        message = self.serializer.serialize(event)
        return self.send(message)

    async def _recv(self):
        while self._is_open:
            try:
                message = await self.websocket.recv()
                await self._process_message(message)
            except websockets.ConnectionClosed:
                self._is_open = False
                print('conn closed')
            # pylint: disable=broad-except
            # General case
            except Exception as e:
                print(type(e))
                self._is_open = False
                logging.exception(e)

    async def _process_message(self, message):
        if self.recv_handler:
            self.recv_handler(message)


class wsHandler:

    def __init__(self, websocket, path):
        self.ws = websocket
        self.path = path
        self.close_handlers = []

    def trigger(self):
        for hnd in self.close_handlers:
            try:
                hnd(self.ws, self.path)
            # pylint: disable=broad-except
            except Exception as ex:
                logging.debug(ex)

    def add_close_handler(self, hnd):
        self.close_handlers.append(hnd)


class Server:

    def __init__(self, loop, host='localhost', port=4479):
        self.loop = loop
        self.host = host
        self.port = port
        self.websockets = {}
        self._started = False
        self.actions = {}

    def on_action(self, path, cb):
        actions = self.actions.get(path)
        if not actions:
            actions = self.actions[path] = []
        actions.append(cb)

    async def _on_client_connection(self, websocket, path):
        self.websockets[websockets] = wsHandler(websocket, path)
        try:
            while self._started:
                message = await websocket.recv()
                resp = await self._process_req(path, message, websocket)
                if resp is not None:
                    await websocket.send(str(resp))
                print('Request handled. Server started: ', self._started)
        except websockets.ConnectionClosed:
            self._remove_websocket(websocket)
            print('Closing websocket connection:', websocket)
        except Exception as e:
            self._remove_websocket(websocket)
            print('Closing websocket connection because of unknown error:', websocket)
            logging.exception(e)

    def _remove_websocket(self, websocket):
        # self.websockets.remove(websocket)
        hnd = self.websockets.get(websocket)
        if hnd is not None:
            del self.websockets[websocket]
            hnd.trigger(websocket)

    def on_websocket_close(self, websocket, cb):
        hnd = self.websockets.get(websocket)
        if hnd is not None:
            hnd.add_close_handler(cb)
            return True
        return False

    async def _process_req(self, path, message, websocket):
        resp = ''
        for reg_path, actions in self.actions.items():
            if reg_path == path:
                try:
                    for action in actions:
                        resp = action(path, message, websocket, resp)
                # pylint: disable=broad-except
                # Intended to be broad as it handles generic action
                except Exception as e:
                    logging.exception(e)
                    return json.dumps({"error": str(e)})
                break
        return resp

    def start(self):
        start_server = websockets.serve(self._on_client_connection,
                                        self.host, self.port, loop=self.loop)
        self.loop.run_until_complete(start_server)
        self._started = True

    def stop(self):
        pass
