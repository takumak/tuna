import logging
import inspect
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QKeySequence, QBrush
from PyQt5.QtWidgets import QVBoxLayout, QHeaderView, QComboBox, \
  QTableWidgetItem, QLabel, QPushButton, QButtonGroup, QWidget, \
  QCheckBox

from functions import blockable
from toolwidgetbase import *
from fittool import FitTool
from commonwidgets import *



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
    self.cellChanged.connect(self.parameterEdited)
    self.itemSelectionChanged.connect(self.updateHighlight)

    vh = self.verticalHeader()
    vh.setSectionsMovable(True)
    vh.sectionMoved.connect(lambda *args: self.functionChanged.emit())
    self.setLastRow()

  def focusInEvent(self, ev):
    super().focusInEvent(ev)
    self.focusIn.emit()

  def focusOutEvent(self, ev):
    super().focusOutEvent(ev)
    self.focusOut.emit()

  @blockable
  def parameterEdited(self, r, c):
    item = self.item(r, c)
    param = item.data(Qt.UserRole)
    if param:
      param.setValue(float(item.text()))

  def setItemText(self, r, c, text, editable=True):
    item = super().item(r, c)
    if item is None:
      item = QTableWidgetItem(text)
      if not editable:
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
      self.setItem(r, c, item)
    else:
      item.setText(text)
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
        self.setItemText(row, c, param.name, editable=False)
        val = self.setItemText(row, c+1, '%g' % param.value())
        val.setData(Qt.UserRole, param)

    for i in range(c+2, self.columnCount()):
      self.setItemText(row, i, '')

    self.parameterEdited.unblock()

  @blockable
  def functionSelected(self, row, combo, idx):
    func = combo.itemData(idx)
    if isinstance(func, str):
      for fc in self.funcClasses:
        if fc.name == func:
          func = self.createFunc(fc.name)
          func.parameterChanged.connect(self.funcParameterChanged)
          func.highlight.connect(self.highlight)
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
    combo = QComboBox()
    combo.addItem('Select', None)
    combo.currentIndexChanged.connect(
      lambda idx: self.functionSelected(n, combo, idx))
    for fc in self.funcClasses:
      combo.addItem(fc.label, fc.name)
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
    self.setColumnCount(0)
    self.setRowCount(0)

    self.functionSelected.block()
    for r, func in enumerate(functions):
      combo = self.setLastRow()
      for i in range(combo.count()):
        fname = combo.itemData(i)
        if fname == func.name:
          combo.setItemData(i, func)
          combo.setCurrentIndex(i)
          func.parameterChanged.connect(self.funcParameterChanged)
          func.highlight.connect(self.highlight)
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



class FitToolWidget(ToolWidgetBase):
  toolClass = FitTool

  def __init__(self, view):
    super().__init__()
    self.tool.setView(view)

    vbox = VBoxLayout()
    vbox.setContentsMargins(4, 4, 4, 4)
    self.setLayout(vbox)

    self.normWindow = FunctionList(self.tool.funcClasses, self.tool.createFunction)
    self.normWindow.functionChanged.connect(self.toolSetNormWindow)
    self.normWindow.focusIn.connect(lambda: self.setPlotMode('normwin'))
    self.toolSetNormWindow()
    vbox.addWidget(QLabel('Normalize window'))
    vbox.addWidget(self.normWindow)

    vbox.addWidget(HSeparator())

    self.bgsub = MethodSelectorBGSub()
    self.bgsub.selectionChanged.connect(
      lambda: self.tool.setBGSub(self.bgsub.currentItem()))
    self.addMethodSelector(self.bgsub)
    vbox.addWidget(self.bgsub)

    vbox.addWidget(HSeparator())

    self.lineSelector = LineSelector()
    self.lineSelector.selectionChanged.connect(self.lineSelectionChanged)
    vbox.addWidget(QLabel('Peaks'))
    vbox.addWidget(self.lineSelector)

    self.pressureBox = HBoxLayout()
    self.pressureWidgets = {}
    hbox = HBoxLayout()
    hbox.addWidget(QLabel('Pressure'))
    hbox.addLayout(self.pressureBox)
    vbox.addLayout(hbox)

    self.peakFunctions = FunctionList(self.tool.funcClasses, self.tool.createFunction)
    self.peakFunctions.functionChanged.connect(self.toolSetPeakFunctions)
    self.peakFunctions.focusIn.connect(lambda: self.setPlotMode('peaks'))
    self.peakFunctions.itemSelectionChanged.connect(self.toolSetPlotParams)
    self.peakFunctions.addAction(
      '&Optimize selected parameters',
      self.optimize, QKeySequence('Ctrl+Enter,Ctrl+Return'))
    vbox.addWidget(self.peakFunctions)

    self.optimizeCombo = QComboBox()
    for name in self.tool.optimizeMethods:
      self.optimizeCombo.addItem(name)
    self.optimizeCombo.currentIndexChanged.connect(self.setOptimizeMethod)
    self.optimizeCombo.setCurrentIndex(0)
    self.setOptimizeMethod()
    hbox = HBoxLayout()
    hbox.addWidget(QLabel('Optimize'))
    hbox.addWidget(self.optimizeCombo)
    hbox.addWidget(QLabel('Tolerance'))
    hbox.addWidget(self.tool.optimize_tol.getWidget())
    hbox.addWidget(QLabel('Curr diff square sum'))
    hbox.addWidget(self.tool.diffSquareSum.getWidget())
    hbox.addStretch(1)
    vbox.addLayout(hbox)

    self.plotParams = QCheckBox('Plot Pressure vs Parameters')
    self.plotParams.toggled.connect(self.toolSetPlotParams)
    vbox.addWidget(self.plotParams)

    vbox.addStretch(1)

  def setOptimizeMethod(self):
    self.tool.optimizeMethod = self.optimizeCombo.currentText()

  def clear(self):
    self.lineSelector.clear()
    while self.pressureBox.count() > 0:
      self.pressureBox.takeAt(0)
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

  def toolSetPlotParams(self, *args):
    params = []
    if self.plotParams.isChecked():
      for item in self.peakFunctions.selectedItems():
        p = item.data(Qt.UserRole)
        if p:
          params.append(p)

    if len(params) == 0: params = None
    if params != self.tool.plotParams:
      self.tool.plotParams = params
      self.plotRequested.emit(self.tool, True)

  def lineSelectionChanged(self):
    line = self.lineSelector.selectedLine()
    self.tool.setActiveLineName(line.name if line else None)
    self.plotRequested.emit(self.tool, False)
    self.setUpdatesEnabled(False)
    for name, pw in self.pressureWidgets.items():
      pw.setVisible(name == line.name)
    self.setUpdatesEnabled(True)

  def optimize(self):
    params = self.peakFunctions.selectedParameters()
    if len(params) == 0:
      logging.error('Select parameters to optimize')
      return
    self.tool.optimize(params)

  def restoreState(self, state):
    super().restoreState(state)
    self.normWindow.setFunctions(self.tool.normWindow)
    self.peakFunctions.setFunctions(self.tool.peakFunctions)
