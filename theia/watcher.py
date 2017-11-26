from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from os.path import getsize, isfile, isdir, split as splitpath, realpath
from time import time, sleep
from uuid import uuid4

from theia.model import Event


class FileSource:
    def __init__(self, file_path, callback, enc='UTF-8', tags=None):
        self.path = file_path
        self.position = 0
        self.callback = callback
        self.enc = enc
        self.tags = tags or []
        self._setup()

    def modified(self):
        diff = self._get_diff()
        diff = diff.decode(self.enc)
        self.callback(diff, self.path, self.tags)

    def moved(self, dest_path):
        self.path = dest_path
        self.position = 0

    def created(self):
        self.position = 0

    def removed(self):
        pass

    def _get_diff(self):
        with open(self.path, 'rb') as f:
            f.seek(self.position)
            diff = f.read()
            self.position = f.tell()
            return diff

    def _setup(self):
        if isfile(self.path):
            self.position = getsize(self.path)
        elif isdir(self.path):
            raise Exception('Not a file: %s' % self.path)


class DirectoryEventHandler(FileSystemEventHandler):

    def __init__(self, handlers):
        self.handlers = handlers

    def _notify(self, event, *args):
        print('EVENT>', event, args)
        hnd = self.handlers.get(event)
        if hnd:
            hnd(*args)

    def on_moved(self, event):
        self._notify('moved', event.src_path, event.dest_path)

    def on_created(self, event):
        self._notify('created', event.src_path)

    def on_deleted(self, event):
        self._notify('deleted', event.src_path)

    def on_modified(self, event):
        self._notify('modified', event.src_path)


class SourcesDaemon:

    def __init__(self, observer, client, tags=None):
        self.sources = {}
        self.observer = observer
        self.client = client
        self.tags = tags or []
        self.dir_handler = DirectoryEventHandler(handlers={
            'moved': self._moved,
            'created': self._created,
            'deleted': self._deleted,
            'modified': self._modified
        })
        self.observer.start()

    def add_source(self, fpath, enc='UTF-8', tags=None):
        def callback(diff, srcpath, evtags):
            ts = time()
            ev = Event(id=str(uuid4()), source=fpath, timestamp=ts, tags=evtags, content=diff)
            self.client.send_event(ev)
            print(' > sent:', ev)

        fsrc = FileSource(fpath, callback, enc, tags)
        pdir, fname = self._split_path(fpath)
        files = self.sources.get(pdir)
        if not files:
            files = self.sources[pdir] = {}
            self.observer.schedule(self.dir_handler, pdir, recursive=False)
        if files.get(fname):
            return
        files[fname] = fsrc

    def remove_source(self, fpath):
        pdir, fname = self._split_path(fpath)
        files = self.sources.get(pdir)
        if files and files.get(fname):
            del files[fname]

    def _split_path(self, fpath):
        fpath = realpath(fpath)
        return splitpath(fpath)

    def _get_file_source(self, src_path):
        pdir, fname = self._split_path(src_path)
        files = self.sources.get(pdir)
        if files:
            return files.get(fname)

    def _moved(self, src_path, dest_src):
        pdir, fname = self._split_path(src_path)
        files = self.sources.get(pdir)
        if files and files.get(fname):
            fsrc = files[fname]
            del files[fname]
            ndir, nfname = self._split_path(dest_path)
            if not self.sources.get(ndir):
                self.sources[ndir] = {}
            self.sources[ndir][nfname] = fsrc
            fsrc.moved(dest_path)

    def _created(self, src_path):
        fsrc = self._get_file_source(src_path)
        if fsrc:
            fsrc.created()

    def _deleted(self, src_path):
        fsrc = self._get_file_source(src_path)
        if fsrc:
            fsrc.removed()

    def _modified(self, src_path):
        fsrc = self._get_file_source(src_path)
        if fsrc:
            fsrc.modified()


if __name__ == '__main__':
    from threading import Thread

    def run_daemon():
        daemon = SourcesDaemon(observer=Observer(), client=None, tags=['local', 'test-run'])

        daemon.add_source(fpath='/tmp/pajo', tags=['file'])

        while True:
            sleep(1)

    t = Thread(target=run_daemon)
    t.start()
    t.join()
