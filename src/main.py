import sys
import traceback
from PyQt5.QtWidgets import QApplication

from mainwindow import MainWindow


class Tsuna(QApplication):
  def __init__(self):
    super().__init__(sys.argv)
    self.window = MainWindow()
    self.window.show()


if __name__ == '__main__':
  import log
  app = Tsuna()
  log.set_app(app)

  def excepthook(exctype, value, tb):
    log.log('%s %s\n%s' % (exctype, value, ''.join(traceback.format_tb(tb))), 'error')
  sys.excepthook = excepthook

  sys.exit(app.exec_())
