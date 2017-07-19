import sys, os
from PyQt5.QtWidgets import QApplication

import log


class Tsuna(QApplication):
  def __init__(self, exedir):
    super().__init__(sys.argv)
    self.exedir = exedir
    from mainwindow import MainWindow
    self.window = MainWindow(os.path.join(exedir, 'tuna.conf.json'))
    self.window.show()


if __name__ == '__main__':
  exedir = os.path.dirname(os.path.realpath(sys.argv[0]))

  import logging, log
  logging.basicConfig(level=logging.DEBUG)
  log.setup()

  app = Tsuna(exedir)
  log.setApp(app)
  sys.exit(app.exec_())
