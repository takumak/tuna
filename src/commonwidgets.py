import logging
from PyQt5.QtGui import QKeySequence, QValidator
from PyQt5.QtWidgets import QApplication, QTableWidget, QMenu, \
  QFrame, QVBoxLayout, QHBoxLayout, QSpinBox


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



class SpinBox(QSpinBox):
  def __init__(self, min_, max_, func):
    super().__init__()
    self.min_ = min_
    self.max_ = max_
    self.func = func

    if min_ is not None:
      self.setMinimum(min_)
    if max_ is not None:
      self.setMaximum(max_)

  def validate(self, text, pos):
    state = super().validate(text, pos)
    if state[0] == QValidator.Acceptable:
      val = int(text)
      if self.min_ is not None and val < self.min_:
        return (QValidator.Invalid, text, pos)
      if self.max_ is not None and val > self.max_:
        return (QValidator.Invalid, text, pos)
      if self.func and not self.func(val):
        return (QValidator.Invalid, text, pos)
    return state
