from theia.cli.parser import get_parent_parser as parent_parser
from theia.query import Query
import asyncio
from theia.model import EventParser
from io import BytesIO

def get_parser(subparsers):
  parser = subparsers.add_parser('query', help='Query for events')
  
  parser.add_argument('-l', '--live', action='store_true', dest='live', help='Filter events in real time (live).')
  
  parser.add_argument('--id', dest='f_id', metavar='PATTERN', default=None, help='Filter by event id')
  parser.add_argument('-s', '--source', dest='f_source', metavar='PATTERN', default=None, help='Filter by event source')
  parser.add_argument('-a', '--after', dest='f_after', metavar='TIMESTAMP', default=0, type=int, help='Match events after this timestamp')
  parser.add_argument('-b', '--before', dest='f_before', metavar='TIMESTAMP', default=0, type=int, help='Match events before this timestamp')
  parser.add_argument('-c', '--content', dest='f_content', metavar='PATTERN', default=None, help='Match event content')
  parser.add_argument('-t', '--tags', nargs='*', dest='f_tags', metavar='PATTERN', help='Match any of the tags')

def run_query(args):
  loop = asyncio.get_event_loop()
  query = Query(host=args.server_host, port=args.port, loop=loop)
  
  cf = {}
  if args.f_source:
    cf['source'] = args.f_source
  if args.f_id:
    cf['id'] = args.f_id
  if args.f_after:
    cf['start'] = args.f_after
  if args.f_before:
    cf['end'] = args.f_before
  if args.f_content:
    cf['content'] = args.f_content
  if args.f_tags:
    cf['tags'] = args.f_tags
  
  
  result = None
  parser = EventParser('UTF-8')
  fmt = '{timestamp} [{source}] {tags}: {content}'
  
  def printev(evdata):
    if isinstance(evdata, str):
      print(evdata)
      return
    try:
      ev = parser.parse_event(BytesIO(evdata))
      print(fmt.format(**ev.__dict__))
    except Exception as e:
      print('> Failed to show event', e)
      try:
        print('Value received: ', evdata.decode('UTF-8'))
      except:
        print('Raw data:', evdata)
    
  if args.live:
    result = query.live(cf, printev)
  else:
    result = query.find(cf, printev)
  print('loop forever')
  loop.run_forever()