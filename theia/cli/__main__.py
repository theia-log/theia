from theia.cli.parser import get_parent_parser
from theia.cli.watcher import get_parser as get_watcher_parser, run_watcher

parser = get_parent_parser('theia', 'Theia CLI')

get_watcher_parser(parser.add_subparsers(dest='command', title='command', help='CLI commands'))

args = parser.parse_args()

print(args)

if args.command == 'watch':
  run_watcher(args)
