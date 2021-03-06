import logging
import inspect
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QKeySequence, QBrush
from PyQt5.QtWidgets import QVBoxLayout, QHeaderView, QComboBox, \
  QTableWidgetItem, QLabel, QPushButton, QButtonGroup, QWidget, \
  QCheckBox, QTabWidget

from functions import blockable
from toolwidgetbase import *
from fittool import FitTool
from commonwidgets import *
from fitparameters import FitParam



class FunctionList(TableWidget):
  functionChanged = pyqtSignal()
  focusIn = pyqtSignal()
  focusOut = pyqtSignal()

  def __init__(self, funcClasses, createFunc):
    super().__init__()
    self.setSizeAdjustPolicy(self.AdjustToContents)

    self.funcClasses = funcClasses
    self.createFunc = createFunc

    self.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
    self.itemChanged.connect(self.parameterEdited)
    self.itemSelectionChanged.connect(self.updateHighlight)

    vh = self.verticalHeader()
    vh.setSectionsMovable(True)
    vh.sectionMoved.connect(lambda *args: self.functionChanged.emit())
    self.setLastRow()

  def clear(self):
    super().clear()
    self.setColumnCount(0)
    self.setRowCount(0)
    self.setLastRow()

  def focusInEvent(self, ev):
    super().focusInEvent(ev)
    self.focusIn.emit()

  def focusOutEvent(self, ev):
    super().focusOutEvent(ev)
    self.focusOut.emit()

  @blockable
  def parameterEdited(self, item):
    param = item.data(Qt.UserRole)
    if not isinstance(param, FitParam): return

    text = item.text()
    if text != item.data(Qt.UserRole+1):
      param.setValue(float(text))

  def setItemText(self, r, c, text, editable=True):
    item = super().item(r, c)
    if item is None:
      item = QTableWidgetItem(text)
      self.setItem(r, c, item)
    else:
      item.setText(text)

    f = item.flags()
    if editable:
      f |= Qt.ItemIsEditable
    else:
      f &= ~Qt.ItemIsEditable
    item.setFlags(f)

    return item

  def getFuncRow(self, func):
    for row in range(self.rowCount()):
      f = self.cellWidget(row, 0).currentData()
      if f == func:
        return row
    return None

  def funcParameterChanged(self, func):
    row = self.getFuncRow(func)
    if row is None:
      return

    self.parameterEdited.block()

    c = -1
    if func:
      params = func.editableParams()
      ncol = 1 + len(params)*2
      if self.columnCount() < ncol:
        self.setColumnCount(ncol)

      for i, param in enumerate(params):
        c = 1 + i*2
        self.setItemText(row, c, param.label, editable=False)
        valtext = '%g' % param.value()
        val = self.setItemText(row, c+1, valtext)
        val.setData(Qt.UserRole, param)
        val.setData(Qt.UserRole+1, valtext)

        f = val.flags()
        if param.readOnly:
          f &= ~Qt.ItemIsEditable
        else:
          f |= Qt.ItemIsEditable
        val.setFlags(f)

    for i in range(c+2, self.columnCount()):
      item = self.setItemText(row, i, '', editable=False)
      item.setData(Qt.UserRole, None)

    self.parameterEdited.unblock()

  @blockable
  def functionSelected(self, row, combo, idx):
    func = combo.itemData(idx)
    if isinstance(func, str):
      for fc in self.funcClasses:
        if fc.name == func:
          func = self.createFunc(fc.name)
          func.parameterChanged.connect(self.funcParameterChanged)
          func.highlightChanged.connect(self.highlight)
          combo.setItemData(idx, func)
          break
      else:
        raise RuntimeError('Function named "%s" is not defined' % func)
    self.funcParameterChanged(func)
    self.setLastRow()
    self.functionChanged.emit()

  def setLastRow(self):
    n = self.rowCount()

    if n == 0:
      self.setColumnCount(1)
    else:
      combo = self.cellWidget(n - 1, 0)
      if combo.currentData() is None:
        return combo

    self.setRowCount(n + 1)
    combo = ComboBoxWithDescriptor()
    combo.addItem('Select', None)
    combo.currentIndexChanged.connect(
      lambda idx: self.functionSelected(n, combo, idx))
    for fc in self.funcClasses:
      combo.addItem(fc.label, fc.name)
      combo.setItemData(combo.count()-1, fc.getDescriptorWidget(), Qt.UserRole+1)
    self.setCellWidget(n, 0, combo)
    return combo

  def getFunctions(self):
    functions = []
    for r in range(self.rowCount()):
      combo = self.cellWidget(r, 0)
      func = combo.currentData()
      if func:
        functions.append((func, self.visualRow(r)))
    return [f for f, r in sorted(functions, key=lambda p: p[1])]

  def setFunctions(self, functions):
    self.clear()

    self.functionSelected.block()
    for r, func in enumerate(functions):
      combo = self.setLastRow()
      for i in range(combo.count()):
        fname = combo.itemData(i)
        if fname == func.name:
          combo.setItemData(i, func)
          combo.setCurrentIndex(i)
          func.parameterChanged.connect(self.funcParameterChanged)
          func.highlightChanged.connect(self.highlight)
          self.funcParameterChanged(func)
          break
    self.functionSelected.unblock()
    self.setLastRow()

  def selectedParameters(self):
    params = []
    for item in self.selectedItems():
      param = item.data(Qt.UserRole)
      if param:
        params.append(param)
    return params

  def highlight(self, func, on):
    import pyqtgraph as pg
    row = self.getFuncRow(func)
    if row is None:
      return
    for c in range(self.columnCount()):
      item = self.item(row, c)
      if item:
        item.setBackground(pg.mkBrush(color='#ddd') if on else QBrush())

  def updateHighlight(self):
    rows = set([item.row() for item in self.selectedItems()])
    for r in range(self.rowCount()):
      combo = self.cellWidget(r, 0)
      func = combo.currentData()
      if func:
        func.setHighlighted(r in rows)



class LineSelector(QWidget):
  selectionChanged = pyqtSignal()

  def __init__(self):
    super().__init__()
    self.layout = FlowLayout()
    self.setLayout(self.layout)
    self.buttons = []

  def clear(self):
    while self.layout.count() > 0:
      self.layout.takeAt(0)
    self.buttons = []

  def add(self, line, active):
    btn = QPushButton(line.name)
    btn.setCheckable(True)
    btn.setChecked(active)
    btn.pressed.connect(lambda: self.unselectAll(btn))
    btn.toggled.connect(self.buttonToggled)
    self.layout.addWidget(btn)
    self.buttons.append((btn, line))

  @blockable
  def buttonToggled(self, checked):
    self.selectionChanged.emit()

  def unselectAll(self, exclude):
    self.buttonToggled.block()
    for btn, line in self.buttons:
      if btn != exclude:
        btn.setChecked(False)
    self.buttonToggled.unblock()

  def selectedLine(self):
    for btn, line in self.buttons:
      if btn.isChecked():
        return line
    return None



class PlotLabelsTable(TableWidget):
  def __init__(self):
    super().__init__()

    self.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
    self.setSizeAdjustPolicy(self.AdjustToContents)

    self.setColumnCount(2)
    self.setRowCount(2)
    self.setHorizontalHeaderLabels(['X label', 'Y label'])
    self.setVerticalHeaderLabels(['Source', 'Parameter'])

    self.sourceX = QTableWidgetItem('Energy (eV)')
    self.sourceY = QTableWidgetItem('Intensity (a.u.)')
    self.paramX = QTableWidgetItem('Pressure (GPa)')
    self.paramY = QTableWidgetItem('')

    self.setItem(0, 0, self.sourceX)
    self.setItem(0, 1, self.sourceY)
    self.setItem(1, 0, self.paramX)
    self.setItem(1, 1, self.paramY)

    self.setParams([])

    self.itemChanged.connect(self.edited)

  def setParams(self, params):
    self.params = params

    self.edited.block()
    flags = self.paramY.flags()
    if len(params) == 0:
      flags &= ~Qt.ItemIsEnabled
      self.paramY.setText('')
    else:
      flags |= Qt.ItemIsEnabled
      labels = list(set([p.plotLabel for p in self.params]))
      label = labels[0] if len(labels) == 1 else None
      self.paramY.setText(label or '')
    self.paramY.setFlags(flags)
    self.edited.unblock()

  @blockable
  def edited(self, item):
    if item == self.paramY and len(self.params) > 0:
      for p in self.params:
        p.plotLabel = self.paramY.text()



class FitToolWidget(ToolWidgetBase):
  toolClass = FitTool

  def __init__(self, graphWidget):
    super().__init__(graphWidget)

    vbox = VBoxLayout()
    vbox.setContentsMargins(4, 4, 4, 4)
    self.setLayout(vbox)

    for name in 'BGSub', 'Smooth':
      sel = globals()['MethodSelector%s' % name]()
      setattr(self, name.lower(), sel)
      sel.selectionChanged.connect((
        lambda n, s: (
          lambda: self.tool.setMethod(n.lower(), s.currentItem())
        )
      )(name, sel))
      self.addMethodSelector(sel)
      vbox.addWidget(sel)
      setattr(self.tool, name.lower(), sel.currentItem())

    vbox.addWidget(HSeparator())

    self.normWindow = FunctionList(self.tool.funcClasses, self.tool.createFunction)
    self.normWindow.functionChanged.connect(self.toolSetNormWindow)
    self.normWindow.focusIn.connect(lambda: self.setPlotMode('normwin'))
    self.toolSetNormWindow()
    vbox.addWidget(ExpanderWidget('Normalize window', self.normWindow))

    vbox.addWidget(HSeparator())

    vbox.addWidget(QLabel('Fit target'))

    self.lineSelector = LineSelector()
    self.lineSelector.selectionChanged.connect(self.lineSelectionChanged)
    vbox.addWidget(self.lineSelector)

    self.pressureBox = HBoxLayout()
    self.pressureWidgets = {}
    hbox = HBoxLayout()
    hbox.addWidget(QLabel('Pressure'))
    hbox.addLayout(self.pressureBox)
    hbox.addStretch(1)
    vbox.addLayout(hbox)

    vbox.addWidget(HSeparator())

    vbox.addWidget(QLabel('Fit functions'))

    self.peakFunctions = FunctionList(self.tool.funcClasses, self.tool.createFunction)
    self.peakFunctions.functionChanged.connect(self.toolSetPeakFunctions)
    self.peakFunctions.focusIn.connect(lambda: self.setPlotMode('peaks'))
    self.peakFunctions.itemSelectionChanged.connect(self.paramsSelected)
    self.peakFunctions.addAction(
      '&Optimize selected parameters',
      lambda: self.optimize(1),
      QKeySequence('Ctrl+Enter,Ctrl+Return')
    )
    self.peakFunctions.addAction('Copy in &JSON', self.copyJSON, QKeySequence.UnknownKey)
    vbox.addWidget(self.peakFunctions)

    self.plotParams = QCheckBox('Plot Pressure vs Parameters')
    self.plotParams.toggled.connect(self.toolSetPlotParams)
    vbox.addWidget(self.plotParams)

    tab = QTabWidget()
    for tablabel in 'Optimize', 'Intersections', 'Peak position', 'Export':
      vbox2 = VBoxLayout(hmargins=True)
      getattr(self, 'maketab_%s' % tablabel.replace(' ', '_').lower())(vbox2)
      vbox2.addStretch(1)
      page = QWidget()
      page.setLayout(vbox2)
      tab.addTab(page, tablabel)
    vbox.addWidget(tab)

    vbox.addStretch(1)

    self.paramsSelected()

  def maketab_optimize(self, vbox):
    self.optimizeCombo = QComboBox()
    for name in self.tool.optimizeMethods:
      self.optimizeCombo.addItem(name)
    self.optimizeCombo.currentIndexChanged.connect(self.setOptimizeMethod)
    self.optimizeCombo.setCurrentIndex(0)
    self.setOptimizeMethod()

    hbox = HBoxLayout()
    hbox.addWidget(QLabel('Method'))
    hbox.addWidget(self.optimizeCombo)
    hbox.addWidget(QLabel('R^2'))
    hbox.addWidget(self.tool.R2.getWidget())
    hbox.addWidget(QLabel('IAD'))
    hbox.addWidget(self.tool.IAD.getWidget())
    hbox.addStretch(1)
    vbox.addLayout(hbox)

    hbox = HBoxLayout()
    hbox.addWidget(QLabel('Constraints'))
    hbox.addWidget(self.tool.constraints.getWidget())
    vbox.addLayout(hbox)

    hbox = HBoxLayout()
    hbox.addWidget(QLabel('Fit range'))
    hbox.addWidget(self.tool.fitRange.getWidget())
    hbox.addStretch(1)
    vbox.addLayout(hbox)

    self.optimize1Btn = QPushButton('Optimize')
    self.optimize1Btn.pressed.connect(lambda: self.optimize(1))
    self.optimizeAutoBtn = QPushButton()
    self.optimizeAutoBtn.pressed.connect(lambda: self.optimize(-1, toggle=True))
    self.optimizeStatus = QLabel()
    hbox = HBoxLayout()
    hbox.addWidget(self.optimize1Btn)
    hbox.addWidget(self.optimizeAutoBtn)
    hbox.addWidget(self.optimizeStatus)
    hbox.addStretch(1)
    vbox.addLayout(hbox)
    self.optimizeCnt = 0
    self.optimizeFinished()

  def maketab_intersections(self, vbox):
    hbox = HBoxLayout()
    hbox.addWidget(QLabel('f(x)='))
    hbox.addWidget(self.tool.isecFunc.getWidget())
    vbox.addLayout(hbox)
    self.isec_table = TableWidget()
    vbox.addWidget(self.isec_table)
    calcbtn = QPushButton('Calc')
    calcbtn.clicked.connect(self.tool.calcIntersections)
    vbox.addWidget(calcbtn)

    self.updateIsecTable()
    self.tool.intersectionsUpdated.connect(self.updateIsecTable)

  def updateIsecTable(self):
    tbl = self.isec_table
    tbl.setColumnCount(3)
    tbl.setRowCount(len(self.tool.isecPoints))

    for i, (line, pts) in enumerate(self.tool.isecPoints):
      tbl.setItem(i, 0, QTableWidgetItem(line.name))
      for j, (x, y) in enumerate(pts):
        if tbl.columnCount() <= j*2+2:
          tbl.setColumnCount(j*2+3)
        tbl.setItem(i, j*2+1, QTableWidgetItem(str(x)))
        tbl.setItem(i, j*2+2, QTableWidgetItem(str(y)))

  def maketab_peak_position(self, vbox):
    self.peak_pos_table = TableWidget()
    vbox.addWidget(self.peak_pos_table)
    self.updatePeakPosTable()
    self.tool.peakPositionsUpdated.connect(self.updatePeakPosTable)

  def updatePeakPosTable(self):
    tbl = self.peak_pos_table
    tbl.setColumnCount(3)
    tbl.setRowCount(len(self.tool.peakPos))

    for i, (line, (x, y)) in enumerate(self.tool.peakPos):
      tbl.setItem(i, 0, QTableWidgetItem(line.name))
      tbl.setItem(i, 1, QTableWidgetItem(str(x)))
      tbl.setItem(i, 2, QTableWidgetItem(str(y)))

  def maketab_export(self, vbox):
    self.plotModeCombo = QComboBox()
    self.plotModeCombo.currentIndexChanged.connect(self.plotModeSelected)
    self.plotModeCombo.addItem('Select...', None)
    for value, label in FitParam.plotModes:
      self.plotModeCombo.addItem(label, value)
    hbox = HBoxLayout()
    hbox.addWidget(QLabel('Plot Pressure vs Selected parameters'))
    hbox.addWidget(self.plotModeCombo)
    vbox.addLayout(hbox)

    self.plotLabelsTable = PlotLabelsTable()
    vbox.addWidget(self.plotLabelsTable)

    hbox = HBoxLayout()
    btn = QPushButton('Export xlsx')
    btn.clicked.connect(self.exportXlsx)
    hbox.addWidget(btn)
    vbox.addLayout(hbox)

  def setOptimizeMethod(self):
    self.tool.optimizeMethod = self.optimizeCombo.currentText()

  def clear(self):
    self.lineSelector.clear()
    while self.pressureBox.count() > 0:
      pw = self.pressureBox.takeAt(0).widget()
      pw.close()
    self.pressureWidgets = {}

  def add(self, line):
    active = line.name == self.tool.activeLineName
    self.lineSelector.add(line, active)
    pw = self.tool.getPressure(line.name).getWidget()
    pw.setVisible(active)
    self.pressureBox.addWidget(pw)
    self.pressureWidgets[line.name] = pw

  def toolSetNormWindow(self):
    self.tool.setNormWindow(self.normWindow.getFunctions())
    self.plotRequested.emit(self.tool, False)

  def toolSetPeakFunctions(self):
    self.tool.setPeakFunctions(self.peakFunctions.getFunctions())
    self.plotRequested.emit(self.tool, False)

  def setPlotMode(self, mode):
    if self.tool.mode != mode:
      self.tool.mode = mode
      self.plotRequested.emit(self.tool, False)

  def selectedParams(self):
    params = []
    for item in self.peakFunctions.selectedItems():
      p = item.data(Qt.UserRole)
      if p:
        params.append(p)
    return params

  def toolSetPlotParams(self, *args):
    params = None
    if self.plotParams.isChecked():
      params = self.selectedParams()
      if len(params) == 0:
        params = None

    if params != self.tool.plotParams:
      self.tool.plotParams = params
      self.plotRequested.emit(self.tool, True)

  def paramsSelected(self, *args):
    self.toolSetPlotParams()

    params = self.selectedParams()
    self.plotLabelsTable.setParams(params)
    if len(params) == 0:
      self.plotModeCombo.setEnabled(False)
      return
    else:
      self.plotModeCombo.setEnabled(True)

    modes = list(set([p.plotMode for p in params]))
    self.plotModeSelected.block()
    try:
      if len(modes) == 1:
        for i in range(1, self.plotModeCombo.count()):
          mode = self.plotModeCombo.itemData(i)
          if mode == modes[0]:
            self.plotModeCombo.setCurrentIndex(i)
            return
      self.plotModeCombo.setCurrentIndex(0)
    finally:
      self.plotModeSelected.unblock()

  @blockable
  def plotModeSelected(self, *args):
    mode = self.plotModeCombo.currentData()
    for p in self.selectedParams():
      p.plotMode = mode
    if self.plotParams.isChecked():
      self.plotRequested.emit(self.tool, True)

  def lineSelectionChanged(self):
    line = self.lineSelector.selectedLine()
    self.tool.setActiveLineName(line.name if line else None)
    self.plotRequested.emit(self.tool, False)
    self.setUpdatesEnabled(False)
    for name, pw in self.pressureWidgets.items():
      pw.setVisible(bool(line and name == line.name))
    self.setUpdatesEnabled(True)
    self.peakFunctions.setFocus()

  def optimize(self, cnt, toggle=False):
    if self.optimizeCnt != 0:
      if toggle: self.optimizeCnt = 0
      return

    params = [p for p in self.peakFunctions.selectedParameters() if not p.readOnly]
    if len(params) == 0:
      raise RuntimeError('Select parameters to optimize')

    self.optimizeCnt = cnt

    prevRes = ['#']

    def callback(success, resparams, resvalues):
      self.peakFunctions.setFocus()

      if not success or self.optimizeCnt == 0:
        self.optimizeFinished()
        return

      if self.optimizeCnt < 0:
        res = ','.join(map(str, resvalues))
        if res == prevRes[0]:
          self.optimizeFinished()
          return
        prevRes[0] = res

      self.optimize1Btn.setEnabled(False)
      if self.optimizeCnt < 0:
        self.optimizeAutoBtn.setText('Cancel')
        self.optimizeStatus.setText('Running... %d' % (-self.optimizeCnt - 1))
      else:
        self.optimizeAutoBtn.setEnabled(False)
        self.optimizeStatus.setText('Running...')

      self.optimizeCnt -= 1
      try:
        self.tool.optimize(params, callback)
      except:
        self.optimizeFinished()
        raise

    callback(True, [], [])

  def optimizeFinished(self):
    self.optimize1Btn.setEnabled(True)
    self.optimizeAutoBtn.setText('Auto run')
    self.optimizeAutoBtn.setEnabled(True)
    self.optimizeStatus.setText('')
    self.optimizeCnt = 0

  def copyJSON(self):
    params = self.peakFunctions.selectedParameters()
    funcs = self.peakFunctions.getFunctions()
    obj = []
    for i, func in enumerate(funcs):
      obj.append((i+1, dict([(p.name, p.value()) for p in params if p in func.params])))

    import json
    from PyQt5.QtWidgets import QApplication
    QApplication.clipboard().setText(json.dumps(obj))

  def writeXlsx(self, wb):
    from fitxlsxexporter import FitXlsxExporter
    exporter = FitXlsxExporter(self.tool)
    exporter.setXlabel('source', self.plotLabelsTable.sourceX.text())
    exporter.setYlabel('source', self.plotLabelsTable.sourceY.text())
    exporter.setXlabel('param', self.plotLabelsTable.paramX.text())
    exporter.write(wb)

  def newSession(self):
    super().newSession()
    self.normWindow.clear()
    self.peakFunctions.clear()
    self.bgsub.combo.setCurrentIndex(0)

  def saveState(self):
    state = super().saveState()
    state['plot_labels'] = {
      'source': (self.plotLabelsTable.sourceX.text(), self.plotLabelsTable.sourceY.text()),
      'paramX': self.plotLabelsTable.paramX.text()
    }
    return state

  def restoreState(self, state):
    super().restoreState(state)

    self.normWindow.setFunctions(self.tool.normWindow)
    self.peakFunctions.setFunctions(self.tool.peakFunctions)

    if 'plot_labels' in state:
      labels = state['plot_labels']
      if 'source' in labels:
        x, y = labels['source']
        self.plotLabelsTable.sourceX.setText(x)
        self.plotLabelsTable.sourceY.setText(y)
      if 'paramX' in labels:
        self.plotLabelsTable.paramX.setText(labels['paramX'])
