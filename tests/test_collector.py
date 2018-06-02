"""Test theia collector module.
"""
import asyncio
from datetime import datetime
from unittest import mock
from websockets import WebSocketClientProtocol as WebSocket
from theia.collector import LiveFilter, Live, Collector
from theia.model import Event, EventSerializer
from theia.storeapi import EventStore


_WAIT_TIME = 0.3


def test_live_filter_match():
    """Test live filter events matching.
    """
    live_filter = LiveFilter(ws=None, criteria={'id': '1000'})

    event = Event(id='1000', source='src1', timestamp=datetime.now().timestamp(),
                  tags=[], content='event 1')

    assert live_filter.match(event)

    event = Event(id='2000', source='src1', timestamp=datetime.now().timestamp(),
                  tags=[], content='event 1')

    assert live_filter.match(event) is False  # should not match

    live_filter = LiveFilter(ws=None, criteria={'source': 'src1'})

    assert live_filter.match(event)

    event = Event(id='2000', source='src2', timestamp=datetime.now().timestamp(),
                  tags=[], content='event 1')

    assert live_filter.match(event) is False

    start = int(datetime.now().timestamp())
    event = Event(id='2000', source='src2', timestamp=start,
                  tags=[], content='event 1')

    live_filter = LiveFilter(ws=None, criteria={'start': start})
    assert live_filter.match(event)

    live_filter = LiveFilter(ws=None, criteria={'start': start + 1})
    assert live_filter.match(event) is False

    live_filter = LiveFilter(ws=None, criteria={'end': start})
    assert live_filter.match(event)

    live_filter = LiveFilter(ws=None, criteria={'end': start - 1})
    assert live_filter.match(event) is False

    live_filter = LiveFilter(ws=None, criteria={'content': 'eve.+'})
    assert live_filter.match(event)

    live_filter = LiveFilter(ws=None, criteria={'content': 'but not this.+'})
    assert live_filter.match(event) is False

    live_filter = LiveFilter(ws=None, criteria={'tags': ['a', 'b']})
    event = Event(id='2000', source='src2', timestamp=start,
                  tags=['c', 'd', 'b', 'a'], content='event 1')
    assert live_filter.match(event)

    live_filter = LiveFilter(ws=None, criteria={'tags': ['a', 'b', 'x']})
    assert live_filter.match(event) is False


def test_live_add_filter():
    """Test adding filter to live pipeline.
    """
    live = Live(serializer=None)

    live.add_filter(LiveFilter(ws=WebSocket(), criteria={'id': '100'}))

    assert len(live.filters) == 1


@mock.patch.object(WebSocket, 'send')
@mock.patch.object(EventSerializer, 'serialize')
def test_live_pipeline(m_serialize, m_send):
    """Test event matching in the live pipeline.
    """

    loop = asyncio.get_event_loop()

    filtered = []

    async def mock_send(data):
        filtered.append(data)

    def mock_serialize(event):
        return "event:%s" % event.id

    m_send.side_effect = mock_send
    m_serialize.side_effect = mock_serialize

    live = Live(serializer=EventSerializer())

    live.add_filter(LiveFilter(ws=WebSocket(), criteria={'id': '1000'}))
    live.add_filter(LiveFilter(ws=WebSocket(), criteria={'tags': ['a']}))

    for event in [Event(id='1000', source='s1', tags=['a', 'b', 'c']), Event(id='2000', source='s2'),
                  Event(id='3000', source='s1', tags=['a', 'b']), Event(id='4000', source='s3')]:
        loop.create_task(live.pipe(event))

    loop.call_soon(loop.stop)
    loop.run_forever()

    assert len(filtered) == 3


def test_create_collector():
    store = EventStore()
    coll = Collector(store=store, hostname="127.0.0.1", port=1122)
    
    assert coll.hostname == "127.0.0.1"
    assert coll.port == 1122
    assert coll.parser is not None
    assert coll.serializer is not None
    assert coll.live is not None


def test_run_collector():
    from time import sleep
    from threading import Thread
    store = EventStore()
    coll = Collector(store=store, hostname="127.0.0.1", port=1122)
    
    def do_run():
        print('coll.run()')
        coll.run()
        print('coll.run() end')
    
    t = Thread(target=do_run)
    t.start()
    sleep(_WAIT_TIME)
    
    assert coll.store_loop is not None
    assert coll.server_loop is not None
    
    coll.store_loop.call_soon_threadsafe(coll.store_loop.stop)
    coll.server_loop.call_soon_threadsafe(coll.server_loop.stop)
    print('waiting for threads to complete...')
    t.join()


def test_run_and_stop_collector():
    from time import sleep
    from threading import Thread
    store = EventStore()
    coll = Collector(store=store, hostname="127.0.0.1", port=1122)
    
    def do_run():
        print('coll.run()')
        coll.run()
        print('coll.run() end')
    
    t = Thread(target=do_run)
    t.start()
    sleep(_WAIT_TIME)
    
    assert coll.store_loop is not None
    assert coll.server_loop is not None
    
    coll.stop()
    print('waiting for threads to complete...')
    t.join()


@mock.patch.object(EventStore, 'save')
def test_collect_events(m_save):
    from time import sleep
    from threading import Thread
    
    stored_events = []
    
    def save_event(event):
        stored_events.append(event)
    
    m_save.side_effect = save_event
    
    ser = EventSerializer()
    store = EventStore()
    coll = Collector(store=store, hostname="127.0.0.1", port=1122)
    
    def do_run():
        coll.run()
    
    t = Thread(target=do_run)
    t.start()
    sleep(_WAIT_TIME)
    
    assert coll.store_loop is not None
    assert coll.server_loop is not None
    
    coll.server_loop.call_soon_threadsafe(coll._on_event,
                                          '/event',
                                          ser.serialize(Event(id='001',
                                                              timestamp=10,
                                                              tags=['1','2'],
                                                              source='src1',
                                                              content='event 1')),
                                          None,
                                          None)
    coll.server_loop.call_soon_threadsafe(coll._on_event,
                                          '/event',
                                          ser.serialize(Event(id='002',
                                                              timestamp=20,
                                                              tags=['1','2', '3'],
                                                              source='src2',
                                                              content='event 2')),
                                          None,
                                          None)
    sleep(_WAIT_TIME)
    coll.stop()
    print('waiting for threads to complete...')
    t.join()
    assert len(stored_events) == 2


@mock.patch.object(WebSocket, 'send')
@mock.patch.object(EventStore, 'save')
def test_collect_and_filter_events(m_save, m_send):
    from time import sleep
    from threading import Thread
    
    stored_events = []
    
    def save_event(event):
        stored_events.append(event)
    
    send_messages = []
    
    def send_ws_message(message):
        send_messages.append(message)
    
    m_save.side_effect = save_event
    m_send.side_effect = send_ws_message
    
    ser = EventSerializer()
    store = EventStore()
    coll = Collector(store=store, hostname="127.0.0.1", port=1122)
    
    def do_run():
        coll.run()
    
    t = Thread(target=do_run)
    t.start()
    sleep(_WAIT_TIME)
    
    assert coll.store_loop is not None
    assert coll.server_loop is not None
    
    # Register filter
    
    coll.server_loop.call_soon_threadsafe(coll._add_live_filter,
                                          '/live',
                                          '{"tags": ["3"]}',
                                          WebSocket(),
                                          None)
    
    
    coll.server_loop.call_soon_threadsafe(coll._on_event,
                                          '/event',
                                          ser.serialize(Event(id='001',
                                                              timestamp=10,
                                                              tags=['1','2'],
                                                              source='src1',
                                                              content='event 1')),
                                          None,
                                          None)
    coll.server_loop.call_soon_threadsafe(coll._on_event,
                                          '/event',
                                          ser.serialize(Event(id='002',
                                                              timestamp=20,
                                                              tags=['1','2', '3'],
                                                              source='src2',
                                                              content='event 2')),
                                          None,
                                          None)
    sleep(_WAIT_TIME)
    coll.stop()
    print('waiting for threads to complete...')
    t.join()
    assert len(stored_events) == 2
    assert len(send_messages) == 1


@mock.patch.object(WebSocket, 'send')
@mock.patch.object(EventStore, 'search')
def test_find_events(m_search, m_send):
    from time import sleep
    from threading import Thread
    
    events = [Event(id='ev-1', timestamp=10, tags=['t-1'], source='s-1', content='c-1'),
              Event(id='ev-2', timestamp=20, tags=['t-1'], source='s-1', content='c-2'),
              Event(id='ev-3', timestamp=30, tags=['t-1'], source='s-1', content='c-3')]
    
    ws_messages = []
    
    async def send_ws_message(msg):
         ws_messages.append(msg)
    
    m_send.side_effect = send_ws_message
    
    def yield_events(*args, **kwargs):
        for event in events:
            yield event
    
    m_search.side_effect = yield_events
    
    store = EventStore()
    coll = Collector(store=store, hostname="127.0.0.1", port=1122)
    
    def do_run():
        coll.run()
    
    t = Thread(target=do_run)
    t.start()
    sleep(_WAIT_TIME)
    
    assert coll.store_loop is not None
    assert coll.server_loop is not None
    
    coll.server_loop.call_soon_threadsafe(coll._find_event,
                                          '/find',
                                          '{"tags": ["c-1"], "start": 1}',
                                          WebSocket(),
                                          None)
    
    sleep(_WAIT_TIME)
    coll.stop()
    t.join()
    
    assert len(ws_messages) == 3
