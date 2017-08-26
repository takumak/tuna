import sys
import re
import logging
import html
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QPoint, QRect, QSize, QEvent, QCoreApplication
from PyQt5.QtGui import QKeySequence, QValidator, QPainter, \
  QPen, QBrush, QColor, QPixmap, QMouseEvent
from PyQt5.QtWidgets import QApplication, QWidget, QTableWidget, QMenu, \
  QFrame, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QLineEdit, QLayout, \
  QComboBox, QGridLayout, QPushButton
import numpy as np

import log



__all__ = [
  'TableWidget', 'HSeparator', 'HBoxLayout', 'VBoxLayout',
  'ErrorBaloon', 'ErrorCheckEdit', 'FlowLayout',
  'DescriptionWidget', 'ComboBoxWithDescriptor',
  'ExpanderWidget'
]



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

  def getSelectedItemTable(self):
    col, row, val = [], [], []
    for index in self.selectedIndexes():
      col.append(self.visualColumn(index.column()))
      row.append(self.visualRow(index.row()))
      val.append(self.item(index.row(), index.column()))

    col = np.array(col) - min(col)
    row = np.array(row) - min(row)

    data = dict(zip(zip(row, col), val))
    tbl = [[data[(r, c)] for c in range(max(col)+1)] for r in range(max(row)+1)]
    return tbl

  def copySelected(self):
    tbl = self.getSelectedItemTable()
    QApplication.clipboard().setText('\n'.join([
      '\t'.join([item.text().strip() for item in r]) for r in tbl]))

  def paste(self):
    text = QApplication.clipboard().text()
    data = [[c.strip() for c in l.split('\t')] for l in re.split(r'\r?\n', text)]

    sel = self.getSelectedItemTable()

    if len(sel) == 0:
      return
    elif len(sel) == 1 and len(sel[0]) == 1:
      r0 = self.visualRow(sel[0][0].row())
      c0 = self.visualColumn(sel[0][0].column())
      v2l_r = dict([(self.visualRow(r), r)    for r in range(self.rowCount())])
      v2l_c = dict([(self.visualColumn(c), c) for c in range(self.columnCount())])
      for r, vals in enumerate(data):
        for c, text in enumerate(vals):
          item = self.item(v2l_r[r0+r], v2l_c[c0+c])
          if item and item.flags() & Qt.ItemIsEditable:
            item.setText(text)
            self.cellChanged.emit(item.row(), item.column())
      return


    selerr_msg = 'The shapes of table selection and paste data are different'
    if len(sel) != len(data):
      logging.error(selerr_msg)
      return

    for items, values in zip(sel, data):
      if len(items) != len(values):
        logging.error(selerr_msg)
        return
      for item, val in zip(items, values):
        if val and not item:
          logging.error(selerr_msg)
          return

    for items, values in zip(sel, data):
      for item, val in zip(items, values):
        if item:
          item.setText(val)



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



class ErrorBaloon(QFrame):
  def __init__(self):
    super().__init__()

    self.label = QLabel()

    vbox = VBoxLayout()
    vbox.setContentsMargins(4, 4, 4, 4)
    vbox.addWidget(self.label)
    self.setLayout(vbox)

    self.setFrameShape(QFrame.StyledPanel)
    self.setWindowFlags(Qt.ToolTip)

  def setMessage(self, text):
    self.label.setText('<span style="font-weight:bold; color:#800">%s</span>' % html.escape(text))

  def updatePosition(self, widget):
    self.adjustSize()
    r = self.rect()
    tl = widget.mapToGlobal(QPoint(0, 0))
    tr = tl + QPoint(widget.size().width(), 0)
    x = (tl.x() + tr.x())/2 - r.width()/2
    self.move(x, tl.y() - r.height())



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
    self.doLayout(rect, False)

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
    return self.doLayout(QRect(0, 0, width, 0), True)

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

  def doLayout(self, rect, test):
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

      if not test:
        item.setGeometry(QRect(x, y, s.width(), s.height()))
      col += 1
      rh = max([rh, s.height()])
      x += s.width()+4
      width = max(width, x-4)

    return y-t+rh



class DescriptionWidget(QFrame):
  closed = pyqtSignal(QObject)

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

  def closeEvent(self, event):
    super().closeEvent(event)
    self.closed.emit(self)



class ComboBoxWithDescriptor(QComboBox):
  mouseEvents = (
    QEvent.MouseButtonPress,
    QEvent.MouseButtonRelease,
    QEvent.MouseMove,
    QEvent.MouseButtonDblClick
  )

  def __init__(self):
    super().__init__()

    self.currDescriptor = None
    self.preventHide = False

    self.view().entered.connect(self.showDescriptor)

  def closeDescriptor(self):
    if self.currDescriptor:
      self.currDescriptor.close()
      self.currDescriptor = None

  def descriptorClosed(self, desc):
    QApplication.instance().removeEventFilter(self)
    desc.closed.disconnect(self.descriptorClosed)

  def showDescriptor(self, index):
    self.closeDescriptor()

    widget = index.data(Qt.UserRole+1)
    if not isinstance(widget, QWidget):
      return

    view = self.view()
    pos = view.mapToGlobal(QPoint(view.width(), view.visualRect(index).y()))

    widget.setWindowFlags(Qt.ToolTip)
    widget.move(pos)
    widget.show()

    widget.closed.connect(self.descriptorClosed)
    QApplication.instance().installEventFilter(self)

    self.currDescriptor = widget

  @classmethod
  def isDescendant(self, widget, ancestor):
    while isinstance(widget, QWidget):
      if widget == ancestor:
        return True
      widget = widget.parentWidget()
    return False

  def eventFilter(self, obj, event):
    if event.type() in self.mouseEvents and self.isDescendant(obj, self.view().window()):
      w = QApplication.widgetAt(event.globalPos())
      if self.isDescendant(w, self.currDescriptor):
        localpos = w.mapFromGlobal(event.globalPos())
        newev = QMouseEvent(
          event.type(),
          localpos,
          event.screenPos(),
          event.button(),
          event.buttons(),
          event.modifiers()
        )
        QApplication.sendEvent(w, newev)
        self.preventHide = True

    if event.type() in (QEvent.Close, QEvent.Hide) and obj == self.view().window():
      self.closeDescriptor()

    return False

  def hidePopup(self):
    if self.preventHide:
      self.preventHide = False
      return
    super().hidePopup()



class ExpanderWidget(QWidget):
  def __init__(self, label, widget):
    super().__init__()

    if isinstance(widget, QLayout):
      layout = widget
      widget = QWidget()
      widget.setLayout(layout)

    self.button = QPushButton(label)
    self.button.setCheckable(True)
    self.button.toggled.connect(self.buttonToggled)
    self.widget = widget
    self.buttonToggled()

    vbox = VBoxLayout()
    vbox.addWidget(self.button)
    vbox.addWidget(self.widget)
    self.setLayout(vbox)

  def buttonToggled(self, *args):
    self.widget.setVisible(self.button.isChecked())
