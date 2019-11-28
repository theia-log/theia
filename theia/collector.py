"""
---------------
theia.collector
---------------

The log aggregator collector server implementation.
"""
import asyncio
from io import BytesIO
import json
from logging import getLogger
from threading import Thread

from websockets.exceptions import ConnectionClosed

from theia.comm import Server
from theia.model import EventParser, EventSerializer


log = getLogger(__name__)

# pylint: disable=too-few-public-methods
# This needs only one method.
class LiveFilter:
    """Filter for the live event pipe.

    Holds a single criteria to filter events by.

    :param ws: :class:`websockets.WebSocketClientProtocol`, reference to the web socket instance.
    :param criteria: ``dict``,  dict holding criteria values.
    """

    ALLOWED_CRITERIA = {'id': str, 'source': str,
                        'start': int, 'end': int, 'content': str, 'tags': list}

    def __init__(self, ws, criteria):
        self.ws = ws
        self.criteria = criteria
        self._check_criteria()

    def _check_criteria(self):
        for k, value in self.criteria.items():
            allowed = LiveFilter.ALLOWED_CRITERIA[k]
            if allowed is None:
                raise Exception('unknown criteria %s' % k)
            if not isinstance(value, allowed):
                raise Exception('invalid value for criteria %s' % k)

    def match(self, event):
        """Matches an event to the criteria of this filter.

        :param event: :class:`theia.model.Event`, the event to match.

        :returns: match(``bool``), True if the event matches the criteria,
            otherwise False.
        """

        return event.match(**self.criteria)


class Live:
    """Live event pipeline.

    Each event is passed through the live event pipeline and matched to the
    LiveFilter filters.

    :param serializer: :class:`theia.model.Serializer`, event serializer.
    """

    def __init__(self, serializer):
        self.serializer = serializer
        self.filters = {}
        self.error_handlers = []
        self.add_error_handler(self._default_error_handler)

    def add_filter(self, lfilter):
        """Adds new filter to the pipeline.

        :param lfilter: :class:`LiveFilter`, the filter to add to the pipeline.
        """
        self.filters[lfilter.ws] = lfilter

    def add_error_handler(self, handler):
        """Adds error handler. The handler will be called for each error that occurs
        while processing the filters in this live pipe.

        :param function handler: error handler callback. The handler has the following prototype:

            .. code-block:: python

                def handler(err, websocket, live_filter):
                    pass

            where:

            * ``err`` (:class:`Exception`) the actual error.
            * ``websocket`` (:class:`websockets.WebSocketClientProtocol`) reference to the WebSocket instance.
            * ``live_filter`` (:class:`LiveFilter`) filter criteria.

        """
        self.error_handlers.append(handler)

    def _handle_error(self, err, websocket, live_filter):
        for handler in self.error_handlers:
            try:
                handler(err, websocket, live_filter)
            except Exception as e:
                log.warning('Error while handling exception: %s', e)

    async def pipe(self, event):
        """Add an event to the live pipeline.

        The event will be matched against all filters in this pipeline.

        :param event: :class:`theia.model.Event`, the event to be pipelined.
        """
        # we have to clone the filters dict to allow the filters to be altered by the error handlers during iteration.
        filters_clone = {}
        filters_clone.update(self.filters)

        for ws, live_filter in filters_clone.items():
            if live_filter.match(event):
                try:
                    result = None
                    try:
                        result = self.serializer.serialize(event)
                    except Exception as se:
                        # failed to serialize
                        result = json.dumps({'error': True, 'message': str(se)})
                        log.debug('Serialization error: %s', se)
                    await ws.send(result)
                except Exception as e:
                    log.debug('Error happened when processing and sending to pipe: %s', e)
                    self._handle_error(e, ws, live_filter)

    def _default_error_handler(self, err, websocket, live_filter):
        if isinstance(err, ConnectionClosed):
            if self.filters.get(websocket):
                del self.filters[websocket]
        else:
            log.error('Error in pipe: %s', err)


class Collector:
    """Collector server.

    Collects the events, passes them down the live pipe filters and stores them
    in the event store.

    :param store: :class:`theia.storeapi.Store`, store instance
    :param hostame: ``str``, server hostname. Default is '0.0.0.0'.
    :param port: ``int``, server port. Default is 4300.
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, store, hostname='0.0.0.0', port=4300, persistent=True):
        self.hostname = hostname
        self.port = port
        self.server = None
        self.store = store
        self.server_thread = None
        self.store_thread = None
        self.store_loop = None
        self.server_loop = None
        self.parser = EventParser()
        self.serializer = EventSerializer()
        self.live = Live(self.serializer)
        self.persistent = persistent

    def run(self):
        """Run the collector server.

        This operation is blocking.
        """
        if self.persistent:
            self._setup_store()

        self._setup_server()

        if self.persistent:
            self.store_thread.join()
        else:
            log.info('Collector will not persist the events. To persist the events please run it in persistent mode.')

        self.server_thread.join()

    def stop(self):
        """Stop the collector server.

        This operation is non blocking.
        """

        self.server.stop()
        try:
            if self.persistent:
                self.store_loop.call_soon_threadsafe(self.store_loop.stop)
        finally:
            self.server_loop.call_soon_threadsafe(self.server_loop.stop)
        if self.store:
            self.store.close()

    def _setup_store(self):
        def run_store_thread():
            """Runs the store loop in a separate thread.
            """

            loop = asyncio.new_event_loop()
            self.store_loop = loop
            loop.run_forever()
            loop.close()
            log.info('store is shut down.')

        self.store_thread = Thread(target=run_store_thread)
        self.store_thread.start()

    def _setup_server(self):
        def run_in_server_thread():
            """Runs the server loop in a separate thread.
            """

            loop = asyncio.new_event_loop()
            self.server_loop = loop
            self.server = Server(loop=loop, host=self.hostname, port=self.port)
            self.server.on_action('/event', self._on_event)
            self.server.on_action('/live', self._add_live_filter)
            self.server.on_action('/find', self._find_event)
            self.server.start()
            loop.run_forever()
            loop.close()
            log.info('server is shut down.')

        self.server_thread = Thread(target=run_in_server_thread)
        self.server_thread.start()

    def _on_event(self, path, message, websocket, resp):
        try:
            self.store_loop.call_soon_threadsafe(self._store_event, message)
        except Exception as e:
            log.exception(e)

    def _store_event(self, message):
        event = self.parser.parse_event(BytesIO(message))
        if self.persistent:
            self.store.save(event)
        try:
            asyncio.run_coroutine_threadsafe(self.live.pipe(event), self.server_loop)
        except Exception as e:
            log.error('Error in pipe: %s (event: %s)', e, event)

    def _add_live_filter(self, path, message, websocket, resp):
        criteria = json.loads(message)
        live_filter = LiveFilter(websocket, criteria)
        self.live.add_filter(live_filter)
        return 'ok'

    def _find_event(self, path, message, websocket, resp):
        if not self.persistent:
            return '{"error": "Action not available in non-persistent mode."}'
        criteria = json.loads(message)
        ts_from = criteria.get('start')
        ts_to = criteria.get('end')
        flags = criteria.get('tags')
        content = criteria.get('content')
        order = criteria.get('order') or 'asc'
        if not ts_from:
            raise Exception('Missing start timestamp')
        asyncio.run_coroutine_threadsafe(self._find_event_results(start=ts_from,
                                                                  end=ts_to,
                                                                  flags=flags,
                                                                  match=content,
                                                                  order=order,
                                                                  websocket=websocket),
                                         self.store_loop)
        return 'ok'

    async def _find_event_results(self, start, end, flags, match, order, websocket):
        for event in self.store.search(ts_start=start, ts_end=end, flags=flags,
                                       match=match, order=order):
            await self._send_result(event, websocket)
            await asyncio.sleep(0, loop=self.store_loop)  # let other tasks run

    async def _send_result(self, event, websocket):
        ser = self.serializer.serialize(event)
        result = asyncio.run_coroutine_threadsafe(websocket.send(ser), self.server_loop)
        result.result()
