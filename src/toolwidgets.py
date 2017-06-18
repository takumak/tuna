import re
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import \
  QWidget, QLabel, QVBoxLayout, QGridLayout, QLineEdit, QFrame, \
  QCheckBox, QSpinBox, QPushButton, QButtonGroup, QRadioButton, \
  QComboBox, QTableWidgetItem, QAbstractScrollArea, \
  QHeaderView

from log import log
from tools import NopInterp, CubicSpline, ToolBase, FitTool, IADTool
from commonwidgets import TableWidget


class ToolWidgetBase(QWidget):
  plotRequested = pyqtSignal(ToolBase, name='plotRequested')

  def __init__(self):
    super().__init__()
    self.tool = self.toolClass()
    self.tool.cleared.connect(self.clear)
    self.tool.added.connect(self.add)

  def name(self):
    return self.toolClass.name

  def clear(self):
    raise NotImplementedError()

  def add(self, data):
    raise NotImplementedError()


class FitToolWidget(ToolWidgetBase):
  toolClass = FitTool

  def __init__(self):
    super().__init__()

  def clear(self):
    pass

  def add(self, data):
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
    self.WCthreshold.textChanged.connect(lambda t: self.updateWCthreshold)
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

  def linesTableCellChanged(self, r, c):
    if c == 1:
      self.updateIADx()

  def updateBase(self):
    self.tool.base = self.selectBaseGroup.checkedId()

  def updateIADx(self):
    self.tool.iadX = []
    for x in self.getIADx():
      try:
        x = float(x)
      except:
        x = None
      self.tool.iadX.append(x)

  def updateWCthreshold(self):
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
    self.linesTable.setColumnCount(4)
    self.linesTable.setHorizontalHeaderLabels(['Name', 'IAD X', 'Weight center', 'X offset'])
    self.linesTable.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

    self.selectBaseGroup = QButtonGroup()
    self.selectBaseGroup.buttonClicked.connect(lambda b: self.updateBase)
    self.lines = []

  def add(self, data):
    r = len(self.lines)
    radio = QRadioButton(data.name)
    self.linesTable.setRowCount(r + 1)
    self.linesTable.setCellWidget(r, 0, radio)

    m = re.search(r'^([\+\-]?\d*(?:\.\d+)?)', data.name)
    if m: self.setIADx(r, m.group(1))

    self.selectBaseGroup.addButton(radio, len(self.selectBaseGroup.buttons()))
    radio.setChecked(True)

    self.lines.append(data)

  def setLinesTableCell(self, r, c, v):
    self.linesTable.setItem(r, c, QTableWidgetItem(str(v)))

  def getLinesTableCol(self, c):
    return [self.linesTable.item(r, c).text() for r in range(self.linesTable.rowCount())]

  def setIADx(self, i, v):
    self.setLinesTableCell(i, 1, v)
    self.updateIADx()

  def setWC(self, i, v):
    self.setLinesTableCell(i, 2, v)

  def setXoff(self, i, v):
    self.setLinesTableCell(i, 3, v)

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

  def plotOriginal(self):
    self.plot('orig')

  def plotXoffset(self):
    self.plot('xoff')

  def plotDifferences(self):
    self.plot('diff')

  def plotIAD(self):
    self.plot('iad')

  def plot(self, mode):
    log('IAD: Plot %s' % mode)
    self.tool.mode = mode
    self.updateIADx()
    self.plotRequested.emit(self.tool)
