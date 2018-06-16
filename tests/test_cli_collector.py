from theia.cli.collector import get_parser, get_rdbs_store, run_collector
from theia.collector import Collector
import theia.cli.collector
import signal
from argparse import ArgumentParser
from unittest import mock
from collections import namedtuple
import theia.rdbs


def test_get_parser():
    parent_parser = ArgumentParser(prog='test')
    
    subparsers = parent_parser.add_subparsers(dest='command', title='command',
                                              help='CLI commands')
    
    parser = get_parser(subparsers)
    
    args = parser.parse_args(args=['-d', '/data-dir'])
    assert args.data_dir == '/data-dir'
    
    args = parser.parse_args(args=['--data-dir', '/data-dir'])
    assert args.data_dir == '/data-dir'
    
    args = parser.parse_args(args=['-U', 'db_url'])
    assert args.db_url == 'db_url'
    
    args = parser.parse_args(args=['--db-url', 'db_url'])
    assert args.db_url == 'db_url'
    
    args = parser.parse_args(args=['--verbose'])
    assert args.store_verbose is True
    
    args = parser.parse_args(args=['--rdbs-store'])
    assert args.rdbs_store is True


@mock.patch.object(theia.rdbs, 'create_store')
def test_get_rdbs_store(m_create_store):
    Namespace = namedtuple('argparse_Namespace', ['db_url', 'store_verbose'])
    
    args = Namespace(db_url='db://url', store_verbose=True)
    
    get_rdbs_store(args)
    
    assert m_create_store.called_once_with(args.db_url, args.store_verbose)

    # try not using the db url
    error = False
    try:
        get_rdbs_store(Namespace())
    except:
        error = True
    
    assert error is True

@mock.patch.object(signal, 'signal')
@mock.patch.object(Collector, 'run')
@mock.patch.object(Collector, 'stop')
@mock.patch.object(theia.cli.collector, 'get_rdbs_store')
def test_run_collector_rdbs_store(m_get_rdbs_store, m_stop, m_run, m_signal):
    from theia.storeapi import EventStore
    
    m_get_rdbs_store.return_value = EventStore()
    
    Namespace = namedtuple('argparse_Namespace', ['db_url', 'store_verbose',
                                                   'rdbs_store','server_host',
                                                   'port'])
    
    state = {}
    
    def fake_signal(sig, handler):
        assert sig in [1, 2, 15]
        state['signal_handler'] = handler
    
    m_signal.side_effect = fake_signal
    
    args = Namespace(db_url='db://url', store_verbose=True, rdbs_store=True,
                     server_host='localhost', port=9089)
    
    run_collector(args)
    
    assert m_get_rdbs_store.called_once_with('db://url', True)
    assert m_run.call_count == 1
    assert m_signal.call_count == 3
    
    assert state.get('signal_handler')
    
    state['signal_handler'](15, None)
    
    assert m_stop.call_count == 1


@mock.patch.object(signal, 'signal')
@mock.patch.object(Collector, 'run')
@mock.patch.object(Collector, 'stop')
@mock.patch.object(theia.cli.collector, 'get_naive_store')
def test_run_collector_naive_store(m_get_naive_store, m_stop, m_run, m_signal):
    Namespace = namedtuple('argparse_Namespace', ['data_dir', 'store_verbose', 'rdbs_store',
                                                  'server_host', 'port'])
    
    mock_store = mock.MagicMock()
    m_get_naive_store.return_value = mock_store
    state = {}
    
    def fake_signal(sig, handler):
        assert sig in [1, 2, 15]
        state['signal_handler'] = handler
    
    m_signal.side_effect = fake_signal
    
    args = Namespace(data_dir='/tmp/data', store_verbose=True, rdbs_store=False,
                     server_host='localhost', port=9089)
    
    run_collector(args)
    
    assert m_get_naive_store.called_once_with(args)
    assert m_run.call_count == 1
    assert m_signal.call_count == 3
    
    assert state.get('signal_handler')
    
    state['signal_handler'](15, None)
    
    assert m_stop.call_count == 1
    
