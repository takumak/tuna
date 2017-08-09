import sys
import re
import logging
import html
from PyQt5.QtCore import Qt, QPoint, QRect, QSize, QEvent, QCoreApplication
from PyQt5.QtGui import QKeySequence, QValidator, QPainter, QPen, QBrush, QColor, QPixmap
from PyQt5.QtWidgets import QApplication, QTableWidget, QMenu, \
  QFrame, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QLayout, \
  QComboBox, QGridLayout

import log



__all__ = ['TableWidget', 'HSeparator', 'HBoxLayout', 'VBoxLayout',
           'ErrorBaloon', 'ErrorCheckEdit', 'FlowLayout',
           'DescriptionWidget', 'ComboBoxWithDescriptor']



class TableWidget(QTableWidget):
  def __init__(self):
    super().__init__()
    self.menu = QMenu()
    self.keys = []

    self.addAction('&Copy selected', self.copySelected, QKeySequence.Copy)
    self.addAction('&Paste',         self.paste,        QKeySequence.Paste)

  def addAction(self, label, func, key):
    self.menu.addAction(label, func, key)
    self.keys.append((key, func))

  def keyPressEvent(self, ev):
    for key, func in self.keys:
      if isinstance(key, QKeySequence.StandardKey):
        m = ev.matches(key)
      else:
        m = (ev.key() | int(ev.modifiers())) in key

      if m:
        ev.accept()
        func()
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
        if item and item.flags() & Qt.ItemIsEditable:
          item.setText(text)
          self.cellChanged.emit(item.row(), item.column())



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
    super().setGeometry(rect)
    self.doLayout(rect)

  def sizeHint(self):
    if self.count() == 0:
      return QSize(0, 0)

    s = [item.minimumSize() for item in self.items]
    w = sum([i.width() for i in s])
    h = max([i.height() for i in s])
    return QSize(w, h)

  def expandingDirections(self):
    return Qt.Orientation(0)

  def hasHeightForWidth(self):
    return True

  def heightForWidth(self, width):
    return self.doLayout(QRect(0, 0, width, 0))

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

  def doLayout(self, rect):
    l, t = rect.x(), rect.y()
    r, b = l+rect.width(), t+rect.height()

    width = 0
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
      width = max(width, x-4)

    return y-t+rh



class DescriptionWidget(QFrame):
  def __init__(self):
    super().__init__()

    vbox = VBoxLayout()
    vbox.setContentsMargins(4, 4, 4, 4)
    self.setLayout(vbox)
    self.vbox = vbox

    self.setFrameShape(QFrame.StyledPanel)

  def addTitle(self, title):
    label = QLabel(title)
    label.setContentsMargins(16, 4, 16, 4)

    vbox = VBoxLayout()
    vbox.addWidget(label)

    frame = QFrame()
    frame.setFrameShape(QFrame.StyledPanel)
    frame.setContentsMargins(4, 4, 4, 4)
    frame.setLayout(vbox)
    self.vbox.addWidget(frame)

  def addLabel(self, text, **kwargs):
    label = QLabel(text)
    if kwargs.get('richtext'):
      label.setTextFormat(Qt.RichText)
      label.setTextInteractionFlags(Qt.TextBrowserInteraction)
      label.setOpenExternalLinks(True)
    self.vbox.addWidget(label)

  def addImage(self, image):
    imglabel = QLabel()
    imglabel.setContentsMargins(16, 4, 16, 4)
    imglabel.setPixmap(QPixmap.fromImage(image))
    self.vbox.addWidget(imglabel)

  def addGrid(self):
    grid = QGridLayout()
    grid.setContentsMargins(16, 4, 4, 16)
    grid.setColumnStretch(1, 1)
    grid.setHorizontalSpacing(16)
    self.vbox.addLayout(grid)
    return grid



class ComboBoxWithDescriptor(QComboBox):
  def __init__(self):
    super().__init__()

    self.currDescriptor = None
    self.preventHide = False

    self.view().entered.connect(self.showDescriptor)
    self.view().window().installEventFilter(self)

  def closeDescriptor(self):
    if self.currDescriptor:
      self.currDescriptor.close()
      self.currDescriptor = None

  def showDescriptor(self, index):
    self.closeDescriptor()

    widget = index.data(Qt.UserRole+1)
    if not isinstance(widget, QWidget):
      return

    widget.setWindowFlags(Qt.ToolTip)

    view = self.view()
    pos = view.mapToGlobal(QPoint(view.width(), view.visualRect(index).y()))

    widget.move(pos)
    widget.show()

    self.currDescriptor = widget

  def eventFilter(self, obj, event):
    if obj == self.view().window():
      if event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
        d = self.currDescriptor
        if d and d.geometry().contains(event.globalPos()):
          self.preventHide = True

    return False

  def hidePopup(self):
    if self.preventHide:
      self.preventHide = False
      return

    super().hidePopup()
    self.closeDescriptor()
