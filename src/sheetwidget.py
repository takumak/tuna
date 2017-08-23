import logging
from PyQt5.QtCore import pyqtSignal, QPoint
from PyQt5.QtGui import QValidator
from PyQt5.QtWidgets import \
  QWidget, QTableWidgetItem, QGridLayout, QLabel, \
  QPushButton, QMenu

import log
from commonwidgets import *
from functions import getTableColumnLabel


class SheetWidget(QWidget):
  copyInputRequested = pyqtSignal(str, bool)

  def __init__(self, sheet):
    super().__init__()
    self.sheet = sheet

    vbox = VBoxLayout()
    self.setLayout(vbox)

    self.inputMenu = QMenu()
    self.inputMenu.addAction(
      'Copy to sibling sheets',
      lambda: self.copyInputRequested.emit(self.inputMenu.target, False))
    self.inputMenu.addAction(
      'Copy to ALL sheets',
      lambda: self.copyInputRequested.emit(self.inputMenu.target, True))


    grid = QGridLayout()
    grid.addWidget(QLabel('X'), 0, 0)
    grid.addWidget(sheet.xFormula.getWidget(), 0, 1)
    grid.addWidget(QLabel('Y'), 1, 0)
    grid.addWidget(sheet.yFormula.getWidget(), 1, 1)
    grid.addWidget(QLabel('X range'), 2, 0)
    grid.addWidget(sheet.xRange.getWidget(), 2, 1)

    for i, name in enumerate(('x', 'y', 'xrange')):
      btn = QPushButton('\u2630')
      btn.setStyleSheet('padding:3')
      f = (lambda btn, n: (lambda *a: self.showInputMenu(btn, n)))(btn, name)
      btn.clicked.connect(f)
      grid.addWidget(btn, i, 2)

    grid.setColumnStretch(1, 1)
    vbox.addLayout(grid)


    self.table = TableWidget()
    self.table.setColumnCount(sheet.colCount())
    self.table.setRowCount(sheet.rowCount())
    vbox.addWidget(self.table)

    for c in range(sheet.colCount()):
      self.table.setHorizontalHeaderItem(c, QTableWidgetItem(getTableColumnLabel(c)))
      for r in range(sheet.rowCount()):
        self.table.setItem(r, c, QTableWidgetItem(str(self.sheet.getValue(r, c))))

  def showInputMenu(self, btn, target):
    self.inputMenu.target = target
    self.inputMenu.exec_(btn.mapToGlobal(QPoint(0, btn.rect().height())))
