import sys
import traceback
from PyQt5.QtWidgets import QApplication


class Tsuna(QApplication):
  def __init__(self):
    super().__init__(sys.argv)
    from mainwindow import MainWindow
    self.window = MainWindow()
    self.window.show()


if __name__ == '__main__':
  import logging, log
  logging.basicConfig(level=logging.DEBUG)
  log.setup()

  app = Tsuna()
  log.set_app(app)

  def excepthook(exctype, value, tb):
    logging.error('%s %s\n%s' % (exctype, value, ''.join(traceback.format_tb(tb))))
  sys.excepthook = excepthook

  sys.exit(app.exec_())
