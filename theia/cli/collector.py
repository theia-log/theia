from theia.cli.parser import get_parent_parser as parent_parser

def get_parser(subparsers):
  parser = subparsers.add_parser('collect', help='Collector server')
  
  parser.add_argument('-d', '--data-dir', dest='data_dir', help='Data store root directory')
  
  return parser


def run_collector(args):
  from theia.naivestore import NaiveEventStore
  from theia.collector import Collector
  
  
  store = NaiveEventStore(root_dir=args.data_dir)
  
  collector = Collector(store=store, hostname=args.server_host, port=args.port)
  
  collector.run()
  
  