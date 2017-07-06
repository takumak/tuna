import logging
import re
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import \
  QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, \
  QLineEdit, QFrame, QCheckBox, QSpinBox, QPushButton, \
  QButtonGroup, QRadioButton, QComboBox, QTableWidgetItem, \
  QAbstractScrollArea, QHeaderView, QApplication

from tools import CubicSpline, ToolBase, FitTool, IADTool
from commonwidgets import TableWidget


class ToolWidgetBase(QWidget):
  plotRequested = pyqtSignal(ToolBase, bool, name='plotRequested')

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
  columnLabels = ['Name', 'IAD X', 'IAD Y', 'X offset', 'Weight center', 'Peak x', 'Peak y']

  def __init__(self):
    super().__init__()

    vbox = QVBoxLayout()
    self.setLayout(vbox)

    self.linesTable = TableWidget()
    self.linesTable.cellChanged.connect(self.linesTableCellChanged)
    vbox.addWidget(self.linesTable)

    self.linesTableCopyButton = QPushButton('Copy')
    self.linesTableCopyButton.clicked.connect(lambda c: self.copyLinesTable())
    hbox = QHBoxLayout()
    hbox.addWidget(self.linesTableCopyButton)
    hbox.addStretch(1)
    vbox.addLayout(hbox)

    vbox.addStretch(1)
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    vbox.addWidget(line)


    self.optionsGrid = QGridLayout()
    vbox.addLayout(self.optionsGrid)

    self.interpComboBox = QComboBox()
    self.interpComboBox.currentIndexChanged.connect(self.interpSelected)
    self.interpOptionsLayout = QVBoxLayout()
    self.interpOptionsLayout.setContentsMargins(40, 0, 0, 0)
    self.interpCheckBox = QCheckBox('Interpolation')
    self.interpCheckBox.setChecked(False)
    self.interpStateChanged(Qt.Unchecked)
    self.interpCheckBox.stateChanged.connect(self.interpStateChanged)
    self.optionsGrid.addWidget(self.interpCheckBox, 0, 0)
    self.optionsGrid.addWidget(self.interpComboBox, 0, 1)
    self.optionsGrid.addLayout(self.interpOptionsLayout, 1, 0, 1, 2)

    self.interpOptions = []
    for interp in [CubicSpline()]:
      opt = interp.createOptionsWidget()
      self.interpComboBox.addItem(interp.name, [interp, opt])
      if opt:
        self.interpOptionsLayout.addWidget(opt)
        self.interpOptions.append(opt)
    self.interpComboBox.setCurrentIndex(0)

    self.WCthreshold = QLineEdit()
    self.WCthreshold.setValidator(QDoubleValidator())
    self.WCthreshold.textChanged.connect(lambda t: self.toolSetWCthreshold)
    self.WCthreshold.setText('%g' % self.tool.threshold)
    self.optionsGrid.addWidget(QLabel('Weight center threshold'), 2, 0)
    self.optionsGrid.addWidget(self.WCthreshold, 2, 1)

    for l, f in [('Plot original', self.plotOriginal),
                 ('Plot with X offset', self.plotXoffset),
                 ('Plot differences', self.plotDifferences),
                 ('Plot IAD', self.plotIAD)]:
      btn = QPushButton(l)
      btn.clicked.connect(f)
      vbox.addWidget(btn)

    self.tool.xoffUpdated.connect(self.updateXoff)
    self.tool.iadYUpdated.connect(self.updateIADy)
    self.tool.peaksUpdated.connect(self.updatePeaks)

  def copyLinesTable(self):
    rows = [self.columnLabels]
    for r in range(self.linesTable.rowCount()):
      row = [self.linesTable.cellWidget(r, 0).text()]
      for c in range(1, self.linesTable.columnCount()):
        row.append(self.linesTable.item(r, c).text())
      rows.append(row)
    QApplication.clipboard().setText('\n'.join(['\t'.join(r) for r in rows]))

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
    self.replot()

  def interpStateChanged(self, state):
    self.tool.interpEnabled = state == Qt.Checked
    self.replot()

  def clear(self):
    self.linesTable.clear()
    self.linesTable.verticalHeader().hide()
    self.linesTable.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
    self.linesTable.setColumnCount(len(self.columnLabels))
    self.linesTable.setHorizontalHeaderLabels(self.columnLabels)
    self.linesTable.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

    self.selectBaseGroup = QButtonGroup()
    self.selectBaseGroup.buttonClicked.connect(lambda b: self.toolSetBase())
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
    self.toolSetBase()

    self.lines.append(data)

  def setLinesTableCell(self, r, c, v):
    self.linesTable.setItem(r, c, QTableWidgetItem(str(v)))

  def getLinesTableCol(self, c):
    return [self.linesTable.item(r, c).text() for r in range(self.linesTable.rowCount())]

  def setIADx(self, i, v):
    self.setLinesTableCell(i, 1, v)
    self.toolSetIADx()

  def setIADy(self, i, v):
    self.setLinesTableCell(i, 2, v)

  def setXoff(self, i, v):
    self.setLinesTableCell(i, 3, v)

  def setWC(self, i, v):
    self.setLinesTableCell(i, 4, v)

  def setPeak(self, i, x, y):
    self.setLinesTableCell(i, 5, x)
    self.setLinesTableCell(i, 6, y)

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

  def updatePeaks(self):
    for i, peak in enumerate(self.tool.peaks):
      self.setPeak(i, *peak)

  def plotOriginal(self):
    self.plot('orig')

  def plotXoffset(self):
    self.plot('xoff')

  def plotDifferences(self):
    self.plot('diff')

  def plotIAD(self):
    self.plot('iad')

  def replot(self):
    self.plot(self.tool.mode)

  def plot(self, mode):
    if not self.tool.lines:
      return

    autoRange = (mode != self.tool.mode
                 and not set([mode, self.tool.mode]) <= set(['orig', 'xoff']))

    logging.info('IAD: Plot %s (auto range: %s)' % (mode, autoRange))

    self.tool.mode = mode
    self.toolSetBase()
    self.toolSetIADx()
    self.toolSetWCthreshold()
    self.plotRequested.emit(self.tool, autoRange)
