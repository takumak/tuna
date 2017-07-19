import os
import logging
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import \
  QWidget, QSplitter, QTreeWidget, QTreeWidgetItem, QMenu, \
  QTableWidgetItem

from sheetwidget import SheetWidget
from commonwidgets import TableWidget



class SourcesWidget(QSplitter):
  updateRequested = pyqtSignal(name='updateRequested')

  def __init__(self):
    super().__init__(Qt.Horizontal)

    self.tree = QTreeWidget()
    self.blank = QWidget()
    self.addWidget(self.tree)
    self.addWidget(self.blank)

    self.tree.header().hide()
    self.tree.itemSelectionChanged.connect(self.treeItemSelectionChanged)
    self.tree.itemChanged.connect(lambda item, col: self.updateRequested.emit())
    self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
    self.tree.customContextMenuRequested.connect(self.treeContextMenuRequested)

    self.fileMenu = QMenu()
    self.fileMenu.addAction('&Remove file').triggered.connect(
      lambda: self.removeFile(self.fileMenu.target))

    self.errtbl = TableWidget()
    self.errtbl.setColumnCount(2)
    self.errtbl.setHorizontalHeaderLabels(['Column', 'Error'])
    self.errtbl.itemChanged.connect(self.errtblItemChanged)
    self.addWidget(self.errtbl)

    self.sheets = []

  def treeItemSelectionChanged(self):
    items = self.tree.selectedItems()
    if len(items) == 0:
      self.replaceWidget(1, self.blank)
      self.errtbl.setDisabled(True)
      return

    item = items[0]
    sw = item.data(0, Qt.UserRole)[0]
    if not isinstance(sw, SheetWidget):
      self.replaceWidget(1, self.blank)
      self.errtbl.setDisabled(True)
      return

    from functions import getTableColumnLabel

    self.replaceWidget(1, sw)
    self.errtbl.clearContents()
    self.errtbl.setRowCount(sw.sheet.colCount())
    for c in range(sw.sheet.colCount()):
      l = getTableColumnLabel(c)
      litem = QTableWidgetItem(l)
      litem.setFlags(litem.flags() & ~Qt.ItemIsEditable)
      eitem = QTableWidgetItem(sw.sheet.errors[c])
      eitem.setData(Qt.UserRole, (sw.sheet, c))
      self.errtbl.setItem(c, 0, litem)
      self.errtbl.setItem(c, 1, eitem)
    self.errtbl.setDisabled(False)

  def errtblItemChanged(self, item):
    data = item.data(Qt.UserRole)
    if data:
      sheet, c = data
      sheet.setError(c, item.text())
      logging.info('Error table item changed: errors[%d]=%s' % (c, item.text()))

  def topLevelItemForFilename(self, filename):
    for i in range(self.tree.topLevelItemCount()):
      item = self.tree.topLevelItem(i)
      if item.data(0, Qt.UserRole)[0] == filename:
        return item
    return None

  def addFile(self, filename, checked, expanded, sheets):
    fitem = self.topLevelItemForFilename(filename)
    if fitem is not None:
      self.tree.takeTopLevelItem(fitem)

    fitem = QTreeWidgetItem([os.path.basename(filename)])
    fitem.setData(0, Qt.UserRole, (filename,))
    fitem.setFlags((fitem.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsSelectable)
    fitem.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
    self.tree.addTopLevelItem(fitem)
    fitem.setExpanded(expanded)

    for sheet, checked in sheets:
      self.addSheet(fitem, sheet, checked)

  def addSheet(self, fitem, sheet, checked):
    item = QTreeWidgetItem([sheet.name])
    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
    item.setData(0, Qt.UserRole, (SheetWidget(sheet),))
    item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
    fitem.addChild(item)

  def removeAllFiles(self):
    while self.tree.topLevelItemCount() > 0:
      self.tree.takeTopLevelItem(0)

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
        files.append({
          'filename': filename,
          'enabled': fitem.checkState(0) == Qt.Checked,
          'expanded': fitem.isExpanded(),
          'sheets': sheets
        })

    return files

  def enabledSheetWidgets(self):
    return sum([[sw for sw, c in f['sheets'] if c] for f in self.files() if f['enabled']], [])

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

  def removeFile(self, item):
    idx = self.tree.indexOfTopLevelItem(item)
    if idx >= 0:
      self.tree.takeTopLevelItem(idx)

  def treeContextMenuRequested(self, pos):
    item = self.tree.itemAt(pos)
    if self.tree.indexOfTopLevelItem(item) >= 0:
      self.fileMenu.target = item
      self.fileMenu.exec_(QCursor.pos())
