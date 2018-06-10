"""
----------
theia.comm
----------

Theia communication module.

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


_WAIT_TIME = 0.1


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
        self._close_handlers = []

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
            except websockets.ConnectionClosed as wse:
                self._closed(wse.code, wse.reason)
                log.debug('[%s:%d] connection closed', self.host, self.port)
            # pylint: disable=broad-except
            # General case
            except Exception as e:
                log.exception(e)
                self._closed(1006, reason=str(e))

    async def _process_message(self, message):
        if self.recv_handler:
            self.recv_handler(message)

    def on_close(self, handler):
        """Add close handler.

        The handles is called when the client connection is closed either by the client
        or by the server.

        :param handler: ``function``, the handler callback. The callback prototype
            looks like so:

            .. code-block:: python

                def callback(websocket, code, reason):
                    pass

        where:

        * ``websocket`` :class:`websockets.WebSocketClientProtocol` is the underlying
            websocket.
        * ``code`` ``int`` is the code received when the connection was closed. Check
            out the `WebSocket specification`_ for the list of codes and their meaning.
        * ``reason`` ``str`` is the reason for closing the connection.

        .. _WebSocket specification: https://tools.ietf.org/html/rfc6455#section-7.4
        """
        self._close_handlers.append(handler)

    def _closed(self, code=1000, reason=None):
        self._is_open = False
        for hnd in self._close_handlers:
            try:
                hnd(self.websocket, code, reason)
            except Exception as e:
                log.debug(e)

    def is_open(self):
        """Check if the client connection is open.

        Returns ``True`` if the client connection is open, otherwise ``False``.
        """
        return self._is_open


class wsHandler:
    """Wrapper for an incoming websocket connection.

    Used primarily with the :class:`Server` implementation in the client connections
    life-cycle management.

    :param websocket: :class:`websockets.WebSocketClientProtocol`, the underlying
        websocket connection.
    :param path: ``str``, the request path of the websocket connection.

    **Note**: This class is mainly used internally and as such it is a subject of
    chnages in its API.
    """
    def __init__(self, websocket, path):
        self.ws = websocket
        self.path = path
        self.close_handlers = []

    def trigger(self, websocket):
        """Triggers the close handlers for this websocket.

        :param websocket: :class:`websockets.WebSocketClientProtocol`, the underlying
            websocket connection.
        """
        for hnd in self.close_handlers:
            try:
                hnd(self.ws, self.path)
            # pylint: disable=broad-except
            except Exception as ex:
                log.debug(ex)

    def add_close_handler(self, hnd):
        """Register a close handler for this connection.

        :param hnd: ``function``, the close handler callback. The callback receives
            two parameters:

            * ``ws`` (:class:`websockets.WebSocketClientProtocol`), the underlying websocket
                connection.
            * ``path`` (``str``), the request path of the websocket.
        """
        self.close_handlers.append(hnd)


class Server:
    """Listens for and manages multiple client connections.

    The server is based on :mod:`asyncio` event loop. It manages the websocket
    connections comming from multiple clients based on the path in the websocket
    request connection.

    Provides a way to register a callback for notifying when a client connects to
    a particular endpoint (path), and also a way to register a callback for when
    the client disconnects.

    Instances of this class are thread-safe.

    :param loop: :class:`asyncio.BaseEventLoop`, the event loop.
    :param host: ``str``, the hostname to bind to when listening fo incoming
        connections.
    :param port: ``int``, the port to listen on.
    """
    def __init__(self, loop, host='localhost', port=4479):
        self.loop = loop
        self.host = host
        self.port = port
        self.websockets = {}
        self._started = False
        self.actions = {}
        self._stop_timeout = 10

    def on_action(self, path, cb):
        """Register a callback to listen for messages from clients that connected
        to this specific entrypoint (path).

        The callback will be called whenever a new message is received from the client
        on this ``path``.

        If multiple callbacks are registered on the same action, then they are called
        one by one in the same order as registered. The response from the callbacks is
        chained between the subsequent calls.

        :param path: ``str``, the request path of the incoming websocket connection.
        :param cb: ``function``, the callback to be called when a message is received
            from the client on this path.
            The callback handler looks like this:

            .. code-block:: python

                def callback(path, message, websocket, resp):
                    return resp

        where:

        * ``path`` ``str``, the path on which the message was received.
        * ``message`` ``str``, the messge received from the websocket connection.
        * ``websocket`` :class:`websockets.WebSocketClientProtocol`, the underlying
            websocket.
        * ``resp`` ``str``, the response from the previous action registered on this
            same action

        The callback must return ``str`` response or ``None``.
        """
        actions = self.actions.get(path)
        if not actions:
            actions = self.actions[path] = []
        actions.append(cb)

    async def _on_client_connection(self, websocket, path):
        self.websockets[websocket] = wsHandler(websocket, path)
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
        """Register a close callback for this websocket.

        :param websocket: :class:`websockets.WebSocketClientProtocol`, the websocket
            to watch for closing.
        :param cb: ``function``, the callback to be called when the ``websocket``
            is closed. The callback should look like this:

            .. code-block:: python

                def callback(ws, path):
                    pass

        where:

        * ``ws`` (:class:`websockets.WebSocketClientProtocol`), the underlying websocket
                connection.
        * ``path`` (``str``), the request path of the websocket.

        This method returns ``True`` if the callback was added; ``False`` if the
        websocket is not managed by this :class:`Server` instance.
        """
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
        """Starts the server.

        This call blocks until the server is started or an error occurs.
        """
        start_server = websockets.serve(self._on_client_connection,
                                        self.host, self.port, loop=self.loop)
        self.loop.run_until_complete(start_server)
        self._started = True

    def stop(self):
        """Stops the server.

        Closes all client websocket connections then shuts down the server.

        This operation blocks until the server stops or an error occurs.
        """
        from time import sleep
        wss = [ws for ws, _ in self.websockets.items()]
        semaphore = {'value': len(wss)}

        for ws in wss:
            try:
                self._remove_websocket(ws)
            except Exception as exc:
                log.exception(exc)
            asyncio.run_coroutine_threadsafe(self._send_close(semaphore, ws, 'server stop'), self.loop)
        log.debug('Server notified to stop')
        total_wait = 0
        while semaphore['value']:
            sleep(_WAIT_TIME)
            total_wait += _WAIT_TIME
            if total_wait > self._stop_timeout:
                break
        if semaphore['value']:
            log.warning('Stop timeout reached before all connections were closed. Server will stop anyway')
        else:
            log.debug('All done. Server stopped.')

    async def _send_close(self, semaphore, websocket, reason=None):
        await websocket.close(code=1000, reason=reason)
        semaphore['value'] -= 1
