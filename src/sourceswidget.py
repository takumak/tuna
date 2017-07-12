from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import \
  QWidget, QSplitter, QTreeWidget, QTreeWidgetItem, QMenu



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
    self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
    self.tree.customContextMenuRequested.connect(self.treeContextMenuRequested)

    self.fileMenu = QMenu()
    self.fileMenu.addAction('&Remove file').triggered.connect(
      lambda: self.removeFile(self.fileMenu.target))

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

  def removeFile(self, item):
    idx = self.tree.indexOfTopLevelItem(item)
    if idx >= 0:
      self.tree.takeTopLevelItem(idx)

  def treeContextMenuRequested(self, pos):
    item = self.tree.itemAt(pos)
    if self.tree.indexOfTopLevelItem(item) >= 0:
      self.fileMenu.target = item
      self.fileMenu.exec_(QCursor.pos())
