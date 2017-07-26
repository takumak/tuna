import sys, os
import logging
import html
import json
from base64 import b64decode, b64encode
import numpy as np
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QTextCursor, QKeySequence
from PyQt5.QtWidgets import \
  QMainWindow, QTextEdit, QDockWidget, \
  QMenuBar, QMenu, QAction


import log
import fileloader
from graphwidget import GraphWidget
from sourceswidget import SourcesWidget
from dialogs import FileDialog
from iadtoolwidget import IADToolWidget



class MainWindow(QMainWindow):
  saveStateVersion = 1

  def __init__(self, configFilename):
    super().__init__()

    self.configFilename = configFilename


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
    self.toolIAD = IADToolWidget()
    self.tools = []
    self.toolWidgets = [self.toolIAD]
    self.curTool = self.toolIAD.tool
    for t in self.toolWidgets:
      t.plotRequested.connect(self.plotRequested)
      dock = QDockWidget(t.tool.label)
      dock.setObjectName('dock_%s' % t.tool.name)
      dock.setWidget(t)
      toolDockWidgets.append(dock)
      self.tools.append(t.tool)
      self.addDockWidget(Qt.RightDockWidgetArea, dock)
      if dock_p:
        self.tabifyDockWidget(dock_p, dock)
      dock_p = dock

    self.addDockWidget(Qt.BottomDockWidgetArea, self.sourcesDockWidget)
    self.resizeDocks(toolDockWidgets, [400] * len(toolDockWidgets), Qt.Horizontal)
    self.toolIAD.raise_()

    self.addDockWidget(Qt.BottomDockWidgetArea, self.logDockWidget)
    self.tabifyDockWidget(self.logDockWidget, self.sourcesDockWidget)
    self.resizeDocks([self.sourcesDockWidget, self.logDockWidget], [200, 200], Qt.Vertical)
    self.logDockWidget.raise_()


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

    self.act_session_relative = sessionmenu.addAction('Save with relative path')
    self.act_session_relative.setCheckable(True)

    viewmenu = menubar.addMenu('&View')
    for dockw in toolDockWidgets + [self.sourcesDockWidget, self.logDockWidget]:
      viewmenu.addAction(dockw.toggleViewAction())


    self.resize(1000, 800)
    self.setAcceptDrops(True)

    self._prevSheetSet = None
    self.sessionFilename = None
    self.performanceReport = False

    try:
      self.loadConfig()
    except:
      log.warnException()
      return

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
      self.addFile(filename, True, True, [(s, True) for s in f])
    self.toolIAD.mode = 'orig'
    self.update()
    self.sourcesDockWidget.raise_()

  def addFile(self, filename, checked, expanded, sheets):
    self.sourcesWidget.addFile(filename, checked, expanded, sheets)

  def update(self, autoRange=True):
    if not self.performanceReport:
      self.update_(autoRange)

    else:
      import cProfile, pstats, io
      pr = cProfile.Profile()
      pr.enable()
      try:
        self.update_(autoRange)
      finally:
        pr.disable()
        s = io.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        logging.info('\n'+s.getvalue())


  def update_(self, autoRange=True):
    for t in self.tools:
      t.clear()

    for sw in self.sourcesWidget.enabledSheetWidgets():
      X = sw.sheet.xValues()
      Y = sw.sheet.yValues()
      Y_ = sw.sheet.yErrors()
      if len(X) == 1: X = list(X) * len(Y)
      if len(X) != len(Y): raise RuntimeError('X and Y formulae count mismatch')

      for i, (x, y, y_) in enumerate(zip(X, Y, Y_)):
        name = sw.sheet.name
        if len(Y) > 1: name += ':%s' % i
        for t in self.tools:
          t.add(name, x, y, y_)

    self.updateGraph()
    if autoRange:
      self.graphWidget.autoRange()

  def plotRequested(self, tool, autoRange):
    self.curTool = tool

    sheetSet = [[sw.sheet.xFormula.value(), sw.sheet.yFormula.value()]+sw.sheet.errors
                for sw in self.sourcesWidget.enabledSheetWidgets()]
    if sheetSet != self._prevSheetSet:
      logging.info('Force reload lines from sources')
      self._prevSheetSet = sheetSet
      self.update()
      return

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
      self.loadSession(json.load(open(filename)), filename)
    except:
      log.warnException()
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

  def loadSession(self, sess, filename):
    logging.debug('Loading session')

    self.sourcesWidget.removeAllFiles()

    if 'relative' in sess:
      self.act_session_relative.setChecked(sess['relative'])

    if 'files' in sess:
      from os.path import normpath, join, dirname

      for f in sess['files']:
        filename = normpath(join(dirname(filename), f['filename']))
        sheets = []

        try:
          book = fileloader.load(filename)
        except:
          log.warnException()
          continue


        for s in f['sheets']:
          c = s['enabled']
          i = s['index']

          sheet = book.getSheet(i)
          if 'xformula' in s: sheet.xFormula.setStrValue(s['xformula'])
          if 'yformula' in s: sheet.yFormula.setStrValue(s['yformula'])
          if 'errors' in s: sheet.errors = s['errors']
          sheets.append((sheet, c))

        logging.debug('Add file: %s' % filename)
        self.sourcesWidget.show()
        self.sourcesWidget.addFile(
          filename,
          f.get('enabled', True),
          f.get('expanded', True),
          sheets
        )

    if 'graph' in sess:
      graph = sess['graph']
      if 'range' in graph:
        self.graphWidget.setRange(QRectF(*graph['range']))

    if 'tools' in sess:
      tools = sess['tools']
      for tw in self.toolWidgets:
        if tw.tool.name in tools:
          try:
            tw.restoreState(tools[tw.tool.name])
          except:
            log.warnException()

  def createSessionData(self, forceAbsPath=False):
    files = []
    relative = self.act_session_relative.isChecked()
    for f in self.sourcesWidget.files():
      if not forceAbsPath and relative:
        f['filename'] = os.path.relpath(
          f['filename'], os.path.dirname(self.sessionFilename))

      f['sheets'] = [{
        'enabled': sc,
        'index': sw.sheet.idx,
        'xformula': sw.sheet.xFormula.strValue(),
        'yformula': sw.sheet.yFormula.strValue(),
        'errors': sw.sheet.errors
      } for sw, sc in f['sheets']]

      files.append(f)

    r = self.graphWidget.viewRect()
    obj = {
      'relative': relative,
      'files': files,
      'graph': {
        'range': [r.x(), r.y(), r.width(), r.height()]
      },
      'tools': dict([(tw.tool.name, tw.saveState()) for tw in self.toolWidgets]),
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
        try:
          self.restoreState(b64decode(mw['state']), self.saveStateVersion)
        except:
          log.warnException()

      if 'geometry' in mw:
        self.restoreGeometry(b64decode(mw['geometry']))

    if 'filedialogs' in obj:
      fd = obj['filedialogs']
      if 'state' in fd and fd['state'] is not None:
        FileDialog.state = b64decode(fd['state'])
      if 'states' in fd: FileDialog.states.update(fd['states'])

    if 'session' in obj:
      self.loadSession(obj['session'], self.configFilename)

    self.update()
    self.sourcesDockWidget.raise_()

  def saveConfig(self):
    fdstate = None
    if FileDialog.state is not None: fdstate = str(b64encode(FileDialog.state), 'ascii')
    obj = {
      'session': self.createSessionData(True),
      'mainwindow': {
        'state': str(b64encode(self.saveState(self.saveStateVersion)), 'ascii'),
        'geometry': str(b64encode(self.saveGeometry()), 'ascii'),
      },
      'filedialogs': {
        'state': fdstate,
        'states': FileDialog.states
      }
    }
    json.dump(obj, open(self.configFilename, 'w'))
