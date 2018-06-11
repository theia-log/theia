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

