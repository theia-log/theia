from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from os.path import getsize, isfile, isdir

class FileWatcher:

  def __init__(self, file_path):
    self.path = file_path
    self.handlers = []

  def on_change(self, handler):
    self.handlers.append(handler)

  def remove_handler(self, handler):
    self.handlers.remove(handler)

  def stop_watching(self):
    self.handlers.clear()

  def publish_change(self, diff):
    for handler in self.handlers:
      try:
        handler(diff)
      except e:
        pass

class WatchdogFileWatcher(FileWatcher):

  def __init__(self, file_path, enc="UTF-8"):
    super(WatchdogFileWatcher, self).__init__(file_path)
    self.observer = Observer()
    self.position = 0
    self.encoding = 'UTF-8'

    self._setup()

    wdwatcher = self

    class FileEventHandler(FileSystemEventHandler):

      def on_moved(self, event):
        wdwatcher.path = event.dest_path

      def on_created(self, event):
          wdwatcher.position = 0

      def on_deleted(self, event):
        pass

      def on_modified(self, event):
          diff = wdwatcher._get_diff()
          if diff is not None:
            wdwatcher.publish_change(diff.decode(wdwatcher.encoding))

    self.observer.schedule(FileEventHandler())
    self.observer.start()

  def _setup(self):
    if isfile(self.path):
      self.position = getsize(self.path)
    elif isdir(self.path):
      raise Exception('Not a file: %s' %self.path)

  def _get_diff(self):
    with open(self.path, 'rb') as f:
      f.seek(self.position)
      diff = f.read()
      self.position = f.tell()
      return diff



  def stop_watching(self):
    super(WatchdogFileWatcher, self).stop_watching()
    self.observer.stop()


class WatchDaemon:

  def __init__(self, tags=None):
    self.tags = tags or []
    self.watching = {}
    
  def stop(self):
    pass

  def watch(self, path):
    pass
