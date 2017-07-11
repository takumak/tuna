import os
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import \
  QVBoxLayout, QHBoxLayout, \
  QWidget, QDialog, QPushButton, QCheckBox, QLabel, \
  QSplitter, QTreeWidget, QTreeWidgetItem

from sheetwidgets import SheetWidget

class SelectColumnDialog(QDialog):
  def __init__(self, c, cname, unselect, x, y):
    super().__init__()
    self.c = c


    buttons = [[(unselect, 'Do not use', self.unselect)],
               [(x, 'X', self.X)]]
    buttons.append([(True, 'Y%d' % (y_ + 1), (lambda y_: lambda: self.Y(y_))(y_)) for y_ in y])


    btnlayout = QVBoxLayout()
    for r in buttons:
      row = QHBoxLayout()
      btnlayout.addLayout(row)
      for enable, text, func in r:
        btn = QPushButton(text)
        btn.clicked.connect((lambda f: f)(func))
        row.addWidget(btn)

    self.applyToAllSheets = QCheckBox('Apply to all sheets')
    self.applyToAllSheets.setChecked(True)

    btn = QPushButton('Cancel')
    btn.clicked.connect(self.reject)
    btnbar2 = QHBoxLayout()
    btnbar2.addStretch(1)
    btnbar2.addWidget(btn)

    vbox = QVBoxLayout()
    vbox.addWidget(QLabel('Use column "%s" for:' % cname))
    vbox.addLayout(btnlayout)
    vbox.addWidget(self.applyToAllSheets)
    vbox.addLayout(btnbar2)

    self.setLayout(vbox)

  def unselect(self):
    self.useFor = None
    self.accept()

  def X(self):
    self.useFor = 'x'
    self.accept()

  def Y(self, yn):
    self.useFor = 'y%d' % yn
    self.accept()



class SourcesWidget(QSplitter):
  updateRequested = pyqtSignal(name='updateRequested')

  def __init__(self):
    super().__init__(Qt.Horizontal)
    self.tree = QTreeWidget()
    self.blank = QWidget()
    self.addWidget(self.tree)
    self.addWidget(self.blank)

    self.tree.header().hide()
    self.tree.itemSelectionChanged.connect(self.itemSelectionChanged)
    self.tree.itemChanged.connect(lambda item, col: self.updateRequested.emit())

    self.sheets = []

  def itemSelectionChanged(self):
    items = self.tree.selectedItems()
    if len(items) == 0:
      self.replaceWidget(1, self.blank)
      return

    item = items[0]
    data = item.data(0, Qt.UserRole)[0]
    if isinstance(data, SheetWidget):
      self.replaceWidget(1, data)

  def headerClicked(self, sheetwidget, c):
    from functions import getTableColumnLabel
    unselect, x, y = sheetwidget.useColumnCandidates(c)
    dlg = SelectColumnDialog(c, getTableColumnLabel(c), unselect, x, y)
    if dlg.exec_() == dlg.Accepted:
      if dlg.applyToAllSheets.isChecked():
        sheets = self.siblingSheetWidgets(sheetwidget)
      else:
        sheets = [sheetwidget]

      if dlg.useFor is None:
        func = 'unselect'
        args = [c]
      elif dlg.useFor is 'x':
        func = 'setX'
        args = [c]
      elif dlg.useFor[0] == 'y':
        func = 'selectY'
        args = [c, int(dlg.useFor[1:])]

      useFor = dlg.useFor
      for sheet in sheets:
        getattr(sheet, func)(*args)

      self.updateRequested.emit()

  def topLevelItemForFilename(self, filename):
    for i in range(self.tree.topLevelItemCount()):
      item = self.tree.topLevelItem(i)
      if item.data(0, Qt.UserRole)[0] == filename:
        return item
    return None

  def addFile(self, filename, checked, sheets):
    pitem = self.topLevelItemForFilename(filename)
    if pitem is not None:
      self.tree.takeTopLevelItem(pitem)

    pitem = QTreeWidgetItem([os.path.basename(filename)])
    pitem.setData(0, Qt.UserRole, (filename,))
    pitem.setFlags((pitem.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsSelectable)
    pitem.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
    self.tree.addTopLevelItem(pitem)
    pitem.setExpanded(True)

    for sheet, checked, x, y in sheets:
      sw = SheetWidget(sheet)
      sw.setX(x)
      sw.setY(y)
      sw.horizontalHeader().sectionClicked.connect(
        (lambda sw: (lambda c: self.headerClicked(sw, c)))(sw))

      item = QTreeWidgetItem([sheet.name])
      item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
      item.setData(0, Qt.UserRole, (sw,))
      item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
      pitem.addChild(item)

  def files(self):
    files = []

    for i in range(self.tree.topLevelItemCount()):
      fitem = self.tree.topLevelItem(i)
      filename = fitem.data(0, Qt.UserRole)[0]

      sheets = []
      for j in range(fitem.childCount()):
        sitem = fitem.child(j)
        sw = sitem.data(0, Qt.UserRole)[0]
        sheets.append((sw, sitem.checkState(0) == Qt.Checked))

      if len(sheets) > 0:
        files.append((filename, fitem.checkState(0) == Qt.Checked, sheets))

    return files

  def enabledSheetWidgets(self):
    return sum([[sw for sw, c in sheets if c] for fn, c, sheets in self.files() if c], [])

  def siblingSheetWidgets(self, sheetwidget):
    for i in range(self.tree.topLevelItemCount()):
      fitem = self.tree.topLevelItem(i)
      widgets = []
      hit = False
      for j in range(fitem.childCount()):
        sitem = fitem.child(j)
        sw = sitem.data(0, Qt.UserRole)[0]
        if sitem.checkState(0) == Qt.Checked: widgets.append(sw)
        if sw == sheetwidget: hit = True
      return widgets
    return []
