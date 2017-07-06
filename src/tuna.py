import sys, os
import traceback
from PyQt5.QtWidgets import QApplication


class Tsuna(QApplication):
  def __init__(self, exedir):
    super().__init__(sys.argv)
    self.exedir = exedir
    from mainwindow import MainWindow
    self.window = MainWindow(os.path.join(exedir, 'tuna.toml'))
    self.window.show()


if __name__ == '__main__':
  exedir = os.path.dirname(os.path.realpath(sys.argv[0]))

  import logging, log
  logging.basicConfig(level=logging.DEBUG)
  log.setup()

  app = Tsuna(exedir)
  log.set_app(app)

  def excepthook(exctype, value, tb):
    logging.error('%s %s\n%s' % (exctype, value, ''.join(traceback.format_tb(tb))))
  sys.excepthook = excepthook

  sys.exit(app.exec_())
