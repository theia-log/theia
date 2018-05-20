"""Log aggregator collector.
"""
import asyncio
from io import BytesIO
import json
from logging import getLogger
from threading import Thread
from theia.comm import Server
from theia.model import EventParser, EventSerializer



log = getLogger(__name__)

# pylint: disable=too-few-public-methods
# This needs only one method.
class LiveFilter:
    """Filter for the live event pipe.

    Holds a single criteria to filter events by.

    Args:
        ws(WebSocket) - reference to the web socoket instance.
        criteria(dict) - dict holding criteria values.
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

        Args:
            event(Event) - the event to match.

        Returns:
            match(bool) - True if the event matches the criteria, otherwise False.
        """

        return event.match(**self.criteria)


class Live:
    """Live event pipeline.

    Each event is passed through the live event pipeline and matched to the
    LiveFilter filters.

    Args:
        serializer(theia.model.Serializer) - event serializer.
    """

    def __init__(self, serializer):
        self.serializer = serializer
        self.filters = {}

    def add_filter(self, lfilter):
        """Adds new filter to the pipeline.

        Args:
            lfilter(LiveFilter) - the filter to add to the pipeline.
        """
        self.filters[lfilter.ws] = lfilter

    async def pipe(self, event):
        """Add an event to the live pipeline.

        The event will be matched against all filters in this pipeline.

        Args:
            event(theia.model.Event): the event to be pipelined.
        """

        for ws, live_filter in self.filters.items():
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
                    log.error('Something went wrong: %s', e)
                    log.exception(e)


class Collector:
    """Collector server.

    Collects the events, passes them down the live pipe filters and stores them
    in the event store.

    Args:
        store(theia.storeapi.Store): store instance
        hostame(str): server hostname. Default is '0.0.0.0'.
        port(int: server port. Default is 4300.
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self, store, hostname='0.0.0.0', port=4300):
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

    def run(self):
        """Run the collector server.

        This operation is blocking.
        """
        self._setup_store()
        self._setup_server()
        self.store_thread.join()

    def stop(self):
        """Stop the collector server.

        This operation is non-blocking.
        """

        self.server.stop()
        try:
            self.store_loop.call_soon_threadsafe(self.store_loop.stop)
        finally:
            self.server_loop.call_soon_threadsafe(self.server_loop.stop)
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
        criteria = json.loads(message)
        ts_from = criteria.get('start')
        ts_to = criteria.get('end')
        flags = criteria.get('tags')
        content = criteria.get('content')
        order = criteria.get('order') or 'asc'
        if not ts_from:
            raise Exception('Missing start timestamp')
        self.store_loop.call_soon_threadsafe(
            self._find_event_results, ts_from, ts_to, flags, content, order, websocket)
        return 'ok'

    def _find_event_results(self, start, end, flags, match, order, websocket):
        for event in self.store.search(ts_start=start, ts_end=end, flags=flags,
                                       match=match, order=order):
            ser = self.serializer.serialize(event)
            asyncio.run_coroutine_threadsafe(websocket.send(ser), self.server_loop)
