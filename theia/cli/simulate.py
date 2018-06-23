"""
------------------
theia.cli.simulate
------------------

Event simulation tool.
"""


import asyncio
import time
from random import randint, shuffle
from uuid import uuid4
from datetime import datetime
from threading import Thread
import argparse

import lorem

from theia.comm import Client
from theia.model import Event, EventSerializer


def get_parser():
    """Configure and instantiate the argument parser for the simulation tool.

    :returns: configured :class:`argparse.ArgumentParser`.
    """
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
    """Generate random  (lorem-ipsum style) content.

    If ``content`` is provided, just passes through. Otherwise generates 'lorem-ipsum'
    style random content that is of about the provided ``size``. If no size is given,
    then it returns just one sentence.

    :param str content: optional, if given, the content to be returned.
    :param int size: optional, the size of the generated content. If not provided,
        then only one sentence is returned. If provided, then generates sentences
        with total size >= ``size``. Always generates full sentences.

    :returns: ``str``, the generated content.
    """
    if content is not None:
        return content

    if size is None:
        return lorem.sentence()

    content = lorem.sentence()

    while len(content) < size:
        content = content + ' ' + lorem.sentence()

    return content


def generate_rand_items(items, default):
    """Generates a random subset (``list``) of the provided list of items.

    The size of the subset is at least one, and at most is the whole ``items``
    list.
    If no items provided, then returns a list of just one item - the ``default``
    one.

    The order of the items in the subset is randomized as well.

    :param list items: the list of items to choose from.
    :param default: the default item to choose if no list of items is provided.

    :returns: :class:`list` randomized subset of the items list.
    """
    if not items:
        return [default]

    if len(items) == 1:
        return items

    rnd_size = randint(1, len(items))

    rndi = [n for n in items]
    shuffle(rndi)

    return rndi[0:rnd_size]


def generate_rand_event(sources, tags, content, cnt_size):
    """Generate random event from the given choices for sources, tags and content.

    :param list sources: list of choices for sources. One random source will be
        chosen from the list.
    :param list tags: list of choices for tags. Random subset with random order
        and size greater than one will be chosen from the given list of tags.
    :param str content: if not ``None``, that content will be used. If ``None``,
        random content will be generated.
    :param int cnt_size: generate content of at least this size. The size of the
        generated content may be grater (the content always contains full sentences)
        but it will never be less than ``cnt_size``.

    :returns: a random :class:`theia.model.Event` generated from the given choices
        values.
    """
    source = sources[randint(0, len(sources) - 1)]
    return Event(id=str(uuid4()), source=source, timestamp=datetime.now().timestamp(),
                 tags=generate_rand_items(tags, 'tag-4'),
                 content=generate_content(content, cnt_size))


def simulate_events(args):
    """Connects and generates random events.

    The events are generated according to the given arguments.

    :param argparse.Namespace args: the parsed arguments passed to the program.

    """
    loop = asyncio.get_event_loop()
    client = Client(host=args.host, port=args.port, path='/event', loop=loop)

    client.connect()

    ser = EventSerializer()
    tags = [args.tags] if isinstance(args.tags, str) else args.tags

    def send_event():
        """Generate and send a single event.
        """
        event = generate_rand_event(args.sources, tags, args.content, args.content_size)
        client.send_event(event)
        print(ser.serialize(event).decode('UTF-8'))
        print()

    def send_all():
        """Generate and send events continuously.
        """
        while True:
            send_event()
            time.sleep(args.delay)

    sender_thread = Thread(target=send_all)
    sender_thread.start()
    loop.run_forever()


def run_simulate_events():
    """Run the simulation of events.
    """
    parser = get_parser()

    args = parser.parse_args()

    simulate_events(args)



if __name__ == '__main__':
    run_simulate_events()
