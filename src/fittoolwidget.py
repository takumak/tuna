import inspect
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout, QHeaderView, QComboBox, \
  QTableWidgetItem, QLabel

from toolwidgetbase import ToolWidgetBase
from fittool import FitTool
from fitfunctions import *
from commonwidgets import *



class FunctionList(TableWidget):
  functionChanged = pyqtSignal()

  def __init__(self, functions, tool, view):
    super().__init__()

    self.functions = functions
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

  def parameterChanged(self, row, func_):
    func = self.cellWidget(row, 0).currentData()
    if func_ != func: return

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

  def functionSelected(self, row, combo, idx):
    func = combo.itemData(idx)
    if inspect.isclass(func):
      func = func(self.tool.getLines(), self.view)
      func.parameterChanged.connect(lambda: self.parameterChanged(row, func))
      combo.setItemData(idx, func)
    self.parameterChanged(row, func)
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
    for func in self.functions:
      combo.addItem(func.label, func)
    self.setCellWidget(n, 0, combo)

  def getFunctions(self):
    functions = []
    for r in range(self.rowCount()):
      combo = self.cellWidget(r, 0)
      func = combo.currentData()
      if func:
        functions.append(func)
    return functions



class FitToolWidget(ToolWidgetBase):
  toolClass = FitTool
  functions = [FitFuncGaussian, FitFuncTwoLines]

  def __init__(self, view):
    super().__init__()

    vbox = VBoxLayout()
    self.setLayout(vbox)

    self.backgroundList = FunctionList(self.functions, self.tool, view)
    self.backgroundList.setSizeAdjustPolicy(self.backgroundList.AdjustToContents)
    vbox.addWidget(QLabel('Background:'))
    vbox.addWidget(self.backgroundList)

    self.functionList = FunctionList(self.functions, self.tool, view)
    self.functionList.functionChanged.connect(self.toolSetFunctions)
    vbox.addWidget(QLabel('Peaks:'))
    vbox.addWidget(self.functionList)

  def clear(self):
    pass

  def add(self, line):
    pass

  def toolSetFunctions(self):
    self.tool.setFunctions(self.functionList.getFunctions())
    self.plotRequested.emit(self.tool, False)
