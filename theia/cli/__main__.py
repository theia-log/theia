from theia.cli.parser import get_parent_parser
from theia.cli.watcher import get_parser as get_watcher_parser, run_watcher
from theia.cli.collector import get_parser as get_collector_parser, run_collector

parser = get_parent_parser('theia', 'Theia CLI')

subparsers = parser.add_subparsers(dest='command', title='command', help='CLI commands')
get_watcher_parser(subparsers)
get_collector_parser(subparsers)

args = parser.parse_args()

print(args)

if args.command == 'watch':
  run_watcher(args)
elif args.command == 'collect':
  run_collector(args)