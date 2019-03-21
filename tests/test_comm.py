from theia.comm import Client, Server
from theia.model import Event, EventSerializer
import asyncio
from unittest import mock
from websockets import WebSocketClientProtocol as WebSocket
import websockets

@mock.patch.object(websockets, 'connect')
@mock.patch.object(WebSocket, 'recv')
@mock.patch.object(WebSocket, 'close')
def test_client_connect_and_close(m_close, m_recv, m_connect):
    from time import sleep
    evloop = asyncio.new_event_loop()
    
    
    async def fake_connect(url, loop):
        assert url == 'ws://localhost:1122/path'
        assert loop == evloop
        
        return WebSocket()
   
    async def fake_recv():
        await asyncio.sleep(100)
        return None
    
    
    def fake_close(code, reason):
        assert code == 1000
        assert reason == 'test-close'
    
    m_connect.side_effect = fake_connect
    m_recv.side_effect = fake_recv
    m_close.side_effect = fake_close
    
    client = Client(loop=evloop, host='localhost', port=1122, path='/path')

    client.connect()
    
    assert client.loop == evloop
    assert client.host == 'localhost'
    assert client.port == 1122
    assert client.secure == False
    assert client.path == '/path'
    assert client.serializer is not None
    assert client.websocket is not None
    assert client._is_open == True
    
    
    client.close(reason='test-close')
    assert client._is_open == False
    assert m_close.call_count == 1
    
    evloop.stop()
    for t in asyncio.Task.all_tasks(evloop):
        t.cancel()
        print('Task:', t, 'cancelled.')
   
    evloop.close()


@mock.patch.object(websockets, 'connect')
@mock.patch.object(WebSocket, 'recv')
@mock.patch.object(WebSocket, 'send')
def test_client_send(m_send, m_recv, m_connect):
    from time import sleep
    evloop = asyncio.new_event_loop()
    
    
    async def fake_connect(url, loop):
        assert url == 'ws://localhost:1122/path'
        assert loop == evloop
        
        return WebSocket()
   
    async def fake_recv():
        await asyncio.sleep(100)
        return None
    
    send_msgs = []
    async def fake_send(msg):
        print('[fake send]')
        send_msgs.append(msg)
        evloop.stop()
    
    
    m_connect.side_effect = fake_connect
    m_recv.side_effect = fake_recv
    m_send.side_effect = fake_send
    
    client = Client(loop=evloop, host='localhost', port=1122, path='/path')

    client.connect()
    
    assert client.loop == evloop
    assert client.host == 'localhost'
    assert client.port == 1122
    assert client.secure == False
    assert client.path == '/path'
    assert client.serializer is not None
    assert client.websocket is not None
    assert client._is_open == True
    
    client.send(message='TEST MESSAGE')
    
    evloop.run_forever()
    assert len(send_msgs) == 1
    
    for t in asyncio.Task.all_tasks(evloop):
        t.cancel()
        print('Task:', t, 'cancelled.')
   
    evloop.close()


@mock.patch.object(websockets, 'connect')
@mock.patch.object(WebSocket, 'recv')
@mock.patch.object(WebSocket, 'send')
def test_client_send_event(m_send, m_recv, m_connect):
    from time import sleep
    evloop = asyncio.new_event_loop()
    
    
    async def fake_connect(url, loop):
        assert url == 'ws://localhost:1122/path'
        assert loop == evloop
        
        return WebSocket()
   
    async def fake_recv():
        await asyncio.sleep(100)
        return None
    
    send_msgs = []
    async def fake_send(msg):
        print('[fake send]')
        send_msgs.append(msg)
        evloop.stop()
    
    
    m_connect.side_effect = fake_connect
    m_recv.side_effect = fake_recv
    m_send.side_effect = fake_send
    
    client = Client(loop=evloop, host='localhost', port=1122, path='/path')

    client.connect()
    
    assert client.loop == evloop
    assert client.host == 'localhost'
    assert client.port == 1122
    assert client.secure == False
    assert client.path == '/path'
    assert client.serializer is not None
    assert client.websocket is not None
    assert client._is_open == True
    
    client.send_event(Event(id='0001', timestamp=10, source='s-1', content='c-1', tags=['t']))
    
    evloop.run_forever()
    assert len(send_msgs) == 1
    assert 'id:0001' in send_msgs[0].decode('utf-8')
    
    for t in asyncio.Task.all_tasks(evloop):
        t.cancel()
        print('Task:', t, 'cancelled.')
   
    evloop.close()


def test_client_close_handlers():
    mock_close_handler = mock.MagicMock()
    mock_websocket = mock.MagicMock()
    
    client = Client(host='localhost', port=11223, loop=None)
    client.websocket = mock_websocket
    
    client.on_close(mock_close_handler)
    
    client._closed(code=1006, reason='unit test')
    
    assert mock_close_handler.called_once_with(mock_websocket, 1006, 'unit test')



def test_start_server():
    loop = asyncio.new_event_loop()

    ser = Server(loop=loop, host='localhost', port=11224)
    
    ser.start()
    
    assert ser.host == 'localhost'
    assert ser.port == 11224
    assert ser._started == True
    
    for t in asyncio.Task.all_tasks(loop):
        t.cancel()
    loop.stop()
    loop.close()


def test_start_and_stop_server():
    loop = asyncio.new_event_loop()

    ser = Server(loop=loop, host='localhost', port=11225)
    
    ser.start()
    
    assert ser.host == 'localhost'
    assert ser.port == 11225
    assert ser._started == True
    
    ser.stop()
    
    assert ser._started == True
    
    for t in asyncio.Task.all_tasks(loop):
        t.cancel()
    loop.stop()
    loop.close()

@mock.patch.object(WebSocket, 'recv')
@mock.patch.object(WebSocket, 'send')
def test_server_on_action(m_send, m_recv):
    loop = asyncio.new_event_loop()

    ser = Server(loop=loop, host='localhost', port=11226)
    
    serialized_event = EventSerializer().serialize(Event(id='00001',
                                                         timestamp=10,
                                                         source='src-1',
                                                         tags=['t-1', 't-2'],
                                                         content='content-1'))
    state = {}
    ws = WebSocket()
    
    async def fake_recv():
        if state.get('event_yield'):
            print('loop stop')
            loop.stop()
            await asyncio.sleep(10)
        else:
            state['event_yield'] = True
        return serialized_event

    m_recv.side_effect = fake_recv
    
    async def fake_send(msg):
        pass
    
    m_send.side_effect = fake_send
    
    def action_handler(path, message, websocket, resp):
        assert path == '/test-path'
        assert message == serialized_event
        assert websocket == ws
        assert resp is ''
        return 'RESP'
   
    on_action_mock = mock.MagicMock()
    on_action_mock.side_effect = action_handler
    
    
    
    ser.on_action('/test-path', on_action_mock)
    
    ser.start()
    
    assert ser.host == 'localhost'
    assert ser.port == 11226
    assert ser._started == True
    
    asyncio.ensure_future(ser._on_client_connection( ws, '/test-path'), loop=loop)
    loop.run_forever()
    for t in asyncio.Task.all_tasks(loop):
        t.cancel() # cancel the asyncio.wait
        print('[CANCEL]',t)
    loop.close()
    
    assert m_recv.call_count == 2 # once to get the message; second time to end the loop
    assert on_action_mock.call_count == 1
    assert m_send.call_count == 1
    m_send.assert_called_once_with('RESP')


@mock.patch.object(WebSocket, 'recv')
@mock.patch.object(WebSocket, 'send')
@mock.patch.object(WebSocket, 'close')
def test_server_close_handler(m_close, m_send, m_recv):
    from threading import Thread
    from time import sleep
    
    loop = asyncio.new_event_loop()

    ser = Server(loop=loop, host='localhost', port=11227)
    ser._stop_timeout = 0.1
    
    serialized_event = EventSerializer().serialize(Event(id='00001',
                                                         timestamp=10,
                                                         source='src-1',
                                                         tags=['t-1', 't-2'],
                                                         content='content-1'))
    state = {}
    websocket = WebSocket()
    
    def ws_close_handler(ws, path):
        assert ws == webocket
        assert path == 'test-path'
    
    mock_handler = mock.MagicMock()
    mock_handler.side_effect = ws_close_handler
    
    
    async def fake_recv():
        # at this point, the client websocket is registered.
        success = ser.on_websocket_close(websocket, mock_handler)
        assert success
        
        loop.call_soon(ser.stop)
        await asyncio.sleep(0.4)
        loop.call_soon(loop.stop)
        await asyncio.sleep(10)

    m_recv.side_effect = fake_recv
    
    async def fake_send(msg):
        pass
    
    m_send.side_effect = fake_send
    
    ser.start()
    
    assert ser.host == 'localhost'
    assert ser.port == 11227
    assert ser._started == True
    
    asyncio.ensure_future(ser._on_client_connection(websocket, 'test-path'), loop=loop)

    loop.run_forever()
    print(' *** loop done ***')
    for t in asyncio.Task.all_tasks(loop):
        t.cancel() # cancel the asyncio.wait
        print('[CANCEL]',t)
    loop.close()
    
    assert m_recv.call_count == 1
    assert mock_handler.call_count == 1
    assert m_close.call_count == 1
