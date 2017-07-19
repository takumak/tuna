import sys
import logging
import traceback
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
      self.app.window.log_(msg, record.levelno>=logging.ERROR)
    else:
      self.log.append(msg)

  def setApp(self, app):
    self.app = app
    for msg in self.log:
      self.app.window.log_(msg)
      self.log = None

def logException(exc_type, exc_value, exc_traceback, level=logging.ERROR):
  tb = ''.join(traceback.format_tb(exc_traceback))
  logging.log(level, '%s %s\n%s' % (exc_type, exc_value, tb))

def warnException():
  exc_type, exc_value, exc_traceback = sys.exc_info()
  logException(*sys.exc_info(), level=logging.WARNING)

def setApp(app):
  global __handler
  __handler.setApp(app)

def setup():
  global __handler
  __handler = LogHandler()
  logging.getLogger().addHandler(__handler)
  sys.excepthook = logException
