"""
-------------
theia.watcher
-------------

File watcher.

Watches files and directories for changes and emits the chnages as events.
"""
from os.path import getsize, isfile, isdir, split as splitpath, realpath
from time import time
from uuid import uuid4

from watchdog.events import FileSystemEventHandler

from theia.model import Event


class FileSource:
    """Represents a source of events.

    The underlying file that is being watched does not have to exist at the
    moment of creation of this :class:`FileSource`.

    :param str file_path: the path to the file to be watched.
    :param function callback: the callback handler to be executed when the file is
        changed. The callback is called with the difference, the path to the
        file and the list of tags for this source. The method signature looks
        like this:

        .. code-block:: python

            def callback(diff, path, tags):
                pass

        where:

        * ``diff``, ``str`` is the difference from the last state of the file.
          Usually this is the content of the emitted event.
        * ``path``, ``str`` is the path to the file that has changed. Usually
          this is the ``source`` property of the event.
        * ``tags``, ``list`` is the list of tags associated with this event
          source.

    :param str enc: the file encoding. If not specified, ``UTF-8`` is assumed.
    :param list tags: list of tags associated with this source.

    """
    def __init__(self, file_path, callback, enc='UTF-8', tags=None):
        self.path = file_path
        self.position = 0
        self.callback = callback
        self.enc = enc
        self.tags = tags or []
        self._setup()

    def modified(self):
        """Triggers an execution of the callbacks when the file has been
        modified.

        Loads the difference from the source file and calls the registered
        callbacks.
        """
        diff = self._get_diff()
        diff = diff.decode(self.enc)
        self.callback(diff, self.path, self.tags)

    def moved(self, dest_path):
        """Called when the source file has been moved to another location.

        :param str dest_path: the target location of the file after the move.
        """
        self.path = dest_path

    def created(self):
        """Called when the file has actually been created. Does not trigger the
        callbacks.
        """
        self.position = 0

    def removed(self):
        """Called when the file has been removed. Does not triggers the
        callbacks.
        """
        pass

    def _get_diff(self):
        with open(self.path, 'rb') as source_file:
            source_file.seek(self.position)
            diff = source_file.read()
            self.position = source_file.tell()
            return diff

    def _setup(self):
        if isfile(self.path):
            self.position = getsize(self.path)
        elif isdir(self.path):
            raise Exception('Not a file: %s' % self.path)


class DirectoryEventHandler(FileSystemEventHandler):
    """Implements :class:`watchdog.events.FileSystemEventHandler` and is used
    with the underlying :class:`watchdog.observers.Observer`.

    Reacts on events triggered by the watchdog Observer and passes down to the
    registered handlers.

    The handlers are registered when creating the instance as a constructor
    argument. They must be specified as ``dict`` whose keys (``str``) are the
    names of the events and the entries are the event handlers themselves.

    An example of creating new :class:`DirectoryEventHandler`:

    .. code-block:: python

        def on_file_moved(src_path, dest_path):
            print("File has moved", src_path, "->", dest_path)

        event_handler = DirectoryEventHandler(handlers={
            "moved": on_file_moved
        })

    The following events are supported:

    * ``moved`` - handles the move of a file to another location. The handler
        takes two arguments: the source path and the destination path. The
        method signature looks like this:

        .. code-block:: python

            def moved_handler(src_path, dest_path):
                pass

    * ``created`` - handles file creation. The handler takes one argument: the
        path of the created file.

        .. code-block:: python

            def created_handler(file_path):
                pass

    * ``modified`` - handles file modification. The handler takes one argument:
        the path of the modified file.

        .. code-block:: python

            def created_handler(file_path):
                pass

    * ``deleted`` - handles file deletion. The handler takes one argument: the
        path of the deleted file.

        .. code-block:: python

            def created_handler(file_path):
                pass

    :param dict handlers: a ``dict`` of handlers for specific events.

    """
    def __init__(self, handlers):
        self.handlers = handlers

    def _notify(self, event, *args):
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
    """Daemon that watches multiple sources for events.

    Uses :mod:`watchdog` to monitor files and directories for changes. This
    defaults to using ``inotify`` kernel subsystem on Linux systems, ``kqueue``
    on MacOSX and BSD-like systems and ``ReadDirectoryChangesW`` on Windows.

    :param watchdog.observers.Observer observer: an instance of the
        :class:`watchdog.observers.Observer` to be used.
    :param theia.comm.Client client: a client to a theia collector
        server.
    :param list tags: initial list of default tags that are appended to every
        file source watched by this daemon.

    """
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
        """Add source of events to be watched by this daemon.

        The path will be added as a file source and a list of tags will be
        associated with it. The default list of tags will be added to provided
        tags.

        :param str fpath: the path of the file to be watched.
        :param str enc: the file encoding. By default ``UTF-8`` is assumed.
        :param list tags: list of tags to be added to the events generated
            by this file source.

        """
        def callback(diff, _, evtags):
            """Handle an event from a :class:`FileSource` and emit an event
                to the collector server.
            """
            timestamp = time()
            event = Event(id=str(uuid4()), source=fpath, timestamp=timestamp,
                          tags=evtags, content=diff)
            self.client.send_event(event)

        fsrc = FileSource(fpath, callback, enc, self._merge_tags(tags))
        pdir, fname = self._split_path(fpath)
        files = self.sources.get(pdir)
        if not files:
            files = self.sources[pdir] = {}
            self.observer.schedule(self.dir_handler, pdir, recursive=False)
        if files.get(fname):
            return
        files[fname] = fsrc

    def _merge_tags(self, tags):
        if self.tags is None and tags is None:
            return None
        return (self.tags or []) + (tags or [])

    def remove_source(self, fpath):
        """Remove this path from the list of file event sources.

        All associated watchers and handlers are removed as well.

        :param str fpath: the path of the file to be removed from the watching
            list.

        """
        pdir, fname = self._split_path(fpath)
        files = self.sources.get(pdir)
        if files and files.get(fname):
            del files[fname]
        if self.sources.get(pdir) is not None and not self.sources[pdir]:
            del self.sources[pdir]

    @staticmethod
    def _split_path(fpath):
        fpath = realpath(fpath)
        return splitpath(fpath)

    def _get_file_source(self, src_path):
        pdir, fname = self._split_path(src_path)
        files = self.sources.get(pdir)
        if files:
            return files.get(fname)
        return None

    def _moved(self, src_path, dest_path):
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
