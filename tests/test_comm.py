from theia.comm import Client
from theia.model import Event
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
