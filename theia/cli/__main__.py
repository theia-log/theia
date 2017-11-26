from theia.cli.parser import get_parent_parser
from theia.cli.watcher import get_parser as get_watcher_parser, run_watcher
from theia.cli.collector import get_parser as get_collector_parser, run_collector
from theia.cli.query import get_parser as get_query_parser, run_query

parser = get_parent_parser('theia', 'Theia CLI')

subparsers = parser.add_subparsers(dest='command', title='command', help='CLI commands')
get_watcher_parser(subparsers)
get_collector_parser(subparsers)
get_query_parser(subparsers)

args = parser.parse_args()

if args.version:
    from theia.metadata import version
    from sys import exit
    print('theia', version)
    exit(0)

if args.command == 'watch':
    run_watcher(args)
elif args.command == 'collect':
    run_collector(args)
elif args.command == 'query':
    run_query(args)
