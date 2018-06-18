from theia.cli.query import get_parser, format_event, event_printer, run_query
from theia.query import Query, ResultHandler
import asyncio
from argparse import ArgumentParser
from io import StringIO
from unittest import mock


def test_get_parser():
    parent_parser = ArgumentParser(prog='test')
    
    subparsers = parent_parser.add_subparsers(dest='command', title='command',
                                              help='CLI commands')
    
    parser = get_parser(subparsers)
    
    # test the defaults
    
    args = parser.parse_args(args=[])
    
    assert args.live is False
    assert args.o_format == '{timestamp:15} [{source:10}] {tags:15}: {content}'
    assert args.o_ts_format == '%Y-%m-%d %H:%M:%S.%f%Z'
    assert args.close_timeout == 10

    args = parser.parse_args(args=['-l'])
    assert args.live is True
    
    args = parser.parse_args(args=['--live'])
    assert args.live is True
    
    args = parser.parse_args(args=['--id', 'id_pattern'])
    assert args.f_id == 'id_pattern'
    
    args = parser.parse_args(args=['-s', 'source_pattern'])
    assert args.f_source == 'source_pattern'
    
    args = parser.parse_args(args=['--source', 'source_pattern'])
    assert args.f_source == 'source_pattern'
    
    args = parser.parse_args(args=['-a', '100'])
    assert args.f_after == 100
    
    args = parser.parse_args(args=['--after', '200'])
    assert args.f_after == 200
    
    args = parser.parse_args(args=['-b', '100'])
    assert args.f_before == 100
    
    args = parser.parse_args(args=['--before', '200'])
    assert args.f_before == 200
    
    args = parser.parse_args(args=['-c', 'content_pattern'])
    assert args.f_content == 'content_pattern'
    
    args = parser.parse_args(args=['--content', 'content_pattern'])
    assert args.f_content == 'content_pattern'
    
    args = parser.parse_args(args=['-t', 'a', 'b', 'c'])
    assert args.f_tags == ['a', 'b', 'c']
    
    args = parser.parse_args(args=['--tags', 'a', 'b', 'c'])
    assert args.f_tags == ['a', 'b', 'c']
    
    args = parser.parse_args(args=['-o', 'asc'])
    assert args.f_order == 'asc'
    
    args = parser.parse_args(args=['--order', 'desc'])
    assert args.f_order == 'desc'
    
    args = parser.parse_args(args=['-F', 'out_format'])
    assert args.o_format == 'out_format'
    
    args = parser.parse_args(args=['--format-output', 'format_output'])
    assert args.o_format == 'format_output'
    
    args = parser.parse_args(args=['-T', 'time_format'])
    assert args.o_ts_format == 'time_format'
    
    args = parser.parse_args(args=['--format-timestamp', 'time_format'])
    assert args.o_ts_format == 'time_format'
    
    args = parser.parse_args(args=['--close-timeout', '30'])
    assert args.close_timeout == 30


def test_format_event():
    from theia.model import Event, EventParser
    
    event = Event(id='id-0', timestamp=1529233605, source='/source/1', tags=['a', 'b'],
                  content='event 1')
                  
    result = format_event(event, '{id}|{timestamp}|{source}|{tags}|{content}')
    assert result == 'id-0|1529233605|/source/1|a,b|event 1'
    
    # test with date format
    result = format_event(event, '{id}|{timestamp}|{source}|{tags}|{content}', '%Y-%m-%d')
    assert result == 'id-0|2018-06-17|/source/1|a,b|event 1'

@mock.patch('sys.stdout', new_callable=StringIO)
def test_event_printer(m_stdout):
    from theia.model import Event, EventParser, EventSerializer
    
    event = Event(id='id-0', timestamp=1529233605, source='/source/1', tags=['a', 'b'],
                  content='event 1')
    parser = EventParser('UTF-8')
    print_event = event_printer('{id}|{timestamp}|{source}|{tags}|{content}', '%Y-%m-%d', parser)
    
    assert print_event is not None
    
    print_event(EventSerializer().serialize(event))
    
    assert m_stdout.getvalue() == 'id-0|2018-06-17|/source/1|a,b|event 1\n'


@mock.patch.object(Query, 'live')
@mock.patch.object(ResultHandler, 'when_closed')
@mock.patch.object(asyncio, 'get_event_loop')
def test_run_query_live(m_get_event_loop, m_when_closed, m_live):
    from collections import namedtuple
    from threading import Thread
    from time import sleep
    
    Namespace = namedtuple('Namespace', ['server_host', 'port', 'live', 'f_source',
                                        'f_id', 'f_after', 'f_before', 'f_content',
                                        'f_tags','f_order', 'o_format', 'o_ts_format',
                                        'close_timeout'])
    
    args = Namespace(server_host='localhost',
                     port=1123,
                     live=True,
                     f_source='src-pattern',
                     f_id='id-pattern',
                     f_after=1000,
                     f_before=2000,
                     f_content='content-pattern',
                     f_tags=['a', 'b'],
                     f_order='order-pattern',
                     o_format='out-format',
                     o_ts_format='ts-format',
                     close_timeout=20)
   
    loop = asyncio.new_event_loop()
    m_get_event_loop.return_value = loop
   
    state = {}
   
    def fake_when_closed(handler):
        state['when_closed'] = handler
    
    m_when_closed.side_effect = fake_when_closed
    
    result_handler = ResultHandler(client=mock.MagicMock())
    
    def fake_live(crt, cb):
        assert cb is not None
        assert crt.get('source') == 'src-pattern'
        assert crt.get('id') == 'id-pattern'
        assert crt.get('start') == 1000
        assert crt.get('end') == 2000
        assert crt.get('content') == 'content-pattern'
        assert crt.get('tags') == ['a', 'b']
        
        return result_handler
   
    m_live.side_effect = fake_live
    
    
    def stop_loop():
        sleep(0.4)
        assert state.get('when_closed') is not None
        loop.call_soon_threadsafe(state['when_closed'])
    
    t = Thread(target=stop_loop)
    t.start()
    run_query(args)
    t.join()
    assert m_live.call_count == 1
    assert m_get_event_loop.call_count == 1
    assert m_when_closed.call_count == 1
         

@mock.patch.object(Query, 'find')
@mock.patch.object(ResultHandler, 'when_closed')
@mock.patch.object(asyncio, 'get_event_loop')
def test_run_query_find(m_get_event_loop, m_when_closed, m_find):
    from collections import namedtuple
    from threading import Thread
    from time import sleep
    
    Namespace = namedtuple('Namespace', ['server_host', 'port', 'live', 'f_source',
                                        'f_id', 'f_after', 'f_before', 'f_content',
                                        'f_tags','f_order', 'o_format', 'o_ts_format',
                                        'close_timeout'])
    
    args = Namespace(server_host='localhost',
                     port=1123,
                     live=False,
                     f_source='src-pattern',
                     f_id='id-pattern',
                     f_after=1000,
                     f_before=2000,
                     f_content='content-pattern',
                     f_tags=['a', 'b'],
                     f_order='order-pattern',
                     o_format='out-format',
                     o_ts_format='ts-format',
                     close_timeout=20)
   
    loop = asyncio.new_event_loop()
    m_get_event_loop.return_value = loop
   
    state = {}
   
    def fake_when_closed(handler):
        state['when_closed'] = handler
    
    m_when_closed.side_effect = fake_when_closed
    
    result_handler = ResultHandler(client=mock.MagicMock())
    
    def fake_find(crt, cb):
        assert cb is not None
        assert crt.get('source') == 'src-pattern'
        assert crt.get('id') == 'id-pattern'
        assert crt.get('start') == 1000
        assert crt.get('end') == 2000
        assert crt.get('content') == 'content-pattern'
        assert crt.get('tags') == ['a', 'b']
        
        return result_handler
   
    m_find.side_effect = fake_find
    
    
    def stop_loop():
        sleep(0.4)
        assert state.get('when_closed') is not None
        loop.call_soon_threadsafe(state['when_closed'])
    
    t = Thread(target=stop_loop)
    t.start()
    run_query(args)
    t.join()
    assert m_find.call_count == 1
    assert m_get_event_loop.call_count == 1
    assert m_when_closed.call_count == 1
         
    
