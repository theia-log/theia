from theia.comm import Client
from theia.model import Event, EventSerializer

from random import randint
from uuid import uuid4
from datetime import datetime
from threading import Thread

import argparse
import lorem
import asyncio
import time
import random


def get_parser():
    parser = argparse.ArgumentParser(prog='theia.cli.simulate',
                                     description='Simulate events (debugging)')

    parser.add_argument('-H', '--host', default='localhost', dest='host', help='Collector host')
    parser.add_argument('-p', '--port', default=6433, dest='port', help='Collector port')
    parser.add_argument('-t', nargs='*', dest='tags', help='Set of tags to choose from')
    parser.add_argument('-s', nargs='*', dest='sources', help='Set of event sources to choose from')
    parser.add_argument('-c', dest='content', default=None,
                        help='Use this event content instead of random content.')
    parser.add_argument('--content-size', dest='content_size', type=int,
                        default=None, help='Size of content (approximately)')
    parser.add_argument('--delay', dest='delay', default=1.0, type=float,
                        help='Delay between event in seconds')

    return parser


def generate_content(content=None, size=None):
    if content is not None:
        return content

    if size is None:
        return lorem.sentence()

    content = lorem.sentence()

    while len(content) < size:
        content = content + ' ' + lorem.sentence()

    return content


def generate_rand_items(items, default):
    if len(items) == 0:
        return [default]

    if len(items) == 1:
        return items

    rn = randint(1, len(items))

    rndi = [n for n in items]
    random.shuffle(rndi)

    return rndi[0:rn]


def generate_rand_event(sources, tags, content, cnt_size):
    source = sources[randint(0, len(sources) - 1)]
    e = Event(id=str(uuid4()), source=source, timestamp=datetime.now().timestamp(),
              tags=generate_rand_items(tags, 'tag-4'), content=generate_content(content, cnt_size))
    return e


def simulate_events(args):
    loop = asyncio.get_event_loop()
    client = Client(host=args.host, port=args.port, path='/event', loop=loop)

    print('tags', args.tags)
    client.connect()

    ser = EventSerializer()
    tags = [args.tags] if isinstance(args.tags, str) else args.tags

    def send_event():
        e = generate_rand_event(args.sources, tags, args.content, args.content_size)
        client.send_event(e)
        print(ser.serialize(e).decode('UTF-8'))
        print()

    def send_all():
        while True:
            send_event()
            time.sleep(args.delay)

    t = Thread(target=send_all)
    t.start()
    loop.run_forever()


if __name__ == '__main__':
    parser = get_parser()

    args = parser.parse_args()

    simulate_events(args)
