import sys, os
import logging
import html
import json, base64
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QTextCursor, QKeySequence
from PyQt5.QtWidgets import \
  QMainWindow, QFileDialog, QTextEdit, QDockWidget


import log
import fileloader
from sheetwidgets import SheetWidget
from graphwidgets import GraphWidget
from tools import NopTool
from toolwidgets import FitToolWidget, IADToolWidget
from commonwidgets import TabWidgetWithCheckBox
from widgets import SourcesWidget



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

    self.sourcesWidget = SourcesWidget()
    self.sourcesWidget.selectionChanged.connect(self.update)
    self.sourcesWidget.hide()
    self.sourcesDockWidget = QDockWidget('Sources')
    self.sourcesDockWidget.setObjectName('dock_sources')
    self.sourcesDockWidget.setWidget(self.sourcesWidget)

    self.logTextEdit = QTextEdit()
    self.logTextEdit.setReadOnly(True)
    self.logDockWidget = QDockWidget('Log')
    self.logDockWidget.setObjectName('dock_log')
    self.logDockWidget.setWidget(self.logTextEdit)

    dock_p = None
    toolDockWidgets = []
    self.toolWidgets = [IADToolWidget()]
    self.tools = []
    self.curTool = self.toolWidgets[0].tool
    for t in self.toolWidgets:
      t.plotRequested.connect(self.plotRequested)
      dock = QDockWidget(t.label())
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
    self.toolWidgets[0].raise_()

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
    if dlg.exec_() == dlg.Accepted:
      self.openFiles([os.path.realpath(f) for f in dlg.selectedFiles()])

  def openFiles(self, filenames):
    for filename in filenames:
      try:
        f = fileloader.load(filename)
      except fileloader.UnsupportedFileException as ex:
        logging.error('Unsupported file: %s %s' % (ex.mimetype, ex.filename))
        continue
      self.addFile(filename, True, [(s, True, 0, [1]) for s in f])
    self.update()
    self.sourcesDockWidget.raise_()

  def addFile(self, filename, checked, sheets):
    logging.debug('Add file: %s' % filename)
    self.sourcesWidget.show()
    self.sourcesWidget.addFile(filename, checked, sheets)

  def update(self):
    for t in self.tools:
      t.clear()

    for sw in self.sourcesWidget.enabledSheetWidgets():
      x = sw.getX()[1]
      y_ = sw.getY()
      for n, y in y_:
        name = sw.sheet.name
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

    obj = json.load(open(self.config_filename))

    if 'mainwindow' in obj:
      mw = obj['mainwindow']
      if 'state' in mw:
        state = base64.b64decode(mw['state'])
        try:
          self.restoreState(state, self.saveStateVersion)
        except:
          log.excepthook(*sys.exc_info())

    if 'files' in obj:
      for f in obj['files']:
        checked = f['enabled']
        filename = f['filename']
        sheets = []

        try:
          book = fileloader.load(filename)
        except:
          log.excepthook(*sys.exc_info())
          continue


        for s in f['sheets']:
          c = s['enabled']
          i = s['index']
          x = s['x']
          y = s['y']
          sheets.append((book.getSheet(i), c, x, y))

        self.addFile(filename, checked, sheets)

    if 'graph' in obj:
      graph = obj['graph']
      if 'range' in graph:
        self.graphWidget.setRange(QRectF(*graph['range']))

    if 'tools' in obj:
      tools = obj['tools']
      for t in self.toolWidgets:
        if t.name() in tools:
          try:
            t.restoreState(tools[t.name()])
          except:
            log.excepthook(*sys.exc_info())
            pass

    self.update()
    self.sourcesDockWidget.raise_()

  def saveConfig(self):
    files = []
    for fn, fc, sw_ in self.sourcesWidget.files():
      sheets = []
      for sw, sc in sw_:
        sheets.append({
          'enabled': sc,
          'index': sw.sheet.idx,
          'x': sw.x,
          'y': sw.y
        })
      files.append({
        'enabled': fc,
        'filename': fn,
        'sheets': sheets
      })

    r = self.graphWidget.viewRect()
    obj = {
      'files': files,
      'mainwindow': {
        'state': str(base64.b64encode(self.saveState(self.saveStateVersion)), 'ascii')
      },
      'tools': dict([(t.name(), t.saveState()) for t in self.toolWidgets]),
      'graph': {
        'range': [r.x(), r.y(), r.width(), r.height()]
      }
    }

    json.dump(obj, open(self.config_filename, 'w'))
