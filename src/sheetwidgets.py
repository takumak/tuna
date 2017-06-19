from PyQt5.QtCore import Qt, QVariant, pyqtSignal
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import QTableWidgetItem

from commonwidgets import TableWidget


class SheetWidget(TableWidget):
  useColumnRequested = pyqtSignal(int, str, bool, name='useColumnRequested')

  def __init__(self, sheet):
    super().__init__()
    self.sheet = sheet
    self.setColumnCount(sheet.colCount())
    self.setRowCount(sheet.rowCount())

    for c in range(sheet.colCount()):
      self.setHorizontalHeaderItem(c, QTableWidgetItem(self.getHeaderLabel(c)))
      for r in range(sheet.rowCount()):
        self.setItem(r, c, QTableWidgetItem(str(self.sheet.getValue(r, c))))

    self.x = None
    self.y = []
    self.setX(0)
    self.selectY(1, 0)

  def getHeaderLabel(self, c):
    label = ''
    while True:
      label += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[c % 26]
      if c <= 26:
        break
      c = int(c/26)
    return label

  def useColumnCandidates(self, c):
    unselect = c in self.y and len(self.y) >= 2
    x = c != self.x
    y = list(range(0, len(self.y) + (0 if c == self.x or c in self.y else 1)))
    return unselect, x, y

  def getColumn(self, c):
    return [self.item(r, c).text() for r in range(self.rowCount())]

  def getX(self):
    return self.getHeaderLabel(self.x), self.getColumn(self.x)

  def getY(self):
    return [(self.getHeaderLabel(c), self.getColumn(c)) for c in self.y]

  def setX(self, c):
    if c in self.y:
      self.y[self.y.index(c)] = self.x
    self.x = c
    self.updateHeaderState()

  def selectY(self, c, yn):
    if c == self.x:
      self.x = self.y[yn]
    elif c in self.y:
      self.y[self.y.index(c)] = self.y[yn]

    if yn == len(self.y):
      self.y.append(c)
    else:
      self.y[yn] = c
    self.updateHeaderState()

  def unselect(self, c):
    if c in self.y:
      self.y.remove(c)
    self.updateHeaderState()

  def updateHeaderState(self):
    for c in range(self.columnCount()):
      item = self.horizontalHeaderItem(c)
      label = self.getHeaderLabel(c)
      if c == self.x:
        item.setBackground(Qt.red)
        label += ' (X)'
      elif c in self.y:
        item.setBackground(Qt.blue)
        label += ' (Y%d)' % (self.y.index(c) + 1)
      else:
        item.setData(Qt.BackgroundRole, QVariant())
      item.setText(label)
