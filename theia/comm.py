"""
---------------------------
Theia communication module.
---------------------------

Defines classes for building theia servers and clients.

Theia communication module is asynchronous and is built on top of asyncio loop.

There are two main interfaces:

* ``Server`` an async server handling and managing WebSocket connections from multiple clients.
* ``Client`` an async client connection to a theia server.

The interfaces are designed to work primarily with theia events and are thread-safe.
"""

import asyncio
import json
from logging import getLogger
import websockets
from theia.model import EventSerializer


log = getLogger(__name__)


class Client:
    """Client represents a client connection to a theia server.

    :param loop: :mod:`asyncio` EventLoop to use for this client.
    :param host: ``str``, theia server hostname.
    :param port: ``int``, theia server port.
    :param secure: ``bool``, is the connection secure.
    :param path: ``str``, the request path - for example: ``"/live"``, ``"/events"`` etc.
    :param recv: ``function``, receive handler. Called when a message is received from the
        server. The handler has the following signature:
    .. code-block:: python

        def handler(message):
            pass

    where:
        * ``message`` is the message received from the theia server.
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
        log.debug('[%s:%d]: connected', self.host, self.port)

    def connect(self):
        """Connect to the remote server.
        """
        self.loop.run_until_complete(self._open_websocket())

    def close(self, reason=None):
        """Close the connection to the remote server.

        :param reason: ``str``, the reason for disconnecting. If not given, a default ``"normal close"`` is
        sent to the server.

        """
        reason = reason or 'normal close'
        self._is_open = False
        self.websocket.close(code=1000, reason=reason)
        log.debug('[%s:%d]: explicitly closed. Reason=%s', self.host, self.port, reason)

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
        return url

    def send(self, message):
        """Send a ``str`` message to the remote server.

        :param message: ``str``, the message to be sent to the remote server.

        Returns the :class:`asyncio.Handle` to the scheduled task for sending the
        actual data.
        """
        return self.loop.call_soon_threadsafe(self._call_send, message)

    def _call_send(self, message):
        asyncio.ensure_future(self.websocket.send(message), loop=self.loop)

    def send_event(self, event):
        """Send an event to the remote server.

        Serializes, then sends the serialized content to the remote server.

        :param event: :class:`theia.model.Event`, the event to be send.

        Returns the :class:`asyncio.Handle` to the scheduled task for sending the
        actual data.
        """
        message = self.serializer.serialize(event)
        return self.send(message)

    async def _recv(self):
        while self._is_open:
            try:
                message = await self.websocket.recv()
                await self._process_message(message)
            except websockets.ConnectionClosed:
                self._is_open = False
                log.debug('[%s:%d] connection closed', self.host, self.port)
            # pylint: disable=broad-except
            # General case
            except Exception as e:
                self._is_open = False
                log.exception(e)

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
                log.debug(ex)

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
        except websockets.ConnectionClosed:
            self._remove_websocket(websocket)
            log.debug('[Server:%s:%d] Closing websocket connection: %s', self.host, self.port, websocket)
        except Exception as e:
            self._remove_websocket(websocket)
            print('Closing websocket connection because of unknown error:', websocket)
            log.error('[Server:%s:%d] Closing websocket connection because of unknown error: %s',
                      self.host, self.port, websocket)
            log.exception(e)

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
                    log.exception(e)
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
