import sys, os
from PyQt5.QtWidgets import QApplication
import pyqtgraph as pg

import log


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

  pg.setConfigOptions(antialias=True)

  app = Tsuna()
  log.setApp(app)
  sys.exit(app.exec_())
