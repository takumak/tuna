import os
import logging
import html
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QTextCursor, QKeySequence
from PyQt5.QtWidgets import \
  QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, \
  QFileDialog, QDialog, QLabel, QTabWidget, QTabBar, \
  QCheckBox, QTextEdit, QSplitter, QDockWidget, QPushButton


import fileloader
from sheetwidgets import SheetWidget
from graphwidgets import GraphWidget
from tools import NopTool
from toolwidgets import FitToolWidget, IADToolWidget
from commonwidgets import TabWidgetWithCheckBox



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


class MainWindow(QMainWindow):
  saveStateVersion = 1

  def __init__(self, config_filename):
    super().__init__()
    self.config_filename = config_filename
    self.fileToolBar = self.addToolBar('File')
    self.fileToolBar.setObjectName('toolbar_File')
    act_open = self.fileToolBar.addAction('Open')
    act_open.setShortcut(QKeySequence.Open)
    act_open.triggered.connect(self.showOpenFileDialog)

    self.graphWidget = GraphWidget()
    self.setCentralWidget(self.graphWidget)

    self.sourcesTabWidget = TabWidgetWithCheckBox()
    self.sourcesTabWidget.setTabsClosable(True)
    self.sourcesTabWidget.selectionChanged.connect(self.update)
    self.sourcesTabWidget.tabCloseRequested.connect(self.sourceTabCloseRequested)
    self.sourcesTabWidget.hide()
    self.sourcesDockWidget = QDockWidget('Sources')
    self.sourcesDockWidget.setObjectName('dock_Sources')
    self.sourcesDockWidget.setWidget(self.sourcesTabWidget)

    self.logTextEdit = QTextEdit()
    self.logTextEdit.setReadOnly(True)
    self.logDockWidget = QDockWidget('Log')
    self.logDockWidget.setObjectName('dock_Log')
    self.logDockWidget.setWidget(self.logTextEdit)

    dock_p = None
    toolWidgets = [IADToolWidget()]
    toolDockWidgets = []
    self.tools = []
    self.curTool = toolWidgets[0].tool
    for t in toolWidgets:
      t.plotRequested.connect(self.plotRequested)
      dock = QDockWidget(t.name())
      dock.setObjectName('dock_%s' % t.name())
      dock.setWidget(t)
      toolDockWidgets.append(dock)
      self.tools.append(t.tool)
      self.addDockWidget(Qt.RightDockWidgetArea, dock)
      if dock_p:
        self.tabifyDockWidget(dock_p, dock)
      dock_p = dock

    self.addDockWidget(Qt.BottomDockWidgetArea, self.sourcesDockWidget)
    self.resizeDocks(toolDockWidgets, [400] * len(toolDockWidgets), Qt.Horizontal)
    toolWidgets[0].raise_()

    self.addDockWidget(Qt.BottomDockWidgetArea, self.logDockWidget)
    self.tabifyDockWidget(self.logDockWidget, self.sourcesDockWidget)
    self.resizeDocks([self.sourcesDockWidget, self.logDockWidget], [200, 200], Qt.Vertical)
    self.logDockWidget.raise_()

    self.resize(1000, 800)
    self.setAcceptDrops(True)

    self.loadConfig()

    logging.info('Drag and drop here to open multiple files')

  def dragEnterEvent(self, ev):
    if not ev.mimeData().hasUrls():
      return
    for url in ev.mimeData().urls():
      if url.isLocalFile():
        ev.acceptProposedAction()
        return

  def dropEvent(self, ev):
    if not ev.mimeData().hasUrls():
      return

    files = []
    for url in ev.mimeData().urls():
      if url.isLocalFile():
        files.append(url.toLocalFile())

    if files:
      ev.acceptProposedAction()
      self.openFiles(files)

  def showOpenFileDialog(self):
    dlg = QFileDialog()
    dlg.setAcceptMode(QFileDialog.AcceptOpen)
    dlg.setFileMode(QFileDialog.ExistingFiles)
    if dlg.exec_() == QDialog.Accepted:
      self.openFiles(dlg.selectedFiles())

  def openFiles(self, filenames):
    for filename in filenames:
      try:
        f = fileloader.load(filename)
      except fileloader.UnsupportedFileException as ex:
        logging.error('Unsupported file: %s %s' % (ex.mimetype, ex.filename))
        continue
      for sheet in f:
        self.addSheet(sheet)
    self.update()
    self.sourcesDockWidget.raise_()

  def addSheet(self, sheet, checked = True):
    logging.info('Add sheet: %s' % sheet.name)
    self.sourcesTabWidget.show()

    sheetwidget = SheetWidget(sheet)
    sheetwidget.horizontalHeader().sectionClicked.connect(
      lambda c: self.headerClicked(sheetwidget, c))
    self.sourcesTabWidget.addTab(sheetwidget, sheet.name, checked)
    return sheetwidget

  def headerClicked(self, sheetwidget, c):
    unselect, x, y = sheetwidget.useColumnCandidates(c)
    dlg = SelectColumnDialog(c, sheetwidget.getHeaderLabel(c), unselect, x, y)
    if dlg.exec_() == QDialog.Accepted:
      if dlg.applyToAllSheets.isChecked():
        sheets = self.sourcesTabWidget.getAllWidgets()
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

      self.update()

  def useColumnForAllSheetRequested(self, c, useFor):
    for sw in self.sourcesTabWidget.getAllWidgets():
      sw.useColumn(c, useFor)

  def sourceTabCloseRequested(self, idx):
    self.sourcesTabWidget.removeTab(idx)
    self.update()

  def update(self):
    for t in self.tools:
      t.clear()

    for i, sw in enumerate(self.sourcesTabWidget.getAllWidgets()):
      if not self.sourcesTabWidget.isChecked(i): continue
      x = sw.getX()[1]
      y_ = sw.getY()
      for n, y in y_:
        name = self.sourcesTabWidget.tabText(i)
        if len(y_) > 1:
          name += ':%s' % n
        for t in self.tools:
          t.add(x, y, name)

    self.updateGraph()

  def plotRequested(self, tool, autoRange):
    self.curTool = tool
    self.updateGraph()
    if autoRange:
      self.graphWidget.autoRange()

  def updateGraph(self):
    self.graphWidget.clearItems()
    for l in self.curTool.getLines():
      self.graphWidget.add(l)

  def log_(self, html, activate=False):
    self.logTextEdit.moveCursor(QTextCursor.End)
    self.logTextEdit.insertHtml(html)
    s = self.logTextEdit.verticalScrollBar()
    s.setValue(s.maximum())
    if activate:
      self.logDockWidget.raise_()

  def closeEvent(self, ev):
    self.saveConfig()
    ev.accept()

  def loadConfig(self):
    if not os.path.exists(self.config_filename):
      return

    import toml
    obj = toml.load(open(self.config_filename))
    self.loadState(obj['mainwindow']['state'])

    files = {}
    for sheet in obj['sheets']:
      filename = sheet.filename
      f = files.get(filename, None)
      if f is False:
        continue
      elif f is None:
        try:
          f = fileloader.load(filename)
        except:
          logging.error('Failed to load file: %s' % filename)
          files[filename] = False
          continue
        files[filename] = f

      sw = self.addSheet(f.getSheet(sheet['index']), sheet['enabled'])
      sw.setX(sheet['x'])
      sw.setY(sheet['y'])

  def saveConfig(self):
    import toml

    sheets = []
    for i, sw in enumerate(self.sourcesTabWidget.getAllWidgets()):
      sheets.append({
        'enabled': self.sourcesTabWidget.isChecked(i),
        'filename': sw.sheet.filename,
        'index': sw.sheet.idx,
        'x': sw.x,
        'y': sw.y
      })

    obj = {
      'sheets': sheets,
      'mainwindow': {
        'state': self.saveState(self.saveStateVersion)
      }
    }

    toml.dump(obj, open(self.config_filename, 'w'))
