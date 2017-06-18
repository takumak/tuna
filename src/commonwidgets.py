from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence, QCursor
from PyQt5.QtWidgets import QApplication, QTableWidget, QMenu, \
  QTabWidget, QTabBar, QCheckBox


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
      row.append(cell.data())
    QApplication.clipboard().setText('\n'.join(['\t'.join(r) for r in rows]))


class TabWidgetWithCheckBox(QTabWidget):
  selectionChanged = pyqtSignal(name='selectionChanged')

  def __init__(self):
    super().__init__()

    self.menu = QMenu()
    self.menu.addAction('Select all', self.selectAll)
    self.menu.addAction('Select all except this', self.selectAllExceptThis)
    self.menu.addAction('Unselect all except this', self.unselectAllExceptThis)
    self.menu.addAction('Select right tabs', self.selectRightTabs)
    self.menu.addAction('Unselect right tabs', self.unselectRightTabs)
    self.menu.addAction('Select left tabs', self.selectLeftTabs)
    self.menu.addAction('Unselect left tabs', self.unselectLeftTabs)

    tabbar = self.tabBar()
    tabbar.setContextMenuPolicy(Qt.CustomContextMenu)
    tabbar.customContextMenuRequested.connect(self.showTabMenu)

  def isChecked(self, i):
    return self.tabBar().tabButton(i, QTabBar.LeftSide).isChecked()

  def setChecked(self, i, checked):
    self.tabBar().tabButton(i, QTabBar.LeftSide).setChecked(checked)

  def selectAll(self, func = None):
    for i in range(self.count()):
      if func is None or func(i):
        self.setChecked(i, True)
    self.selectionChanged.emit()

  def unselectAll(self, func = None):
    for i in range(self.count()):
      if func is None or func(i):
        self.setChecked(i, False)
    self.selectionChanged.emit()

  def selectAllExceptThis(self):
    self.selectAll(lambda i: i != self.currentIndex())

  def unselectAllExceptThis(self):
    self.unselectAll(lambda i: i != self.currentIndex())

  def selectRightTabs(self):
    self.selectAll(lambda i: i > self.currentIndex())

  def unselectRightTabs(self):
    self.unselectAll(lambda i: i > self.currentIndex())

  def selectLeftTabs(self):
    self.selectAll(lambda i: i < self.currentIndex())

  def unselectLeftTabs(self):
    self.unselectAll(lambda i: i < self.currentIndex())

  def showTabMenu(self, point):
    tabbar = self.tabBar()
    idx = tabbar.tabAt(point)
    self.setCurrentIndex(idx)
    self.menu.exec_(QCursor.pos())

  def addTab(self, widget, name, checked):
    idx = super().addTab(widget, name)

    check = QCheckBox()
    check.setChecked(checked)
    check.clicked.connect(self.selectionChanged)
    self.tabBar().setTabButton(idx, QTabBar.LeftSide, check)

  def getAllWidgets(self):
    return [self.widget(i) for i in range(self.count())]
