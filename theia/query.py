"""
-----------
theia.query
-----------

Query theia server for events.

This module contains the :class:`Query` that implements API for querying theia collector server.
"""
import asyncio
import json
from logging import getLogger
from theia.comm import Client


log = getLogger(__name__)


class ResultHandler:
    """Represents a result of a query against a theia collector server.

    The result of a query to the collector server is a stream of events. A callback (see ``callback`` in
    :meth:`Query.live`) can be set to be called whenever an :class:`theia.model.Event` is received, but the control to
    close the stream is passed down to a :class:`ResultHandler`.

    This class wraps the :class:`theia.comm.Client` used to connect to the collector server and adds support for
    registering on client closed events. It also adds means to close (cancel) the connection to the theia server.

    :param client: :class:`theia.comm.Client`, the underlying client to the theia server.

    """
    def __init__(self, client):
        self.client = client
        self._close_handlers = []
        self.client.on_close(self._on_client_closed)

    def _on_client_closed(self, websocket, code, reason):
        for hnd in self._close_handlers:
            try:
                hnd(self.client, code, reason)
            except Exception as e:
                log.debug('ResultHandler[%s]: close hander %s error: %s', self.client, hnd, e)

    def when_closed(self, closed_handler):
        """Register a handler to be called when the connection to the server is closed.

        The handler has the following signature:

        .. code-block:: python

            def closed_handler(client, code, reason):
                pass

        where:

        * ``client`` - :class:`theia.comm.Client`, is the underlying client connected to the theia collector.
        * ``code`` - ``int``, wbsocket close connection code.
        * ``reason`` - ``str``, the reason for closing the connection.

        """
        self._close_handlers.append(closed_handler)

    def cancel(self):
        """Cancel this result.

        Closes the underlying client connection.
        """
        if self.client.is_open():
            self.client.close()


class Query:
    """Represents a query to a theia collector server.

    The query instances are thread-safe.

    :param host: ``str``, the hostname (IP) of the collector server.
    :param port: ``int``, the port of the collector server.
    :param secure: ``bool``, whether to connect securely to the collector server.
    :param loop: :class:`asyncio.BaseEventLoop`, the event loop to use.

    """
    def __init__(self, host, port, secure=False, loop=None):
        self.connections = set()
        self.host = host
        self.port = port
        self.secure = secure
        self.loop = loop if loop is not None else asyncio.get_event_loop()

    def live(self, criteria, callback=None):
        """Make a live query to the collector.

        The collector will watch for any events that occur **after** the live query is registered and return those that
        match the given ``criteria``.

        :param criteria: ``dict``, the criteria filter for the events. This is a ``dict`` that can contain the following
            keys:

            * ``id``, ``str``, pattern for matching the event id.
            * ``source``, ``str``, pattern for matching the event source.
            * ``start``, ``int``, match events with timestamp greater or equal to this.
            * ``end``, ``int``, match events with timestamp less than or equal to this.
            * ``content``, ``str``, pattern for matching the event content.
            * ``tags``, ``list``, list of patterns to match against the event tags.

        :param callback: ``function``, called with the matching event content. The method takes one argument, the
            serialized :class:`theia.model.Event`.

        Returns a :class:`ResultHandler`.
        """
        return self._connect_and_send('/live', criteria, callback)

    def find(self, criteria, callback=None):
        """Make a query to the collector.

        The collector will search for any events that occured **before** theis query was sent to the server and will
        return those that match the given ``criteria``.

        :param criteria: ``dict``, the criteria filter for the events. This is a ``dict`` that can contain the following
            keys:

            * ``id``, ``str``, pattern for matching the event id.
            * ``source``, ``str``, pattern for matching the event source.
            * ``start``, ``int``, match events with timestamp greater or equal to this.
            * ``end``, ``int``, match events with timestamp less than or equal to this.
            * ``content``, ``str``, pattern for matching the event content.
            * ``tags``, ``list``, list of patterns to match against the event tags.

        :param callback: ``function``, called with the matching event content. The method takes one argument, the
            serialized :class:`theia.model.Event`.

        Returns a :class:`ResultHandler`.
        """
        return self._connect_and_send('/find', criteria, callback)

    def _connect_and_send(self, path, criteria, callback):

        client = Client(loop=self.loop, host=self.host, port=self.port, path=path, recv=callback)

        client.connect()

        self.connections.add(client)

        def on_client_closed(websocket, code, reason):
            """Remove the underlying client from the connections set once its connection is closed.
            """
            # client was closed
            if client in self.connections:
                self.connections.remove(client)

        client.on_close(on_client_closed)

        msg = json.dumps(criteria)

        client.send(msg)

        return ResultHandler(client)
