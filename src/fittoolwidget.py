import logging
import inspect
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QVBoxLayout, QHeaderView, QComboBox, \
  QTableWidgetItem, QLabel, QPushButton, QButtonGroup, QWidget

from toolwidgetbase import ToolWidgetBase
from fittool import FitTool
from commonwidgets import *



class FunctionList(TableWidget):
  functionChanged = pyqtSignal()

  def __init__(self, funcClasses, tool, view):
    super().__init__()

    self.funcClasses = funcClasses
    self.tool = tool
    self.view = view

    self.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
    self.cellChanged.connect(self.parameterEdited)

    vh = self.verticalHeader()
    vh.setSectionsMovable(True)
    vh.setDragEnabled(True)
    vh.setDragDropMode(self.InternalMove)
    self.setLastRow()

  def parameterEdited(self, r, c):
    if c < 2 or c % 2 != 0:
      return

    func = self.cellWidget(r, 0).currentData()
    if not func:
      return

    i = c//2-1
    if i >= len(func.params):
      return

    value = float(self.item(r, c).text())
    func.params[i].setValue(value)

  def funcParameterChanged(self, row, func_):
    func = self.cellWidget(row, 0).currentData()
    if func_ != func: return

    self.blockSignals(True)

    c = 0

    if func:
      ncol = 1 + len(func.params)*2
      if self.columnCount() < ncol:
        self.setColumnCount(ncol)

      for i, param in enumerate(func.params):
        c = 1 + i*2
        self.setItem(row, c, QTableWidgetItem(param.label))
        self.setItem(row, c+1, QTableWidgetItem('%g' % param.value()))
      c += 2

    for i in range(c, self.columnCount()):
      self.setItem(row, i, QTableWidgetItem(''))

    self.blockSignals(False)

  def functionSelected(self, row, combo, idx):
    func = combo.itemData(idx)
    if inspect.isclass(func):
      func = func(self.tool.getLines(), self.view)
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

      combobox = self.cellWidget(n - 1, 0)
      if combobox.currentData() is None:
        return

      break

    self.setRowCount(n + 1)
    combo = QComboBox()
    combo.addItem('Select', None)
    combo.currentIndexChanged.connect(
      lambda idx: self.functionSelected(n, combo, idx))
    for funcC in self.funcClasses:
      combo.addItem(funcC.label, funcC)
    self.setCellWidget(n, 0, combo)

  def getFunctions(self):
    functions = []
    for r in range(self.rowCount()):
      combo = self.cellWidget(r, 0)
      func = combo.currentData()
      if func:
        functions.append(func)
    return functions



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

    vbox = VBoxLayout()
    vbox.setContentsMargins(4, 4, 4, 4)
    self.setLayout(vbox)

    self.lineSelector = LineSelector()
    self.lineSelector.selectionChanged.connect(self.lineSelectionChanged)
    vbox.addWidget(self.lineSelector)

    self.functionList = FunctionList(self.tool.funcClasses, self.tool, view)
    self.functionList.functionChanged.connect(self.toolSetFunctions)
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
    self.tool.setActiveLineName(line.name)
    self.plotRequested.emit(self.tool, False)
