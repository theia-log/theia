"""Test theia collector module.
"""
import asyncio
from datetime import datetime
from unittest import mock
from websockets import WebSocketClientProtocol as WebSocket
from theia.collector import LiveFilter, Live
from theia.model import Event, EventSerializer


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
