import logging
import re
import numpy as np
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import \
  QWidget, QLabel, QGridLayout, QLineEdit, QPushButton, \
  QButtonGroup, QRadioButton, QComboBox, QTableWidgetItem, \
  QAbstractScrollArea, QHeaderView, QApplication

from tools import ToolBase, FitTool, IADTool
from interpolation import InterpLinear, InterpCubicSpline, \
  InterpBarycentric, InterpKrogh, InterpPchip, InterpAkima
from bgsubtraction import BGSubNop, BGSubMinimum, BGSubLeftEdge, BGSubRightEdge
from commonwidgets import TableWidget, HSeparator, VBoxLayout, HBoxLayout
from widgets import FileDialog


class ToolWidgetBase(QWidget):
  plotRequested = pyqtSignal(ToolBase, bool, name='plotRequested')

  def __init__(self):
    super().__init__()
    self.tool = self.toolClass()
    self.tool.cleared.connect(self.clear)
    self.tool.added.connect(self.add)

  def name(self):
    return self.toolClass.name

  def label(self):
    return self.toolClass.label

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
    self.selectBaseGroup = None

    vbox = VBoxLayout()
    vbox.setContentsMargins(4, 4, 4, 4)
    self.setLayout(vbox)

    self.linesTable = TableWidget()
    self.linesTable.cellChanged.connect(self.linesTableCellChanged)
    vbox.addWidget(self.linesTable)

    self.copyResultButton = QPushButton('Copy')
    self.copyResultButton.clicked.connect(lambda c: self.copyResult())
    hbox = HBoxLayout()
    hbox.addWidget(self.copyResultButton)
    hbox.addStretch(1)
    vbox.addLayout(hbox)


    vbox.addStretch(1)
    vbox.addWidget(HSeparator())


    self.bgsubComboBox = QComboBox()
    self.bgsubComboBox.currentIndexChanged.connect(self.bgsubSelected)
    hbox = HBoxLayout()
    hbox.addWidget(QLabel('BG subtraction'))
    hbox.addWidget(self.bgsubComboBox)
    vbox.addLayout(hbox)

    bgsubOptionsLayout = VBoxLayout()
    bgsubOptionsLayout.setContentsMargins(40, 0, 0, 0)
    vbox.addLayout(bgsubOptionsLayout)

    self.bgsubOptions = []
    for bgsub in [BGSubNop(), BGSubMinimum(), BGSubLeftEdge(), BGSubRightEdge()]:
      opt = bgsub.getOptionsWidget()
      self.bgsubComboBox.addItem(bgsub.label, [bgsub, opt])
      if opt:
        bgsubOptionsLayout.addWidget(opt)
        self.bgsubOptions.append(opt)
    self.bgsubComboBox.setCurrentIndex(0)
    self.bgsubSelected(self.bgsubComboBox.currentIndex())


    self.interpComboBox = QComboBox()
    self.interpComboBox.currentIndexChanged.connect(self.interpSelected)
    self.interpdxLineEdit = QLineEdit()
    self.interpdxLineEdit.setValidator(QDoubleValidator())
    self.interpdxLineEdit.setText('%g' % self.tool.interpdx)
    self.interpdxLineEdit.textChanged.connect(lambda t: self.updateToolProps())
    hbox = HBoxLayout()
    hbox.addWidget(QLabel('Interpolation'))
    hbox.addWidget(self.interpComboBox)
    hbox.addWidget(QLabel('dx'))
    hbox.addWidget(self.interpdxLineEdit)
    vbox.addLayout(hbox)

    interpOptionsLayout = VBoxLayout()
    interpOptionsLayout.setContentsMargins(40, 0, 0, 0)
    vbox.addLayout(interpOptionsLayout)

    self.interpOptions = []
    for interp in [InterpCubicSpline(), InterpLinear(), InterpPchip(),
                   InterpAkima(), InterpKrogh(), InterpBarycentric()]:
      opt = interp.getOptionsWidget()
      self.interpComboBox.addItem(interp.label, [interp, opt])
      if opt:
        interpOptionsLayout.addWidget(opt)
        self.interpOptions.append(opt)
    self.interpComboBox.setCurrentIndex(0)
    self.interpSelected(self.interpComboBox.currentIndex())

    self.WCthreshold = QLineEdit()
    self.WCthreshold.setValidator(QDoubleValidator())
    self.WCthreshold.setText('%g' % self.tool.threshold)
    self.WCthreshold.textChanged.connect(lambda t: self.updateToolProps())
    hbox = HBoxLayout()
    hbox.addWidget(QLabel('Weight center threshold'))
    hbox.addWidget(self.WCthreshold)
    vbox.addLayout(hbox)


    vbox.addWidget(HSeparator())


    buttons = [('Plot original',      self.plotOriginal),
               ('Plot with X offset', self.plotXoffset),
               ('Plot differences',   self.plotDifferences),
               ('Plot IAD',           self.plotIAD),
               ('Export xls',         self.exportXls)]
    grid = QGridLayout()
    vbox.addLayout(grid)
    for i, (l, f) in enumerate(buttons):
      c = i%2
      r = i//2

      btn = QPushButton(l)
      btn.clicked.connect(f)
      grid.addWidget(btn, r, c)

    self.updateToolProps()

    self.tool.xoffUpdated.connect(self.updateXoff)
    self.tool.iadYUpdated.connect(self.updateIADy)
    self.tool.peaksUpdated.connect(self.updatePeaks)

  def copyResult(self):
    rows = [self.columnLabels]
    for r in range(self.linesTable.rowCount()):
      row = [self.linesTable.cellWidget(r, 0).text()]
      for c in range(1, self.linesTable.columnCount()):
        row.append(self.linesTable.item(r, c).text().strip())
      rows.append(row)
    QApplication.clipboard().setText('\n'.join(['\t'.join(r) for r in rows]))

  def exportXls(self):
    from functions import getTableColumnLabel
    def cellName(r, c, absx='', absy=''):
      return '%s%s%s%d' % (absx, getTableColumnLabel(c), absy, r+1)

    dlg = FileDialog('iad_export_xls')
    if dlg.exec_() != dlg.Accepted:
      return
    filename = dlg.selectedFiles()[0]


    lines = self.tool.getLines('xoff')
    base = lines.index(lines[self.tool.base])

    import xlwt
    wb = xlwt.Workbook()
    ws = wb.add_sheet('IAD')

    c0, r0 = 0, 0
    c1, r1 = c0+1, r0+1
    for c, l in enumerate(lines):
      if c == 0:
        ws.write(r0, c0, 'x')
        for r, x in enumerate(l.x):
          ws.write(r1+r, c0, x)

      ws.write(r0, c1+c, l.name)
      for r, y in enumerate(l.y):
        ws.write(r1+r, c1+c, y)

    c2 = c1 + len(lines) + 1

    for c, l in enumerate(lines):
      ws.write(r0, c2+c, l.name)
      for r, y in enumerate(l.y):
        f = 'abs(%s-%s)' % (cellName(r1+r, c1+c), cellName(r1+r, c1+base, '$'))
        ws.write(r1+r, c2+c, xlwt.Formula(f))

    c3 = c2 + len(lines) + 1
    c4 = c3 + 1
    ws.write(r0, c4+0, 'IAD')
    ws.write(r0, c4+1, 'Weight center')
    ws.write(r0, c4+2, 'Intensity sum')
    for i, l in enumerate(lines):
      n = l.name
      m = re.search(r'^([\+\-]?\d*(?:\.\d+)?)', l.name)
      if m: n = m.group(1)

      r2 = r1+len(l.y)-1
      f1 = 'sum(%s:%s)' % (cellName(r1, c2+i), cellName(r2, c2+i))
      ry = '%s:%s'      % (cellName(r1, c1+i), cellName(r2, c1+i))
      f2 = 'sumproduct(%s:%s,%s)/sum(%s)' % (
        cellName(r1, c0), cellName(r2, c0), ry, ry)
      f3 = 'sum(%s:%s)' % (cellName(r1, c1+i), cellName(r2, c1+i))

      ws.write(r1+i, c3, n)
      ws.write(r1+i, c3+1, xlwt.Formula(f1))
      ws.write(r1+i, c3+2, xlwt.Formula(f2))
      ws.write(r1+i, c3+3, xlwt.Formula(f3))

    wb.save(filename)

  def linesTableCellChanged(self, r, c):
    if c == 1:
      self.updateToolProps()

  def updateToolProps(self):
    self.tool.bgsub = self.bgsubComboBox.currentData()[0]

    self.tool.interp = self.interpComboBox.currentData()[0]
    self.tool.interpdx = float(self.interpdxLineEdit.text())
    self.tool.threshold = float(self.WCthreshold.text())

    self.tool.iadX = []
    for x in self.getIADx():
      try:
        x = float(x)
      except:
        x = None
      self.tool.iadX.append(x)

  def baseRadioClicked(self, b):
    self.tool.base = self.selectBaseGroup.checkedId()
    self.replot()

  def bgsubSelected(self, idx):
    bgsub, opt_ = self.bgsubComboBox.currentData()
    for opt in self.bgsubOptions:
      if opt == opt_:
        opt.show()
      else:
        opt.hide()
    self.replot()

  def interpSelected(self, idx):
    interp, opt_ = self.interpComboBox.currentData()
    for opt in self.interpOptions:
      if opt == opt_:
        opt.show()
      else:
        opt.hide()
    self.replot()

  def clear(self):
    self.linesTable.clear()
    self.linesTable.verticalHeader().hide()
    self.linesTable.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
    self.linesTable.setColumnCount(len(self.columnLabels))
    self.linesTable.setHorizontalHeaderLabels(self.columnLabels)
    self.linesTable.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

    self.selectBaseGroup = QButtonGroup()
    self.selectBaseGroup.buttonClicked.connect(self.baseRadioClicked)
    self.lines = []

  def add(self, data):
    r = len(self.lines)
    radio = QRadioButton(data.name)
    self.linesTable.setRowCount(r + 1)
    self.linesTable.setCellWidget(r, 0, radio)

    m = re.search(r'^([\+\-]?\d*(?:\.\d+)?)', data.name)
    if m: self.setIADx(r, m.group(1))

    idx = len(self.selectBaseGroup.buttons())
    if self.tool.base < 0 or self.tool.base == idx:
      radio.setChecked(True)
    self.selectBaseGroup.addButton(radio, idx)

    self.lines.append(data)

  def setLinesTableCell(self, r, c, v):
    self.linesTable.setItem(r, c, QTableWidgetItem(str(v)))

  def getLinesTableCol(self, c):
    return [self.linesTable.item(r, c).text() for r in range(self.linesTable.rowCount())]

  def setIADx(self, i, v):
    self.setLinesTableCell(i, 1, v)
    self.updateToolProps()

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
        self.setWC(i, '%.10f' % wc)
      else:
        b = self.tool.wc[self.tool.base]
        self.setWC(i, '%.10f' % b)
      self.setXoff(i, '%+.10f' % xoff)

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

    autoRange = mode != self.tool.mode

    logging.info('IAD: Plot %s (auto range: %s)' % (mode, autoRange))

    self.tool.mode = mode
    self.updateToolProps()
    self.plotRequested.emit(self.tool, autoRange)

  def getBGSubList(self):
    return [self.bgsubComboBox.itemData(i)[0] for i in range(self.bgsubComboBox.count())]

  def getInterpList(self):
    return [self.interpComboBox.itemData(i)[0] for i in range(self.interpComboBox.count())]

  def saveState(self):
    curr_bgsub, opt_ = self.bgsubComboBox.currentData()
    curr_interp, opt_ = self.interpComboBox.currentData()
    return {
      'curr_bgsub': curr_bgsub.name,
      'bgsub': dict([(item.name, item.saveState()) for item in self.getBGSubList()]),
      'curr_interp': curr_interp.name,
      'interp': dict([(item.name, item.saveState()) for item in self.getInterpList()]),
      'interpdx': self.interpdxLineEdit.text(),
      'wc_threshold': self.WCthreshold.text(),
      'plot_mode': self.tool.mode,
      'base': self.tool.base
    }

  def restoreState(self, state):
    bgsub = dict([(item.name, (i, item)) for i, item in enumerate(self.getBGSubList())])
    if 'curr_bgsub' in state:
      self.bgsubComboBox.setCurrentIndex(bgsub[state['curr_bgsub']][0])
    if 'bgsub' in state:
      for name, s in state['bgsub'].items():
        if name in bgsub:
          bgsub[name][1].restoreState(s)

    interp = dict([(item.name, (i, item)) for i, item in enumerate(self.getInterpList())])
    if 'curr_interp' in state:
      self.interpComboBox.setCurrentIndex(interp[state['curr_interp']][0])
    if 'interp' in state:
      for name, istate in state['interp'].items():
        if name in interp:
          interp[name][1].restoreState(istate)
    if 'interpdx' in state: self.interpdxLineEdit.setText(state['interpdx'])

    if 'wc_threshold' in state: self.WCthreshold.setText(state['wc_threshold'])
    if 'plot_mode' in state: self.tool.mode = state['plot_mode']
    if 'base' in state: self.tool.base = state['base']

    self.updateToolProps()
