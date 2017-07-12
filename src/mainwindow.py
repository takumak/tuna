import sys, os
import logging
import html
import json
from base64 import b64decode, b64encode
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QTextCursor, QKeySequence
from PyQt5.QtWidgets import \
  QMainWindow, QTextEdit, QDockWidget, \
  QMenuBar, QMenu, QAction


import log
import fileloader
from sheetwidgets import SheetWidget
from graphwidgets import GraphWidget
from tools import NopTool
from toolwidgets import FitToolWidget, IADToolWidget
from commonwidgets import TabWidgetWithCheckBox
from widgets import SourcesWidget, FileDialog



class MainWindow(QMainWindow):
  saveStateVersion = 1

  def __init__(self, configFilename):
    super().__init__()
    self.configFilename = configFilename


    actions = [
      ('act_file_import',     '&Import file',    QKeySequence(Qt.CTRL | Qt.Key_I), self.showImportFileDialog),
      ('act_session_open',    '&Open session',   QKeySequence.Open, self.showOpenSessionDialog),
      ('act_session_save',    '&Save session',   QKeySequence.Save, self.saveSession),
      ('act_session_save_as', 'Save session as', QKeySequence.SaveAs, lambda: self.saveSession(True)),
    ]

    for name, label, key, func in actions:
      act = QAction(label)
      act.setShortcut(key)
      act.triggered.connect(func)
      setattr(self, name, act)

    menubar = self.menuBar()
    filemenu = menubar.addMenu('&File')
    filemenu.addAction(self.act_file_import)

    sessionmenu = menubar.addMenu('&Session')
    sessionmenu.addAction(self.act_session_open)
    sessionmenu.addAction(self.act_session_save)
    sessionmenu.addAction(self.act_session_save_as)


    self.graphWidget = GraphWidget()
    self.setCentralWidget(self.graphWidget)

    self.sourcesWidget = SourcesWidget()
    self.sourcesWidget.updateRequested.connect(self.update)
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

    self.sessionFilename = None
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
      self.importFiles(files)

  def showImportFileDialog(self):
    dlg = FileDialog('file_import')
    if dlg.exec_() == dlg.Accepted:
      self.importFiles([os.path.realpath(f) for f in dlg.selectedFiles()])

  def importFiles(self, filenames):
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

  def showOpenSessionDialog(self):
    dlg = FileDialog('session_open')
    if dlg.exec_() != dlg.Accepted:
      return

    filename = os.path.realpath(dlg.selectedFiles()[0])
    try:
      self.loadSession(json.load(open(filename)))
    except:
      log.excepthook(*sys.exc_info())
      return

    self.sessionFilename = filename
    self.update()

  def saveSession(self, forceShowDialog=False):
    if self.sessionFilename is None or forceShowDialog:
      dlg = FileDialog('session_save')
      if dlg.exec_() != dlg.Accepted:
        return
      self.sessionFilename = os.path.realpath(dlg.selectedFiles()[0])

    obj = self.createSessionData()
    json.dump(obj, open(self.sessionFilename, 'w'))

  def loadSession(self, sess):
    logging.debug('Loading session')

    self.sourcesWidget.removeAllFiles()

    if 'files' in sess:
      for f in sess['files']:
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

    if 'graph' in sess:
      graph = sess['graph']
      if 'range' in graph:
        self.graphWidget.setRange(QRectF(*graph['range']))

    if 'tools' in sess:
      tools = sess['tools']
      for t in self.toolWidgets:
        if t.name() in tools:
          try:
            t.restoreState(tools[t.name()])
          except:
            log.excepthook(*sys.exc_info())
            pass

  def createSessionData(self):
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
      'graph': {
        'range': [r.x(), r.y(), r.width(), r.height()]
      },
      'tools': dict([(t.name(), t.saveState()) for t in self.toolWidgets]),
    }

    return obj

  def loadConfig(self):
    if not os.path.exists(self.configFilename):
      return

    logging.debug('Loading config file')
    obj = json.load(open(self.configFilename))

    if 'mainwindow' in obj:
      mw = obj['mainwindow']
      if 'state' in mw:
        state = b64decode(mw['state'])
        try:
          self.restoreState(state, self.saveStateVersion)
        except:
          log.excepthook(*sys.exc_info())

    if 'filedialogs' in obj:
      fd = obj['filedialogs']
      if 'state' in fd and fd['state'] is not None:
        FileDialog.state = b64decode(fd['state'])
      if 'states' in fd: FileDialog.states.update(fd['states'])

    if 'session' in obj:
      self.loadSession(obj['session'])

    self.update()
    self.sourcesDockWidget.raise_()

  def saveConfig(self):
    fdstate = None
    if FileDialog.state is not None: fdstate = str(b64encode(FileDialog.state), 'ascii')
    obj = {
      'session': self.createSessionData(),
      'mainwindow': {
        'state': str(b64encode(self.saveState(self.saveStateVersion)), 'ascii')
      },
      'filedialogs': {
        'state': fdstate,
        'states': FileDialog.states
      }
    }
    json.dump(obj, open(self.configFilename, 'w'))
