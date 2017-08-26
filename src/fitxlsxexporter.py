import logging
import numpy as np
from xlsxexporter import XlsxExporter



class FitXlsxExporter(XlsxExporter):
  formatForPlotModes = {'diff': '+0.00;-0.00', 'ratio': '+0.00%;-0.00%'}

  def __init__(self, tool):
    self.tool = tool

  def write(self, book):
    super().write(book)
    self.prepare()

    self.writeParameters()
    self.writeNormalizeSheet()

    for line in self.lines:
      self.writeFitSheet(line)
    #   f = "='%s'!%s" % (ws.name, R2)
    #   ws_params.write(cells_R2[line.name], f)
    # ws_params.write(cells_R2[0], 'R^2')

  def prepare(self):
    lines = []
    params = self.tool.peakFuncParams
    funcs = self.tool.peakFunctions
    pressures = {}

    for line in self.tool.lines:
      if line.name not in params: continue
      p = self.tool.getPressure(line.name).value()
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




  def writeParameters(self):
    self.addSheet('Parameters')

    self.Parameters[2:,0].write(
      [self.pressures[l.name] for l in self.lines])

    self.Parameters[1,1].write('R^2')
    R2 = self.Parameters[2:,1]
    self.Parameters.R2 = dict([(l.name, R2[i,0]) for i, l in enumerate(self.lines)])

    params = self.Parameters[:2+len(self.lines),2:]
    changes = params.below()[2:,:]

    self.paramCells = {}

    for i, func in enumerate(self.funcs):
      fparams = [p for p in func.params if not p.hidden]
      params[0,:len(fparams)].merge('P%d' % i)

      for j, param in enumerate(fparams):
        params[1,j].write(param.label)

        for k, line in enumerate(self.lines):
          try:
            v = self.params[line.name][func.id][param.name]
          except KeyError:
            logging.debug('KeyError: line=%s, func=%s, param=%s'
                          % (line.name, func.label, param.name))
            raise

          p = params[2+k,j]
          p.write(v)
          self.paramCells[(line.name, func.id, param.name)] = p

      params = params[:,len(fparams):]



  #   r1 = 2+len(self.lines)+2
  #   r2 = r1+2
  #   r3 = r2+len(self.lines)-1
  #   cc = c0+2

  #   for i, line in enumerate(self.lines):
  #     ws.write(r2+i, c0, self.pressures[line.name])

  #   plotdata = {}
  #   ylabels = []
  #   for i, func in enumerate(self.funcs):
  #     plotParams = [p for p in func.params if p.plotMode]
  #     N = len(plotParams)
  #     if N == 0:
  #       continue
  #     elif N == 1:
  #       ws.write(r1, cc, 'P%d' % i)
  #     else:
  #       ws.merge_range(r1, cc, r1, cc+N-1, 'P%d' % i)

  #     for c, param in enumerate(plotParams):
  #       ws.write(r1+1, cc+c, param.label)

  #       for r, line in enumerate(self.lines):
  #         cell0 = self.paramCells[(self.lines[0].name, func.id, param.name)]
  #         celli = self.paramCells[(line.name, func.id, param.name)]
  #         if param.plotMode == 'diff':
  #           f = '=%s-%s' % (celli, cell0)
  #         elif param.plotMode == 'ratio':
  #           f = '=({1}-{0})/{0}'.format(cell0, celli)
  #         else:
  #           raise RuntimeError('Unknown plot mode - "%s"' % param.plotMode)
  #         fmt = self.getFormat(wb, self.formatForPlotModes[param.plotMode])
  #         ws.write_formula(cellName(r2+r, cc+c), f, fmt)

  #       if param.label not in plotdata:
  #         plotdata[param.label] = []
  #         ylabels.append((param.label, self.formatForPlotModes[param.plotMode]))

  #       plotdata[param.label].append((cellName(r1, cc), rangeNameAbs(r2, cc+c, r3, cc+c)))

  #     cc += len(plotParams)


  #   r4 = r3+2
  #   for i, (ylabel, yfmt) in enumerate(ylabels):
  #     chart = wb.add_chart({'type': 'scatter', 'subtype': 'straight_with_markers'})
  #     chart.set_title({'none': True})
  #     chart.set_x_axis({
  #       'name': 'Pressure (GPa)',
  #       'major_gridlines': {'visible': False},
  #       'major_tick_mark': 'inside'
  #     })
  #     chart.set_y_axis({
  #       'name': ylabel,
  #       'major_gridlines': {'visible': False},
  #       'major_tick_mark': 'inside',
  #       'num_format': yfmt
  #     })

  #     for name, data in plotdata[ylabel]:
  #       chart.add_series({
  #         'name':       "='%s'!%s" % (ws.name, name),
  #         'categories': "='%s'!%s" % (ws.name, rangeNameAbs(r2, c0, r3, c0)),
  #         'values':     "='%s'!%s" % (ws.name, data),
  #         'line':       {'width': 1}
  #       })

  #     ws.insert_chart(cellName(r4, c0+(i*8)), chart)

  #   cells_R2 = dict([(l.name, cellName(r0+2+i, c0+1))
  #                    for i, l in enumerate(self.lines)])
  #   cells_R2[0] = cellName(r0+1, c0+1)
  #   return cells_R2




  def writeNormalizeSheet(self):
    self.addSheet('Normalize')

    maxy = max(self.lines[0].y)/sum(self.lines[0].y)

    x = self.lines[0].x
    if len(self.tool.normWindow) == 0:
      win = np.ones(len(x))
    else:
      win = np.sum([f.y(x) for f in self.tool.normWindow], axis=0)
    win = win/max(win)*maxy*0.8
    cols = [('x', x), ('window', win)] + [(l.name, l.y) for l in self.lines]

    for c, (name, vals) in enumerate(cols):
      self.Normalize[0,c].write(name)
      self.Normalize[1:,c].write(vals)


    x = self.Normalize[:len(self.lines[0].x)+1,0]
    win = x.right()[:,0]
    raw = win.right()[:,:len(self.lines)]
    norm1 = raw.right()[:,1:len(self.lines)+1]
    norm2 = norm1.right()[:,1:len(self.lines)+1]

    self.Normalize.lines = {}

    for c, l in enumerate(self.lines):
      norm1[0,c].write(l.name)
      norm2[0,c].write(l.name)

      w = win[1:,:].rangeName()
      r = raw[1:,c].rangeName()
      norm1[1:,c].write(raw[1:,c].format('=%(n)s/sumproduct(%(r)s,%(w)s)', r=r, w=w))
      norm2[1:,c].write(norm1[1:,c].format('=%(n)s/sum(%(n0)s)', n0=norm1[1:,0].rangeName()))

      self.Normalize.lines[l.name] = norm2[:,c]


    chart = self.Normalize.addChart('source')
    chart.add(x, win)
    chart.add(x, norm2)
    chart.complete()


    self.Normalize.x = x
    self.Normalize.data = norm2




  def writeFitSheet(self, line):
    sheet = self.addSheet(line.name)

    x     = sheet[:self.Normalize.x.height(),0]
    y     = x.right()[:,0]
    ydiff = y.right()[:,0]
    funcs = ydiff.right()[:,:len(self.funcs)]
    fit   = funcs.right()[:,0]
    diff  = fit.right()[:,0]

    x[0,0].write('x')
    y[0,0].write('y')
    ydiff[0,0].write('y-avg(y)')
    fit[0,0].write('fit')
    diff[0,0].write('diff')

    x[1:,:].write(self.Normalize.x[1:,:].format('=%(N)s'))
    y[1:,:].write(self.Normalize.lines[line.name][1:,:].format('=%(N)s'))
    ydiff[1:,:].write(y[1:,:].format('=%(n)s-average(%(a)s)', a=y[1:,:].rangeName()))
    fit[1:,:].write(['=sum(%s)' % r.rangeName() for r in funcs[1:,:].rowRanges()])
    diff[1:,:].write(['=%s-%s' % (y, f) for y, f in zip(y[1:,:].cellNames(), fit[1:,:].cellNames())])

    for c, func in enumerate(self.funcs):
      funcs[0,c].write('P%d' % c)
      expr = func.excelExpr()

      subs = []
      for p in func.params:
        if p.hidden: continue
        cell = self.paramCells[(line.name, func.id, p.name)]
        subs.append((p.name, cell.cellName(True)))
      subs = dict(subs)

      funcs[1:,c].write(x[1:,:].format('='+expr, fmtname='x', **subs))


    R2 = diff.right()[:2,1]
    R2[0,0].write('R^2')
    R2[1,0].write('=1-sumsq(%s)/sumsq(%s)' % (diff[1:,:].rangeName(), ydiff[1:,:].rangeName()))
    self.Parameters.R2[line.name].write('=%s' % R2[1,0].cellName(True))


    chart = R2.below().addChart('source')
    chart.add(x, y)
    chart.add(x, funcs)
    chart.add(x, fit)
    chart.add(x, diff)
    chart.complete()
