import logging
import numpy as np
from xlsxwriter.utility import \
  xl_rowcol_to_cell as cellName, \
  xl_range as rangeName, \
  xl_range_abs as rangeNameAbs



class FitXlsxWriter:
  recalcMsg = 'Press F9 (for Excel) or Ctrl+Shift+F9 (for LibreOffice) to re-calculate cell formulae'
  formatForPlotModes = {'diff': '+0.00;-0.00', 'ratio': '+0.00%;-0.00%'}

  def __init__(self, tool):
    self.tool = tool

  def write(self, wb):
    self.prepare()

    ws_params = self.addSheet(wb, 'Parameters')
    cells_R2 = self.writeParameters(wb, ws_params, 0, 1)
    cells = self.writeNormalizeSheet(wb, self.addSheet(wb, 'Normalize'), 0, 1)

    for line in self.lines:
      ws = self.addSheet(wb, line.name)
      R2 = self.writeFitSheet(wb, ws, 0, 1, line.name, cells[line.name])
      f = "='%s'!%s" % (ws.name, R2)
      ws_params.write(cells_R2[line.name], f)
    ws_params.write(cells_R2[0], 'R^2')

  def addSheet(self, wb, name):
    ws = wb.add_worksheet(name)
    ws.write(0, 0, self.recalcMsg)
    return ws

  def prepare(self):
    lines = []
    params = self.tool.peakFuncParams
    funcs = self.tool.peakFunctions
    pressures = {}

    for line in self.tool.lines:
      if line.name not in params: continue
      p = self.tool.getPressure(line.name).value()
      # if p is None: continue
      pressures[line.name] = p
      for func in funcs:
        if func.id not in params[line.name]: break
      else:
        lines.append(line)

    self.lines = list(self.tool.lines)
    self.params = params
    self.funcs = funcs
    self.pressures = pressures
    self.formats = {}

  def getFormat(self, wb, fmt):
    if fmt not in self.formats:
      self.formats[fmt] = wb.add_format({'num_format': fmt})
    return self.formats[fmt]

  def writeParameters(self, wb, ws, c0, r0):
    for i, line in enumerate(self.lines):
      ws.write(r0+2+i, c0, self.pressures[line.name])

    self.paramCells = {}

    cc = c0+2
    for i, func in enumerate(self.funcs):
      fparams = [p for p in func.params if not p.hidden]
      ws.merge_range(r0, cc, r0, cc+len(fparams)-1, 'P%d' % i)
      for j, param in enumerate(fparams):
        ws.write(r0+1, cc+j, param.label)
        for k, line in enumerate(self.lines):
          try:
            v = self.params[line.name][func.id][param.name]
          except KeyError:
            logging.debug('KeyError: line=%s, func=%s, param=%s'
                          % (line.name, func.label, param.name))
            raise
          ws.write(r0+2+k, cc+j, v)
          cellname = "'%s'!%s" % (ws.name, cellName(r0+2+k, cc+j, True, True))
          self.paramCells[(line.name, func.id, param.name)] = cellname
      cc += len(fparams)



    r1 = 2+len(self.lines)+2
    r2 = r1+2
    r3 = r2+len(self.lines)-1
    cc = c0+2

    for i, line in enumerate(self.lines):
      ws.write(r2+i, c0, self.pressures[line.name])

    plotdata = {}
    ylabels = []
    for i, func in enumerate(self.funcs):
      plotParams = [p for p in func.params if p.plotMode]
      N = len(plotParams)
      if N == 0:
        continue
      elif N == 1:
        ws.write(r1, cc, 'P%d' % i)
      else:
        ws.merge_range(r1, cc, r1, cc+N-1, 'P%d' % i)

      for c, param in enumerate(plotParams):
        ws.write(r1+1, cc+c, param.label)

        for r, line in enumerate(self.lines):
          cell0 = self.paramCells[(self.lines[0].name, func.id, param.name)]
          celli = self.paramCells[(line.name, func.id, param.name)]
          if param.plotMode == 'diff':
            f = '=%s-%s' % (celli, cell0)
          elif param.plotMode == 'ratio':
            f = '=({1}-{0})/{0}'.format(cell0, celli)
          else:
            raise RuntimeError('Unknown plot mode - "%s"' % param.plotMode)
          fmt = self.getFormat(wb, self.formatForPlotModes[param.plotMode])
          ws.write_formula(cellName(r2+r, cc+c), f, fmt)

        if param.label not in plotdata:
          plotdata[param.label] = []
          ylabels.append((param.label, self.formatForPlotModes[param.plotMode]))

        plotdata[param.label].append((cellName(r1, cc), rangeNameAbs(r2, cc+c, r3, cc+c)))

      cc += len(plotParams)


    r4 = r3+2
    for i, (ylabel, yfmt) in enumerate(ylabels):
      chart = wb.add_chart({'type': 'scatter', 'subtype': 'straight_with_markers'})
      chart.set_title({'none': True})
      chart.set_x_axis({
        'name': 'Pressure (GPa)',
        'major_gridlines': {'visible': False},
        'major_tick_mark': 'inside'
      })
      chart.set_y_axis({
        'name': ylabel,
        'major_gridlines': {'visible': False},
        'major_tick_mark': 'inside',
        'num_format': yfmt
      })

      for name, data in plotdata[ylabel]:
        chart.add_series({
          'name':       "='%s'!%s" % (ws.name, name),
          'categories': "='%s'!%s" % (ws.name, rangeNameAbs(r2, c0, r3, c0)),
          'values':     "='%s'!%s" % (ws.name, data),
          'line':       {'width': 1}
        })

      ws.insert_chart(cellName(r4, c0+(i*8)), chart)

    cells_R2 = dict([(l.name, cellName(r0+2+i, c0+1))
                     for i, l in enumerate(self.lines)])
    cells_R2[0] = cellName(r0+1, c0+1)
    return cells_R2

  def writeNormalizeSheet(self, wb, ws, c0, r0):
    maxy = max(self.lines[0].y)/sum(self.lines[0].y)

    x = self.lines[0].x
    if len(self.tool.normWindow) == 0:
      win = np.ones(len(x))
    else:
      win = np.sum([f.y(x) for f in self.tool.normWindow], axis=0)
    win = win/max(win)*maxy*0.8
    cols = [('x', x), ('window', win)] + [(l.name, l.y) for l in self.lines]

    for c, (name, vals) in enumerate(cols):
      ws.write(r0, c0+c, name)
      for r, val in enumerate(vals):
        ws.write(r0+1+r, c0+c, val)

    r1 = r0+1
    r2 = r1+len(x)-1
    c1 = c0 + len(cols) + 1
    c2 = c1 + len(self.lines) + 1

    chart = wb.add_chart({'type': 'scatter', 'subtype': 'straight'})
    chart.set_title({'none': True})
    chart.set_x_axis({
      'name': 'Energy (eV)',
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside'
    })
    chart.set_y_axis({
      'name': 'Intensity (a.u.)',
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside'
    })

    range_x = rangeNameAbs(r1, c0+0, r2, c0+0)
    range_w = rangeNameAbs(r1, c0+1, r2, c0+1)
    range_l0w = rangeNameAbs(r1, c1, r2, c1)
    for c, l in enumerate(self.lines):
      ws.write(r0, c1+c, l.name)
      ws.write(r0, c2+c, l.name)

      range_l = rangeName(r1, c0+2+c, r2, c0+2+c)
      range_r = rangeName(r1, c2+c, r2, c2+c)

      for r in range(len(x)):
        cell_l = cellName(r1+r, c0+2+c)
        cell_w = cellName(r1+r, c1+c)
        formula = '=%s/sumproduct(%s,%s)' % (cell_l, range_l, range_w)
        ws.write(cell_w, formula)

        formula = '=%s/sum(%s)' % (cell_w, range_l0w)
        ws.write(cellName(r1+r, c2+c), formula)

      chart.add_series({
        'name':       "='%s'!%s" % (ws.name, cellName(r0, c2+c)),
        'categories': "='%s'!%s" % (ws.name, range_x),
        'values':     "='%s'!%s" % (ws.name, range_r),
        'line':       {'width': 1}
      })

    # window
    chart.add_series({
      'name':       "='%s'!%s" % (ws.name, cellName(r0, c0+1)),
      'categories': "='%s'!%s" % (ws.name, range_x),
      'values':     "='%s'!%s" % (ws.name, range_w),
      'line':       {'width': 1}
    })

    ws.insert_chart(cellName(r0+10, c0), chart)
    return dict([(l.name, (ws.name, (r1, r2), c0, c2+c)) for c, l in enumerate(self.lines)])

  def writeFitSheet(self, wb, ws, c0, r0, lname, cells):
    from sympy.parsing.sympy_parser import parse_expr
    from sympy import Symbol

    data_sheetname, (data_r1, data_r2), data_c_x, data_c_y = cells
    datalen = data_r2 - data_r1 + 1

    r1 = r0+1
    r2 = r1+datalen-1

    ws.write(r0, c0+0, 'x')
    ws.write(r0, c0+1, 'y')
    ws.write(r0, c0+2, 'y-avg(y)')
    for r in range(datalen):
      fx = "='%s'!%s" % (data_sheetname, cellName(data_r1+r, data_c_x))
      fy = "='%s'!%s" % (data_sheetname, cellName(data_r1+r, data_c_y))
      fd = '=%s - AVERAGE(%s)' % (cellName(r1+r, c0+1), rangeName(r1, c0+1, r2, c0+1))
      ws.write(cellName(r1+r, c0+0), fx)
      ws.write(cellName(r1+r, c0+1), fy)
      ws.write(cellName(r1+r, c0+2), fd)

    c1 = c0+3

    for c, func in enumerate(self.funcs):
      ws.write(r0, c1+c, 'P%d' % c)
      expr = func.excelExpr()

      subs = []
      for p in func.params:
        if p.hidden: continue
        cell = self.paramCells[(lname, func.id, p.name)]
        subs.append((p.name, cell))
      subs = dict(subs)

      for r in range(datalen):
        subs['x'] = cellName(r1+r, c0)
        f = '=%s' % (expr % subs)
        ws.write(cellName(r1+r, c1+c), f)

    c2 = c1+len(self.funcs)

    ws.write(r0, c2+0, 'fit')
    ws.write(r0, c2+1, 'diff')
    for r in range(datalen):
      n1 = cellName(r1+r, c0+3)
      n2 = cellName(r1+r, c2-1)
      ws.write(r1+r, c2, '=sum(%s:%s)' % (n1, n2))

      y = cellName(r1+r, c0+1)
      fit = cellName(r1+r, c2)
      ws.write(r1+r, c2+1, '=%s-%s' % (y, fit))


    c3 = c2+len(self.funcs)
    f = '=1 - sumsq(%s)/sumsq(%s)' % (
      rangeName(r1, c2+1, r2, c2+1),
      rangeName(r1, c0+1, r2, c0+1))
    ws.write(cellName(r0, c3), 'R^2')
    ws.write(cellName(r1, c3), f)


    chart = wb.add_chart({'type': 'scatter', 'subtype': 'straight'})
    chart.set_title({'none': True})
    chart.set_x_axis({
      'name': 'Energy (eV)',
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside',
      'min': min([min(l.x) for l in self.lines]),
      'max': max([max(l.x) for l in self.lines])
    })
    chart.set_y_axis({
      'name': 'Intensity (a.u.)',
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside'
    })

    for c in range(len(self.funcs)+4):
      if c == 1: continue
      chart.add_series({
        'name':       "='%s'!%s" % (ws.name, cellName(r0, c0+1+c, True, True)),
        'categories': "='%s'!%s" % (ws.name, rangeNameAbs(r1, c0, r2, c0)),
        'values':     "='%s'!%s" % (ws.name, rangeNameAbs(r1, c0+1+c, r2, c0+1+c)),
        'line':       {'width': 1}
      })

    ws.insert_chart(cellName(r0, c3+2), chart)

    return cellName(r1, c3)
