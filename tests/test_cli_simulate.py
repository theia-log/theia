from theia.cli.simulate import (get_parser,
                                generate_content,
                                generate_rand_items,
                                generate_rand_event,
                                simulate_events)
from unittest import mock
from theia.comm import Client
import asyncio


def test_get_parser():
    parser = get_parser()
    
    
    args = parser.parse_args([])
    assert args.host == 'localhost'
    assert args.port == 6433
    assert args.delay == 1.0
    
    args = parser.parse_args(['-H', 'hostname'])
    assert args.host == 'hostname'
    
    args = parser.parse_args(['--host', 'hostname'])
    assert args.host == 'hostname'
    
    args = parser.parse_args(['-p', '11223'])
    assert args.port == 11223
    
    args = parser.parse_args(['--port', '11223'])
    assert args.port == 11223
    
    args = parser.parse_args(['-t', 't1', 't2', 't3'])
    assert args.tags == ['t1', 't2', 't3']
    
    args = parser.parse_args(['-s', 's1', 's2', 's3'])
    assert args.sources == ['s1', 's2', 's3']
    
    args = parser.parse_args(['-c', 'alternative content'])
    assert args.content == 'alternative content'
    
    args = parser.parse_args(['--content-size', '1234'])
    assert args.content_size == 1234
    
    args = parser.parse_args(['--delay', '12.34'])
    assert args.delay == 12.34


def test_generate_content():
    content = generate_content()
    assert content is not None
    assert content
    
    content = generate_content(content='alternative content')
    assert content == 'alternative content'
    
    for i in range(0, 150):
        content = generate_content(size=120)
        assert content is not None
        assert len(content) >= 120


def test_generate_rand_items():
    items = [1, 2, '3', '4', 'five']
    
    rnd = generate_rand_items([], 'ten')
    assert rnd
    assert rnd[0] == 'ten'
    
    rnd = generate_rand_items(['ten'], None)
    assert rnd
    assert rnd[0] == 'ten'
    
    for i in range(0, 150):
        rnd = generate_rand_items(items, None)
        assert rnd is not None
        assert rnd
        assert set(rnd).issubset(set(items))


def test_generate_rand_event():
    from random import randint
    tags = ['ttag-%d' % i for i in range(0, 10)]
    sources = ['source-%d' % i for i in range(0, 10)]
    content = 'alternative content'

    for i in range(0, 500):
        size = randint(5, 150)
        cnt = content if randint(0, 1) else None
        event = generate_rand_event(sources, tags, cnt, size)
        assert event.content is not None
        if cnt is not None:
            assert event.content == cnt
        else:
            assert len(event.content) >= size
        
        assert event.tags
        assert set(event.tags).issubset(set(tags))
        assert event.source
        assert event.source in sources


@mock.patch.object(Client, 'connect')
@mock.patch.object(Client, 'send_event')
@mock.patch.object(asyncio, 'get_event_loop')
def test_simulate_events(m_get_event_loop, m_send_event, m_connet):
    import threading
    import asyncio
    from collections import namedtuple
    
    _Namespace = namedtuple('Namespace', ['host', 'port', 'tags', 'sources', 'content',
                                          'content_size', 'delay'])
    
    loop = asyncio.new_event_loop()
    m_get_event_loop.return_value = loop
    
    args = _Namespace(host='localhost', port=11223, tags=['t1', 't2'], sources=['s1', 's2'],
                      content=None, content_size=150, delay=0.1)
    
    def fake_send_event(event):
        assert event.content
        assert len(event.content) >= 150
        assert event.tags
        assert set(event.tags).issubset({'t1', 't2'})
        assert event.source
        assert event.source in ['s1', 's2']
   
   
    m_send_event.side_effect = fake_send_event
    
    main_thread = threading.current_thread()

    def stop():
        from time import sleep
        sleep(0.5)
        for thr in threading.enumerate():
            if thr != main_thread and thr != threading.current_thread() and hasattr(thr, 'is_running'):
                thr.is_running = False
                thr.join()
        
        loop.call_soon_threadsafe(loop.stop)
            
    stop_thread = threading.Thread(target=stop)
    stop_thread.start()
    simulate_events(args)
    stop_thread.join()
    assert m_connet.call_count == 1
    assert m_send_event.call_count >= 4
   
   
    
    
