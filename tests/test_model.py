from theia.model import Event, EventSerializer, EventParser

from io import StringIO, BytesIO

from unittest import TestCase


class TestEventSerializer(TestCase):

    def test_serialize_event(self):
        ev_str = EventSerializer().serialize(
            Event(id='id1', source='env1', tags=['a', 'b'], content='TEST EVENT'))
        expected = ['event: 68 58 10', 'id:id1', 'timestamp:',
                    'source:env1', 'tags:a,b', 'TEST EVENT', '']
        i = 0
        for line in ev_str.decode('utf-8').split('\n'):
            if i == 2:
                assert line.startswith('timestamp:')
            else:
                assert line == expected[i]
            i += 1

    def test_parse_event(self):
        event_str = '\n'.join(
            ['event: 68 58 10', 'id:id1', 'timestamp: 1491580705.9789374', 'source:env1', 'tags:a,b', 'TEST EVENT'])
        parser = EventParser()
        event = parser.parse_event(BytesIO(event_str.encode('utf-8')))

        assert event
        assert event.id == 'id1'
        assert event.source == 'env1'
        assert event.timestamp == 1491580705.9789374
        assert event.tags == ['a', 'b']
        assert event.content == 'TEST EVENT'
