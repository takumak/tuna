import logging
import html
from datetime import datetime


class LogFormatter(logging.Formatter):
  colors = {
    logging.DEBUG:    '#888',
    logging.INFO:     '#000',
    logging.WARN:     '#a80',
    logging.ERROR:    '#800',
    logging.CRITICAL: '#800'
  }

  def format(self, record):
    msg = super().format(record)
    fmt = '<div style="color:%s;font-family:monospace;white-space:pre">%s</div><br>'
    return fmt % (self.colors[record.levelno], html.escape(msg))


class LogHandler(logging.Handler):
  def __init__(self):
    super().__init__()
    self.setFormatter(LogFormatter('%(asctime)s [%(name)s] %(message)s'))
    self.log = []
    self.app = None

  def emit(self, record):
    msg = self.format(record)
    if self.app:
      self.app.window.log_(msg)
    else:
      self.log.append(msg)

  def setApp(self, app):
    self.app = app
    for msg in self.log:
      self.app.window.log_(msg)
      self.log = None


def set_app(app):
  global __handler
  __handler.setApp(app)

def setup():
  global __handler
  __handler = LogHandler()
  logging.getLogger().addHandler(__handler)
