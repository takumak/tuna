import logging
import inspect
import re
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import \
  QWidget, QLabel, QVBoxLayout, QGridLayout, QLineEdit, QFrame, \
  QCheckBox, QSpinBox, QPushButton, QButtonGroup, QRadioButton, \
  QComboBox, QTableWidgetItem, QAbstractScrollArea, \
  QHeaderView

from tools import NopInterp, CubicSpline, ToolBase, FitTool, IADTool
from commonwidgets import TableWidget
from fit_functions import FitFuncGaussian


class ToolWidgetBase(QWidget):
  plotRequested = pyqtSignal(ToolBase, name='plotRequested')

  def __init__(self):
    super().__init__()
    self.tool = self.toolClass()
    self.tool.cleared.connect(self.clear)
    self.tool.linesUpdated.connect(self.linesUpdated)

  def name(self):
    return self.toolClass.name

  def clear(self):
    pass

  def linesUpdated(self, lines):
    pass


class IADToolWidget(ToolWidgetBase):
  toolClass = IADTool

  def __init__(self):
    super().__init__()

    self.vbox = QVBoxLayout()
    self.setLayout(self.vbox)

    self.linesTable = TableWidget()
    self.linesTable.cellChanged.connect(self.linesTableCellChanged)
    self.vbox.addWidget(self.linesTable)

    self.vbox.addStretch(1)
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    self.vbox.addWidget(line)


    self.optionsGrid = QGridLayout()
    self.vbox.addLayout(self.optionsGrid)

    self.interpComboBox = QComboBox()
    self.interpComboBox.currentIndexChanged.connect(self.interpSelected)
    self.interpOptionsLayout = QVBoxLayout()
    self.interpOptionsLayout.setContentsMargins(40, 0, 0, 0)
    self.optionsGrid.addWidget(QLabel('Interpolation'), 0, 0)
    self.optionsGrid.addWidget(self.interpComboBox, 0, 1)
    self.optionsGrid.addLayout(self.interpOptionsLayout, 1, 0, 1, 2)

    self.interpOptions = []
    for interp in [NopInterp(), CubicSpline()]:
      opt = interp.createOptionsWidget()
      self.interpComboBox.addItem(interp.name, [interp, opt])
      if opt:
        self.interpOptionsLayout.addWidget(opt)
        self.interpOptions.append(opt)
    self.interpComboBox.setCurrentIndex(1)

    self.WCthreshold = QLineEdit()
    self.WCthreshold.setValidator(QDoubleValidator())
    self.WCthreshold.textChanged.connect(lambda t: self.toolSetWCthreshold)
    self.WCthreshold.setText('%g' % self.tool.threshold)
    self.optionsGrid.addWidget(QLabel('WC threshold'), 2, 0)
    self.optionsGrid.addWidget(self.WCthreshold, 2, 1)

    for l, f in [('Plot original', self.plotOriginal),
                 ('Plot with X offset', self.plotXoffset),
                 ('Plot differences', self.plotDifferences),
                 ('Plot IAD', self.plotIAD)]:
      btn = QPushButton(l)
      btn.clicked.connect(f)
      self.vbox.addWidget(btn)

    self.tool.xoffUpdated.connect(self.updateXoff)
    self.tool.iadYUpdated.connect(self.updateIADy)

  def linesTableCellChanged(self, r, c):
    if c == 1:
      self.toolSetIADx()

  def toolSetBase(self):
    self.tool.base = self.selectBaseGroup.checkedId()

  def toolSetIADx(self):
    self.tool.iadX = []
    for x in self.getIADx():
      try:
        x = float(x)
      except:
        x = None
      self.tool.iadX.append(x)

  def toolSetWCthreshold(self):
    self.tool.threshold = float(self.WCthreshold.text())

  def interpSelected(self, idx):
    interp, opt_ = self.interpComboBox.currentData()
    self.tool.interp = interp
    for opt in self.interpOptions:
      if opt == opt_:
        opt.show()
      else:
        opt.hide()

  def clear(self):
    self.linesTable.clear()
    self.linesTable.verticalHeader().hide()
    self.linesTable.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
    self.linesTable.setColumnCount(5)
    self.linesTable.setHorizontalHeaderLabels(['Name', 'IAD X', 'IAD Y', 'X offset', 'Weight center'])
    self.linesTable.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

    self.selectBaseGroup = QButtonGroup()
    self.selectBaseGroup.buttonClicked.connect(lambda b: self.toolSetBase())

  def linesUpdated(self, lines):
    self.linesTable.setRowCount(len(lines) + 1)

    for r, line in enumerate(lines):
      radio = QRadioButton(line.name)
      self.selectBaseGroup.addButton(radio, len(self.selectBaseGroup.buttons()))
      self.linesTable.setCellWidget(r, 0, radio)

      m = re.search(r'^([\+\-]?\d*(?:\.\d+)?)', line.name)
      if m: self.setIADx(r, m.group(1))

    radio.setChecked(True)
    self.toolSetBase()

  def setLinesTableCell(self, r, c, v):
    self.linesTable.setItem(r, c, QTableWidgetItem(str(v)))

  def getLinesTableCol(self, c):
    items = []
    for r in range(self.linesTable.rowCount()):
      item = self.linesTable.item(r, c)
      items.append(item.text() if item else None)
    return items

  def setIADx(self, i, v):
    self.setLinesTableCell(i, 1, v)
    self.toolSetIADx()

  def setIADy(self, i, v):
    self.setLinesTableCell(i, 2, v)

  def setXoff(self, i, v):
    self.setLinesTableCell(i, 3, v)

  def setWC(self, i, v):
    self.setLinesTableCell(i, 4, v)

  def getIADx(self):
    return self.getLinesTableCol(1)

  def updateXoff(self):
    for i, (wc, xoff) in enumerate(zip(self.tool.wc, self.tool.xoff)):
      if i == self.tool.base:
        self.setWC(i, '%g' % wc)
      else:
        b = self.tool.wc[self.tool.base]
        self.setWC(i, '%g%+g' % (b, wc - b))
      self.setXoff(i, '%g' % xoff)

  def updateIADy(self):
    for i, iadY in enumerate(self.tool.iadY):
      self.setIADy(i, '%g' % iadY)

  def plotOriginal(self):
    self.plot('orig')

  def plotXoffset(self):
    self.plot('xoff')

  def plotDifferences(self):
    self.plot('diff')

  def plotIAD(self):
    self.plot('iad')

  def plot(self, mode):
    logging.info('IAD: Plot %s' % mode)
    self.tool.mode = mode
    self.toolSetBase()
    self.toolSetIADx()
    self.toolSetWCthreshold()
    self.plotRequested.emit(self.tool)


class FitToolWidget(ToolWidgetBase):
  toolClass = FitTool

  def __init__(self):
    super().__init__()

    self.vbox = QVBoxLayout()
    self.setLayout(self.vbox)

    self.functions = [FitFuncGaussian]

    self.paramsTable = TableWidget()
    self.paramsTable.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
    self.paramsTable.cellChanged.connect(self.paramsTableCellChanged)
    self.vbox.addWidget(self.paramsTable)
    self.setLastRow()

  def paramsTableCellChanged(self, r, c):
    pass

  def functionSelected(self, row, combo, idx):
    func = combo.itemData(idx)
    if inspect.isclass(func):
      func = func(self.tool.lines)
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
        self.paramsTable.setItem(row, c, QTableWidgetItem(param.name))
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
      combo.addItem(func.name, func)
    self.paramsTable.setCellWidget(n, 0, combo)

  def toolSetFunctions(self):
    self.tool.functions = []
    for r in range(self.paramsTable.rowCount()):
      combo = self.paramsTable.cellWidget(r, 0)
      func = combo.currentData()
      if func:
        self.tool.functions.append(func)
    self.plotRequested.emit(self.tool)
