from theia.cli.parser import get_parent_parser as parent_parser


def get_parser(subparsers):
  parser = subparsers.add_parser('query', help='Query for events')
  
  parser.add_argument('-l', '--live', action='store_true', dest='live', help='Filter events in real time (live).')
  
  parser.add_argument('--id', dest='f_id', metavar='PATTERN', default=None, help='Filter by event id')
  parser.add_argument('-s', '--source', dest='f_source', metavar='PATTERN', default=None, help='Filter by event source')
  parser.add_argument('-a', '--after', dest='f_after', metavar='TIMESTAMP', default=0, type=int, help='Match events after this timestamp')
  parser.add_argument('-b', '--before', dest='f_before', metavar='TIMESTAMP', default=0, type=int, help='Match events before this timestamp')
  parser.add_argument('-c', '--content', dest='f_content', metavar='PATTERN', default=None, help='Match event content')
  