import logging
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence, QCursor
from PyQt5.QtWidgets import QApplication, QTableWidget, QMenu, \
  QTabWidget, QTabBar, QCheckBox, QFrame, QVBoxLayout, QHBoxLayout


class TableWidget(QTableWidget):
  def __init__(self):
    super().__init__()
    self.menu = QMenu()
    self.menu.addAction('&Copy selected', self.copySelected, QKeySequence('Ctrl+C'))

  def keyPressEvent(self, ev):
    if ev.matches(QKeySequence.Copy):
      self.copySelected()
      return

    super().keyPressEvent(ev)

  def contextMenuEvent(self, ev):
    self.menu.exec_(ev.globalPos())

  def copySelected(self):
    rows = []
    row = None
    curRow = None
    for cell in self.selectedIndexes():
      if cell.row() != curRow:
        row = []
        rows.append(row)
        curRow = cell.row()
      row.append(str(cell.data()).strip())
    QApplication.clipboard().setText('\n'.join(['\t'.join(r) for r in rows]))



class HSeparator(QFrame):
  def __init__(self):
    super().__init__()
    self.setFrameShape(QFrame.HLine)
    self.setFrameShadow(QFrame.Sunken)



class HBoxLayout(QHBoxLayout):
  def __init__(self):
    super().__init__()
    self.setContentsMargins(0, 0, 0, 0)
    self.setSpacing(4)



class VBoxLayout(QVBoxLayout):
  def __init__(self):
    super().__init__()
    self.setContentsMargins(0, 0, 0, 0)
    self.setSpacing(4)
