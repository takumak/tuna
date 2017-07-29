import inspect
from PyQt5.QtWidgets import QVBoxLayout, QHeaderView, QComboBox, \
  QTableWidgetItem

from toolwidgetbase import ToolWidgetBase
from fittool import FitTool
from fitfunctions import *
from commonwidgets import *



class FitToolWidget(ToolWidgetBase):
  toolClass = FitTool

  def __init__(self, view):
    super().__init__()

    self.view = view

    self.vbox = VBoxLayout()
    self.setLayout(self.vbox)

    self.functions = [FitFuncGaussian, FitFuncTwoLines]

    self.paramsTable = TableWidget()
    self.paramsTable.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
    self.paramsTable.cellChanged.connect(self.paramsTableCellChanged)
    self.vbox.addWidget(self.paramsTable)
    self.setLastRow()

  def clear(self):
    pass

  def add(self, data):
    pass

  def paramsTableCellChanged(self, r, c):
    if c < 2 or c % 2 != 0:
      return

    func = self.paramsTable.cellWidget(r, 0).currentData()
    if not func:
      return

    i = c//2-1
    if i >= len(func.params):
      return

    value = float(self.paramsTable.item(r, c).text())
    func.params[i].setValue(value)

  def functionSelected(self, row, combo, idx):
    func = combo.itemData(idx)
    if inspect.isclass(func):
      func = func(self.tool.getLines(), self.view)
      func.parameterChanged.connect(lambda: self.parameterChanged(row, func))
      combo.setItemData(idx, func)
    self.parameterChanged(row, func)
    self.setLastRow()
    self.toolSetFunctions()

  def parameterChanged(self, row, func_):
    func = self.paramsTable.cellWidget(row, 0).currentData()
    if func_ != func: return

    c = 0

    if func:
      ncol = 1 + len(func.params)*2
      if self.paramsTable.columnCount() < ncol:
        self.paramsTable.setColumnCount(ncol)

      for i, param in enumerate(func.params):
        c = 1 + i*2
        self.paramsTable.setItem(row, c, QTableWidgetItem(param.label))
        self.paramsTable.setItem(row, c+1, QTableWidgetItem('%g' % param.value()))
      c += 2

    for i in range(c, self.paramsTable.columnCount()):
      self.paramsTable.setItem(row, i, QTableWidgetItem(''))

  def setLastRow(self):
    n = self.paramsTable.rowCount()

    while True:
      if n == 0:
        self.paramsTable.setColumnCount(1)
        break

      combobox = self.paramsTable.cellWidget(n - 1, 0)
      if combobox.currentData() is None:
        return

      break

    self.paramsTable.setRowCount(n + 1)
    combo = QComboBox()
    combo.addItem('Select', None)
    combo.currentIndexChanged.connect(
      lambda idx: self.functionSelected(n, combo, idx))
    for func in self.functions:
      combo.addItem(func.label, func)
    self.paramsTable.setCellWidget(n, 0, combo)

  def toolSetFunctions(self):
    functions = []
    for r in range(self.paramsTable.rowCount()):
      combo = self.paramsTable.cellWidget(r, 0)
      func = combo.currentData()
      if func:
        functions.append(func)
    self.tool.setFunctions(functions)
    self.plotRequested.emit(self.tool, False)
