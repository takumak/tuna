import re
import numpy as np
from PyQt5.QtCore import Qt, QVariant, pyqtSignal
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import \
  QWidget, QTableWidgetItem, QGridLayout, QLabel, QLineEdit

from commonwidgets import TableWidget, VBoxLayout
from functions import getTableColumnLabel


class SheetWidget(QWidget):

  def __init__(self, sheet):
    super().__init__()
    self.sheet = sheet

    vbox = VBoxLayout()
    self.setLayout(vbox)

    self.xLineEdit = QLineEdit()
    self.yLineEdit = QLineEdit()

    grid = QGridLayout()
    grid.addWidget(QLabel('X'), 0, 0)
    grid.addWidget(self.xLineEdit, 0, 1)
    grid.addWidget(QLabel('Y'), 1, 0)
    grid.addWidget(self.yLineEdit, 1, 1)
    vbox.addLayout(grid)

    self.table = TableWidget()
    self.table.setColumnCount(sheet.colCount())
    self.table.setRowCount(sheet.rowCount())
    vbox.addWidget(self.table)

    for c in range(sheet.colCount()):
      self.table.setHorizontalHeaderItem(c, QTableWidgetItem(getTableColumnLabel(c)))
      for r in range(sheet.rowCount()):
        self.table.setItem(r, c, QTableWidgetItem(str(self.sheet.getValue(r, c))))

    self.errors = ['0']*sheet.colCount()

  def x(self):
    return self.xLineEdit.text()

  def setX(self, text):
    self.xLineEdit.setText(text)

  def y(self):
    return self.yLineEdit.text()

  def setY(self, text):
    self.yLineEdit.setText(text)

  def xvalues(self):
    return np.array(list(zip(*self.sheet.evalFormula(self.x()))))

  def yvalues(self):
    return np.array(list(zip(*self.sheet.evalFormula(self.y()))))
