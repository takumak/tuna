import logging
from PyQt5.QtCore import pyqtSignal, QPoint
from PyQt5.QtGui import QValidator
from PyQt5.QtWidgets import \
  QWidget, QTableWidgetItem, QGridLayout, QLabel, \
  QPushButton, QMenu

import log
from commonwidgets import TableWidget, VBoxLayout, ErrorCheckEdit
from functions import getTableColumnLabel


class SheetWidget(QWidget):
  copyFormulaRequested = pyqtSignal(str)

  def __init__(self, sheet):
    super().__init__()
    self.sheet = sheet

    vbox = VBoxLayout()
    self.setLayout(vbox)

    self.formulaMenu = QMenu()
    self.formulaMenu.addAction(
      'Copy to sibling sheets',
      lambda: self.copyFormulaRequested.emit(self.formulaMenu.xy))

    self.xMenuButton = QPushButton('\u2630')
    self.xMenuButton.setStyleSheet('padding:3')
    self.xMenuButton.clicked.connect(lambda *a: self.showFormulaMenu('x'))
    self.yMenuButton = QPushButton('\u2630')
    self.yMenuButton.setStyleSheet('padding:3')
    self.yMenuButton.clicked.connect(lambda *a: self.showFormulaMenu('y'))

    grid = QGridLayout()
    grid.addWidget(QLabel('X'), 0, 0)
    grid.addWidget(sheet.xFormula.getWidget(), 0, 1)
    grid.addWidget(self.xMenuButton, 0, 2)
    grid.addWidget(QLabel('Y'), 1, 0)
    grid.addWidget(sheet.yFormula.getWidget(), 1, 1)
    grid.addWidget(self.yMenuButton, 1, 2)
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

  def showFormulaMenu(self, xy):
    btn = getattr(self, '%sMenuButton' % xy)
    self.formulaMenu.xy = xy
    self.formulaMenu.exec_(btn.mapToGlobal(QPoint(0, btn.rect().height())))
