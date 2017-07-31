import sys
import logging
import html
from PyQt5.QtCore import QPoint, QRect, QSize
from PyQt5.QtGui import QKeySequence, QValidator, QPainter, QPen, QBrush, QColor
from PyQt5.QtWidgets import QApplication, QTableWidget, QMenu, \
  QFrame, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QLayout

import log



__all__ = ['TableWidget', 'HSeparator', 'HBoxLayout', 'VBoxLayout',
           'ErrorBaloon', 'ErrorCheckEdit', 'FlowLayout']



class TableWidget(QTableWidget):
  def __init__(self):
    super().__init__()
    self.menu = QMenu()
    self.menu.addAction('&Copy selected', self.copySelected, QKeySequence.Copy)
    self.menu.addAction('&Paste',         self.paste,        QKeySequence.Paste)

  def keyPressEvent(self, ev):
    if ev.matches(QKeySequence.Copy):
      self.copySelected()
      return

    if ev.matches(QKeySequence.Paste):
      self.paste()
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

  def paste(self):
    text = QApplication.clipboard().text()
    rows = [[c.strip() for c in l.split('\t')] for l in re.split(r'\r?\n', text)]

    r0, c0 = self.currentRow(), self.currentColumn()
    for r, row in enumerate(rows):
      for c, text in enumerate(row):
        item = self.item(r0+r, c0+c)
        if item.flags() & Qt.ItemIsEditable:
          item.setText(text)



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
      self.setStyleSheet('background-color:red');

  def focusInEvent(self, ev):
    super().focusInEvent(ev)
    if self.state == QValidator.Acceptable:
      self.hideBaloon()
    else:
      self.showBaloon()

  def focusOutEvent(self, ev):
    super().focusOutEvent(ev)
    self.hideBaloon()



class FlowLayout(QLayout):
  def __init__(self):
    super().__init__()
    self.items = []

  def count(self):
    return len(self.items)

  def addItem(self, item):
    self.items.append(item)

  def setGeometry(self, rect):
    l, t = rect.x()+4, rect.y()+4
    r, b = l+rect.width()-8, t+rect.height()-8

    col, rh = 0, 0
    x, y = l, t
    for item in self.items:
      s = item.minimumSize()

      if col > 0 and x+s.width() >= r:
        x = l
        y += rh + 4
        col, rh = 0, 0

      item.setGeometry(QRect(x, y, s.width(), s.height()))
      col += 1
      rh = max([rh, s.height()])
      x += s.width()+4

  def sizeHint(self):
    if len(self.items) == 0:
      return QSize(0, 0)

    s = [item.minimumSize() for item in self.items]
    w = sum([i.width() for i in s])
    h = max([i.height() for i in s])
    return QSize(w, h)

  def itemAt(self, idx):
    try:
      return self.items[idx]
    except IndexError:
      return None

  def takeAt(self, idx):
    try:
      item = self.items[idx]
      item.widget().close()
      del self.items[idx]
      return item
    except IndexError:
      return None
