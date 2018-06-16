"""
-------------------
theia.cli.collector
-------------------

Theia collector command line interface script.
"""
import signal
from logging import getLogger
from theia.naivestore import NaiveEventStore
from theia.collector import Collector


log = getLogger(__name__)


def get_parser(subparsers):
    """Configures the subparser for the ``collect`` command.

    :param argparse.ArgumentParser subparser: subparser for commands.

    Returns :class:`argparse.ArgumentParser` confured for the ``collect`` command.
    """
    parser = subparsers.add_parser('collect', help='Collector server')

    parser.add_argument('-d', '--data-dir', dest='data_dir', help='Data store root directory')
    parser.add_argument('-U', '--db-url', dest='db_url', help='Database URL (SQLAlchemy form)',
                        default=None)
    parser.add_argument('--verbose', dest='store_verbose', action='store_true',
                        help='Make the EventStore to log more verbose output.')
    parser.add_argument('--rdbs-store', dest='rdbs_store', action='store_true',
                        help='Use RDBS EventStore instead of NaiveEventStore.' +
                        'The RDBS store keeps the events in a relational database.')

    return parser


def run_collector(args):
    """Runs the collector server.

    :param argparse.Namespace args: arguments to configure the
        :class:`theia.collector.Collector` instance.

    """
    store = None

    if args.rdbs_store:
        store = get_rdbs_store(args)
        if store:
            log.info('Using RDBS Event Store')
        else:
            log.warning('Unable to set up the RDBS Event Store. Will fall back to using Naive Event Store.')
    if not store:
        store = get_naive_store(args)
        log.info('Using Naive Event Store')

    collector = Collector(store=store, hostname=args.server_host, port=args.port)

    def stop_collector(sig, frame):
        """Signal handler that stops the collector.
        """
        log.info('Collector is shutting down.')
        collector.stop()

    signal.signal(signal.SIGHUP, stop_collector)
    signal.signal(signal.SIGINT, stop_collector)
    signal.signal(signal.SIGTERM, stop_collector)

    collector.run()


def _has_sqlalchemy():
    try:
        import sqlalchemy
    except:
        return False
    return True


def get_rdbs_store(args):
    """Creates and configures new :class:`theia.rdbs.RDBSEventStore` based on
    the arguments passed.

    :param argparse.Namespace args: arguments.

    """
    if not _has_sqlalchemy():
        log.info('SQLAlchemy is not present on your system. RDBSEventStore cannot work without it.')
        return None

    from theia.rdbs import create_store

    if not args.db_url:
        raise Exception('No Database URL')

    return create_store(db_url=args.db_url, verbose=args.store_verbose)


def get_naive_store(args):
    """Creates and configures new :class:`theia.naivestore.NaiveEventStore`
    based on the arguments passed.

    :param argparse.Namespace args: arguments.

    """

    if not args.data_dir:
        raise Exception('No data directory specified')

    return NaiveEventStore(root_dir=args.data_dir)
