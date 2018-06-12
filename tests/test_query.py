from unittest import mock
from theia.query import Query, ResultHandler
from theia.comm import Client

@mock.patch.object(Client, 'close')
@mock.patch.object(Client, 'is_open')
def test_result_handler_cancel(m_is_open, m_close):
    m_is_open.return_value = True
    
    rh = ResultHandler(client=Client(loop=None, host=None, port=None))
    
    rh.cancel()
    
    assert m_is_open.call_count == 1
    assert m_close.call_count == 1


def test_result_handler_when_closed():
    rh = ResultHandler(client=Client(loop=None, host=None, port=None))
    
    def closed_handler(*args, **kwargs):
        pass
    
    rh.when_closed(closed_handler)
    
    assert rh._close_handlers
    assert closed_handler in rh._close_handlers


@mock.patch.object(Client, 'close')
@mock.patch.object(Client, 'on_close')
@mock.patch.object(Client, 'is_open')
def test_assert_result_handler_closed_handlers_called(m_is_open, m_on_close, m_close):
    m_is_open.return_value = True
    
    handlers = []
    
    def fake_client_close():
        for hnd in handlers:
            hnd(None, 1006, 'server stop')
    
    m_close.side_effect = fake_client_close
    
    def fake_client_on_close(handler):
        handlers.append(handler)
    
    closed_handler = mock.MagicMock()
    
    client = Client(loop=None, host=None, port=None)
    
    rh = ResultHandler(client=client)
    
    rh.when_closed(closed_handler)
    
    rh.cancel()
    
    assert closed_handler.called_once_with(client, 1006, 'server stop')


@mock.patch.object(Client, 'on_close')
@mock.patch.object(Query, '_connect_and_send')
def test_query_find(m_connect_and_send, m_on_close):
    query = Query(host='localhost', port=11223)
    
    def callback(*args):
        pass
    rh = ResultHandler(client=Client(loop=None, host=None, port=None))
    def fake_connect_and_send(*args, **kwargs):
        return rh
    
    m_connect_and_send.side_effect = fake_connect_and_send
    
    criteria = {'id': 'event-1'}
    
    result = query.find(criteria, callback)
    assert result is not None
    assert result == rh
    assert m_connect_and_send.called_once_with('/find', criteria, callback)


@mock.patch.object(Client, 'on_close')
@mock.patch.object(Query, '_connect_and_send')
def test_query_live(m_connect_and_send, m_on_close):
    query = Query(host='localhost', port=11223)
    
    def callback(*args):
        pass
    rh = ResultHandler(client=Client(loop=None, host=None, port=None))
    def fake_connect_and_send(*args, **kwargs):
        return rh
    
    m_connect_and_send.side_effect = fake_connect_and_send
    
    criteria = {'id': 'event-1'}
    
    result = query.find(criteria, callback)
    assert result is not None
    assert result == rh
    assert m_connect_and_send.called_once_with('/live', criteria, callback)


@mock.patch.object(Client, 'connect')
@mock.patch.object(Client, 'on_close')
@mock.patch.object(Client, 'send')
def test_query_connect_and_send(m_send, m_on_close, m_connect):
    close_callbacks = []
    
    def fake_on_close(callback):
        close_callbacks.append(callback)
    
    m_on_close.side_effect = fake_on_close

    query = Query(host='localhost', port=11223)
    
    
    
    criteria = {'id': 'event-1'}
    def callback(*args):
        pass
    result = query._connect_and_send('/endpoint', criteria, callback)
    
    assert result is not None
    assert isinstance(result, ResultHandler)
    assert len(query.connections) == 1
    assert m_connect.call_count == 1
    assert m_send.call_count == 1
    assert m_on_close.call_count == 2 # one for the Query, one for the ResultHander
    assert len(close_callbacks) == 2  # first one from the Query, second one from the ResultHandler
    
    # call the close handler to simulate client close
    close_callbacks[0](None, None, None)
    assert len(query.connections) == 0
    
