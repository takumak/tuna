import logging
import inspect
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QVBoxLayout, QHeaderView, QComboBox, \
  QTableWidgetItem, QLabel, QPushButton, QButtonGroup, QWidget

from toolwidgetbase import ToolWidgetBase
from fittool import FitTool
from commonwidgets import *



class FunctionList(TableWidget):
  functionChanged = pyqtSignal()

  def __init__(self, tool):
    super().__init__()
    self.tool = tool

    self.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
    self.cellChanged.connect(self.parameterEdited)

    vh = self.verticalHeader()
    vh.setSectionsMovable(True)
    vh.setDragEnabled(True)
    vh.setDragDropMode(self.InternalMove)
    self.setLastRow()

  def parameterEdited(self, r, c):
    item = self.item(r, c)
    param = item.data(Qt.UserRole)
    if param:
      param.setValue(value)

  def funcParameterChanged(self, row, func_):
    func = self.cellWidget(row, 0).currentData()
    if func_ != func: return

    self.blockSignals(True)

    c = 0

    if func:
      params = func.editableParams()
      ncol = 1 + len(params)*2
      if self.columnCount() < ncol:
        self.setColumnCount(ncol)

      for i, param in enumerate(params):
        c = 1 + i*2
        label = QTableWidgetItem(param.label)
        label.setFlags(label.flags() & ~Qt.ItemIsEditable)
        val = QTableWidgetItem('%g' % param.value())
        val.setData(Qt.UserRole, param)
        self.setItem(row, c, label)
        self.setItem(row, c+1, val)
      c += 2

    for i in range(c, self.columnCount()):
      self.setItem(row, i, QTableWidgetItem(''))

    self.blockSignals(False)

  def functionSelected(self, row, combo, idx):
    func = combo.itemData(idx)
    if isinstance(func, str):
      func = self.tool.addFunction(func)
      func.parameterChanged.connect(lambda: self.funcParameterChanged(row, func))
      combo.setItemData(idx, func)
    self.funcParameterChanged(row, func)
    self.setLastRow()
    self.functionChanged.emit()

  def setLastRow(self):
    n = self.rowCount()

    while True:
      if n == 0:
        self.setColumnCount(1)
        break

      combo = self.cellWidget(n - 1, 0)
      if combo.currentData() is None:
        return combo

      break

    self.setRowCount(n + 1)
    combo = QComboBox()
    combo.addItem('Select', None)
    combo.currentIndexChanged.connect(
      lambda idx: self.functionSelected(n, combo, idx))
    for funcC in self.tool.funcClasses:
      combo.addItem(funcC.label, funcC.name)
    self.setCellWidget(n, 0, combo)
    return combo

  def getFunctions(self):
    functions = []
    for r in range(self.rowCount()):
      combo = self.cellWidget(r, 0)
      func = combo.currentData()
      if func:
        functions.append(func)
    return functions

  def setFunctions(self, functions):
    self.clear()
    self.setColumnCount(0)
    self.setRowCount(0)

    for r, func in enumerate(functions):
      combo = self.setLastRow()
      for i in range(combo.count()):
        fname = combo.itemData(i)
        if fname == func.name:
          combo.setItemData(i, func)
          combo.setCurrentIndex(i)
          func.parameterChanged.connect(lambda: self.funcParameterChanged(r, func))
          break

  def selectedParameters(self):
    params = []
    for item in self.selectedItems():
      param = item.data(Qt.UserRole)
      if param:
        params.append(param)
    return params



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
    btn.toggled.connect(lambda: self.selectionChanged.emit())
    self.layout.addWidget(btn)
    self.buttons.append((btn, line))

  def unselectAll(self, exclude):
    self.blockSignals(True)
    for btn, line in self.buttons:
      if btn != exclude:
        btn.setChecked(False)
    self.blockSignals(False)

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

    self.lineSelector = LineSelector()
    self.lineSelector.selectionChanged.connect(self.lineSelectionChanged)
    vbox.addWidget(self.lineSelector)

    self.functionList = FunctionList(self.tool)
    self.functionList.functionChanged.connect(self.toolSetFunctions)
    self.functionList.addAction(
      '&Optimize selected parameters',
      self.optimize, QKeySequence('Ctrl+Enter,Ctrl+Return'))
    vbox.addWidget(self.functionList)

  def clear(self):
    self.lineSelector.clear()

  def add(self, line):
    self.lineSelector.add(line, line.name == self.tool.activeLineName)

  def toolSetFunctions(self):
    self.tool.setFunctions(self.functionList.getFunctions())
    self.plotRequested.emit(self.tool, False)

  def lineSelectionChanged(self):
    line = self.lineSelector.selectedLine()
    self.functionList.setEnabled(bool(line))
    self.tool.setActiveLineName(line.name if line else None)
    self.plotRequested.emit(self.tool, False)

  def restoreState(self, state):
    super().restoreState(state)
    self.functionList.setFunctions(self.tool.functions)

  def optimize(self):
    params = self.functionList.selectedParameters()
    if len(params) == 0:
      logging.error('Select parameters to optimize')
      return
    self.tool.optimize(params)
