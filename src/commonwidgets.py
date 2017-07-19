import sys
import logging
import html
from PyQt5.QtCore import QPoint, QRect
from PyQt5.QtGui import QKeySequence, QValidator, QPainter, QPen, QBrush, QColor
from PyQt5.QtWidgets import QApplication, QTableWidget, QMenu, \
  QFrame, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit

import log



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



class ErrorBaloon(QWidget):
  def __init__(self):
    super().__init__()

    self.label = QLabel()

    vbox = VBoxLayout()
    vbox.setContentsMargins(4, 4, 4, 4)
    vbox.addWidget(self.label)
    self.setLayout(vbox)

  def paintEvent(self, ev):
    rect = self.rect()
    rect = QRect(rect.x(), rect.y(), rect.width()-1, rect.height()-1)

    painter = QPainter(self)
    painter.setRenderHint(painter.Antialiasing)
    painter.setBrush(QBrush(QColor(0xf8, 0xf8, 0xf8)))
    painter.setPen  (  QPen(QColor(0x80, 0x80, 0x80)))
    painter.drawRoundedRect(rect, 3, 3)
    painter.end()

  def setMessage(self, text):
    self.label.setText('<span style="font-weight:bold; color:#800">%s</span>' % html.escape(text))

  def updatePosition(self, widget):
    self.setParent(widget.window())
    self.adjustSize()

    parent = widget.parentWidget()
    pt = widget.mapTo(parent, QPoint(0, 0))
    while(parent != self.parentWidget()):
      pt = parent.mapTo(parent.parentWidget(), pt)
      parent = parent.parentWidget()

    self.move(pt.x(), pt.y() - self.rect().height())



class ErrorCheckEdit(QLineEdit):
  def __init__(self, validator, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.validator = validator
    self.baloon = ErrorBaloon()
    self.state = QValidator.Acceptable
    self.textChanged.connect(lambda t: self.checkValue())

  def checkValue(self):
    try:
      self.state, message = self.validator(self.text())
    except:
      log.warnException()
      self.state = QValidator.Invalid
      message = '%s %s' % sys.exc_info()[:2]

    self.baloon.setMessage(message)
    if self.state != QValidator.Acceptable and self.hasFocus():
      self.showBaloon()
    else:
      self.hideBaloon()

  def showBaloon(self):
    self.baloon.updatePosition(self)
    self.baloon.update()
    self.baloon.show()
    self.setStyleSheet('');

  def hideBaloon(self):
    self.baloon.hide()
    if self.state == QValidator.Acceptable:
      self.setStyleSheet('');
    else:
      self.setStyleSheet('QLineEdit{background-color:red}');

  def focusInEvent(self, ev):
    super().focusInEvent(ev)
    if self.state == QValidator.Acceptable:
      self.hideBaloon()
    else:
      self.showBaloon()

  def focusOutEvent(self, ev):
    super().focusOutEvent(ev)
    self.hideBaloon()
