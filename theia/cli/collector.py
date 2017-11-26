from theia.cli.parser import get_parent_parser as parent_parser
from theia.naivestore import NaiveEventStore
from theia.collector import Collector
import signal


def get_parser(subparsers):
    parser = subparsers.add_parser('collect', help='Collector server')

    parser.add_argument('-d', '--data-dir', dest='data_dir', help='Data store root directory')

    return parser


def run_collector(args):
    store = NaiveEventStore(root_dir=args.data_dir)

    collector = Collector(store=store, hostname=args.server_host, port=args.port)

    def stop_collector(sig, frame):
        print('Collector is shutting down.')
        collector.stop()

    signal.signal(signal.SIGHUP, stop_collector)
    signal.signal(signal.SIGINT, stop_collector)
    signal.signal(signal.SIGTERM, stop_collector)

    collector.run()
