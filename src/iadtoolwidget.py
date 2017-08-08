import re
import logging
from PyQt5.QtWidgets import QPushButton, QComboBox, QLabel, \
  QGridLayout, QHeaderView, QButtonGroup, QRadioButton, \
  QTableWidgetItem

from iadtool import IADTool
from toolwidgetbase import *
from commonwidgets import *



class IADToolWidget(ToolWidgetBase):
  toolClass = IADTool
  columnLabels = ['Name', 'IAD X', 'IAD Y', 'X offset', 'Weight center', 'Peak x', 'Peak y']

  def __init__(self, graphWidget):
    super().__init__(graphWidget)
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


    for name in 'Smooth', 'BGSub', 'Interp':
      cls = globals()['MethodSelector%s' % name]
      sel = cls(self.tool.interpdx) if name == 'Interp' else cls()
      setattr(self, name.lower(), sel)
      sel.selectionChanged.connect(self.replot)
      self.addMethodSelector(sel)
      vbox.addWidget(sel)


    hbox = HBoxLayout()
    hbox.addWidget(QLabel('Weight center threshold'))
    hbox.addWidget(self.tool.threshold.getWidget())
    vbox.addLayout(hbox)


    vbox.addWidget(HSeparator())


    buttons = [('Plot original',      lambda: self.plot('orig')),
               ('Plot normalized',    lambda: self.plot('norm')),
               ('Plot with X offset', lambda: self.plot('xoff')),
               ('Plot differences',   lambda: self.plot('diff')),
               ('Plot IAD',           lambda: self.plot('iad')),
               ('Export xlsx',        self.exportXlsx)]
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

  def writeXlsx(self, wb):
    ws_IAD = wb.add_worksheet('IAD')
    ws_err = wb.add_worksheet('IAD err')

    ws_IAD.write(0, 0, self.xlsxRecalcMsg)

    errCells = self.writeXlsx_err(wb, ws_err, 0, 0)
    errCells = ["='%s'!%s" % (ws_err.name, c) for c in errCells]
    chart_spectra, chart_diff, chart_iad \
      = self.writeXlsx_IAD(wb, ws_IAD, 0, 1, errCells)

    wb.add_chartsheet('Spectra').set_chart(chart_spectra)
    wb.add_chartsheet('Diff').set_chart(chart_diff)
    wb.add_chartsheet('IAD graph').set_chart(chart_iad)

  def writeXlsx_IAD(self, wb, ws, c0, r0, errCells):
    fmt_wc = wb.add_format()
    fmt_wc.set_num_format('0.000000000000')
    fmt_is = wb.add_format()
    fmt_is.set_num_format('0.00')

    from functions import getTableCellName as cellName
    lines = self.tool.getLines('xoff')
    base = lines.index(lines[self.tool.base])

    c1, r1 = c0+1, r0+1
    c2 = c1 + len(lines) + 1

    for c, l in enumerate(lines):
      if c == 0:
        ws.write(r0, c0, 'x')
        for r, x in enumerate(l.x):
          ws.write(r1+r, c0, x)

      ws.write(r0, c1+c, l.name)
      ws.write(r0, c2+c, l.name)
      for r, y in enumerate(l.y):
        # spectrum
        ws.write(r1+r, c1+c, y)
        # diff
        f = '=%s-%s' % (cellName(r1+r, c1+c), cellName(r1+r, c1+base, '$'))
        ws.write(r1+r, c2+c, f)


    chart_spectra = wb.add_chart({'type': 'scatter', 'subtype': 'straight'})
    chart_spectra.set_title({'none': True})
    chart_spectra.set_x_axis({
      'name': 'Energy (eV)',
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside'
    })
    chart_spectra.set_y_axis({
      'name': 'Intensity (a.u.)',
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside'
    })

    chart_diff = wb.add_chart({'type': 'scatter', 'subtype': 'straight'})
    chart_diff.set_title({'none': True})
    chart_diff.set_x_axis({
      'name': 'Energy (eV)',
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside'
    })
    chart_diff.set_y_axis({
      'name': 'Intensity difference (a.u.)',
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside'
    })

    chart_iad = wb.add_chart({'type': 'scatter', 'subtype': 'straight_with_markers'})
    chart_iad.set_title({'none': True})
    chart_iad.set_legend({'none': True})
    chart_iad.set_x_axis({
      'name': 'Pressure (GPa)',
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside'
    })
    chart_iad.set_y_axis({
      'name': 'IAD (a.u.)',
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside',
      'min': 0
    })

    c3 = c2 + len(lines) + 1
    c4 = c3 + 1
    ws.write(r0, c4+0, 'IAD')
    ws.write(r0, c4+1, 'IAD err')
    ws.write(r0, c4+2, 'Weight center')
    ws.write(r0, c4+3, 'Intensity sum')
    lines_iad = [(l, iadX) for l, iadX in zip(lines, self.tool.iadX) if iadX is not None]
    for i, (l, iadX) in enumerate(lines_iad):
      r2 = r1+len(l.y)-1
      f1 = '=sumproduct(abs(%s:%s))' % (cellName(r1, c2+i), cellName(r2, c2+i))
      ry = '%s:%s'      % (cellName(r1, c1+i), cellName(r2, c1+i))
      f2 = '=sumproduct(%s:%s,%s)/sum(%s)' % (
        cellName(r1, c0), cellName(r2, c0), ry, ry)
      f3 = '=sum(%s:%s)' % (cellName(r1, c1+i), cellName(r2, c1+i))

      ws.write(r1+i, c3, iadX)
      ws.write(r1+i, c3+1, f1)
      ws.write(r1+i, c3+2, errCells[i])
      ws.write(r1+i, c3+3, f2, fmt_wc)
      ws.write(r1+i, c3+4, f3, fmt_is)

      chart_spectra.add_series({
        'name':       [ws.name, r0, c1+i],
        'categories': [ws.name, r1, c0, r2, c0],
        'values':     [ws.name, r1, c1+i, r2, c1+i],
        'line':       {'width': 1}
      })

      chart_diff.add_series({
        'name':       [ws.name, r0, c2+i],
        'categories': [ws.name, r1, c0, r2, c0],
        'values':     [ws.name, r1, c2+i, r2, c2+i],
        'line':       {'width': 1}
      })

    err_values = "='%s'!%s:%s" % (ws.name, cellName(r1, c3+2), cellName(r1+len(lines_iad)-1, c3+2))
    chart_iad.add_series({
      'name':       [ws.name, r0, c3+1],
      'categories': [ws.name, r1, c3,   r1+len(lines_iad)-1, c3],
      'values':     [ws.name, r1, c3+1, r1+len(lines_iad)-1, c3+1],
      'y_error_bars': {
        'type':         'custom',
        'plus_values':  err_values,
        'minus_values': err_values
      },
    })

    return chart_spectra, chart_diff, chart_iad

  def writeXlsx_err(self, wb, ws, c0, r0):
    from functions import getTableCellName as cellName
    lines = self.tool.getLines('orig')
    base = lines.index(lines[self.tool.base])

    c1, r1 = c0+1, r0+1
    c2 = c1 + (len(lines)*2) + 1
    c3 = c2 + 4
    c4 = c3 + len(lines) + 1
    ws.write(r0, c2+1, 'sum(I)')
    ws.write(r0, c2+2, 'sum(I) err')
    ws.write(r0, c4+1, 'IAD err')
    for c, l in enumerate(lines):
      if c == 0:
        ws.write(r0, c0, 'x')
        for r, x in enumerate(l.x):
          ws.write(r1+r, c0, x)

      C = c1+(c*2)
      r2 = r1+len(l.y)-1

      ws.write(r0, C, l.name)
      ws.write(r0, C+1, '%s err' % l.name)
      ws.write(r0, c3+c, '%s norm err' % l.name)
      for r, (y, y_) in enumerate(zip(l.y, l.y_)):
        ws.write(r1+r, C, y)
        ws.write(r1+r, C+1, y_)
        ws.write(r1+r, c3+c,
                 '=sqrt((1/%(sumy)s)^2*(%(y_)s^2) + (%(y)s/%(sumy)s^2)^2*(%(sumy_)s^2))' % {
                   'y':     cellName(r1+r, C),
                   'y_':    cellName(r1+r, C+1),
                   'sumy':  cellName(r1+c, c2+1),
                   'sumy_': cellName(r1+c, c2+2)
                 })


      ws.write(r1+c, c2, l.name)
      ws.write(r1+c, c2+1, '=sum(%s:%s)' % (cellName(r1, C), cellName(r2, C)))
      ws.write(r1+c, c2+2, '=sqrt(sumsq(%s:%s))' % (cellName(r1, C+1), cellName(r2, C+1)))

      ws.write(r1+c, c4, l.name)
      ws.write(r1+c, c4+1, '=sqrt(sumsq(%s:%s)+sumsq(%s:%s))' % (
        cellName(r1, c3+c), cellName(r2, c3+c),
        cellName(r1, c3+base), cellName(r2, c3+base)
      ))

    return [cellName(r1+i, c4+1) for i, l in enumerate(lines)]

  def linesTableCellChanged(self, r, c):
    if c == 1:
      self.updateToolProps()

  def updateToolProps(self):
    self.tool.bgsub  = self.bgsub.currentItem()
    self.tool.smooth = self.smooth.currentItem()
    self.tool.interp = self.interp.currentItem()

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

  def clear(self):
    self.linesTable.clear()
    self.linesTable.verticalHeader().hide()
    self.linesTable.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
    self.linesTable.setColumnCount(len(self.columnLabels))
    self.linesTable.setHorizontalHeaderLabels(self.columnLabels)
    self.linesTable.setSizeAdjustPolicy(self.linesTable.AdjustToContents)

    self.selectBaseGroup = QButtonGroup()
    self.selectBaseGroup.buttonClicked.connect(self.baseRadioClicked)
    self.lines = []

  def add(self, line):
    r = len(self.lines)
    radio = QRadioButton(line.name)
    self.linesTable.setRowCount(r + 1)
    self.linesTable.setCellWidget(r, 0, radio)

    m = re.search(r'^([\+\-]?\d*(?:\.\d+)?)', line.name)
    if m: self.setIADx(r, m.group(1))

    idx = len(self.selectBaseGroup.buttons())
    if self.tool.base < 0 or self.tool.base == idx:
      radio.setChecked(True)
    self.selectBaseGroup.addButton(radio, idx)

    self.lines.append(line)

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

  def restoreState(self, state):
    super().restoreState(state)
    self.updateToolProps()
