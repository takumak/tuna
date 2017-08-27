import logging
import numpy as np
from xlsxexporter import XlsxExporter



class FitXlsxExporter(XlsxExporter):
  formatForPlotModes = {'absolute': None, 'diff': '+0.00;-0.00', 'ratio': '+0.00%;-0.00%'}

  def __init__(self, tool):
    super().__init__()
    self.tool = tool

  def write(self, book):
    super().write(book)
    self.prepare()
    self.writeParameters()
    self.writeNormalizeSheet()
    for line in self.lines:
      self.writeFitSheet(line)

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




  def writeParameters(self):
    self.addSheet('Parameters')

    params = self.Parameters[:2+len(self.lines),:]
    params[1,0].write(self.xLabel('param'))
    params[2:,0].write([self.pressures[l.name] for l in self.lines])
    params[1,1].write('R^2')
    self.Parameters.R2 = dict([(l.name, params[2+i,1]) for i, l in enumerate(self.lines)])

    self.paramCells = {}
    param = params[:,2:]
    for i, func in enumerate(self.funcs):
      fparams = [p for p in func.params if not p.hidden]
      param.setWidth(len(fparams))
      param[0,:].merge('P%d' % i)

      for j, p in enumerate(fparams):
        param[1,j].write(p.label)

        for k, line in enumerate(self.lines):
          try:
            v = self.params[line.name][func.id][p.name]
          except KeyError:
            logging.debug('KeyError: line=%s, func=%s, param=%s'
                          % (line.name, func.label, p.name))
            raise

          pv = param[2+k,j]
          pv.write(v)
          self.paramCells[(line.name, func.id, p.name)] = pv

      param = param.right()


    from collections import OrderedDict
    plot_data = OrderedDict()

    for i, func in enumerate(self.funcs):
      plotParams = [p for p in func.params if p.plotMode]
      if len(plotParams) == 0: continue

      for p in plotParams:

        def pcell(l):
          return self.paramCells[(l.name, func.id, p.name)].cellName()

        c0 = pcell(self.lines[0])
        if p.plotMode == 'absolute':
          formula = '=%s'
        elif p.plotMode == 'diff':
          formula = '=%s-{}'.format(c0)
        elif p.plotMode == 'ratio':
          formula = '=(%s-{0})/{0}'.format(c0)
        else:
          raise RuntimeError('Unknown plot mode - "%s"' % p.plotMode)

        key = p.plotLabel, p.plotMode
        if key in plot_data:
          data = plot_data[key]
        else:
          data = []
          plot_data[key] = data

        vals = [formula % pcell(l) for l in self.lines]
        data.append(('P%d' % i, vals))


    changes = params.below()[2:4+len(self.lines),:]
    changes[1,0].write(self.xLabel('param'))
    changes_x = changes[1:,0]
    changes_x[1:,:].write([self.pressures[l.name] for l in self.lines])

    charts = changes.below()[2:,:]
    param = changes[:,1:]
    for i, ((ylabel, plotMode), cols) in enumerate(plot_data.items()):
      param.setWidth(len(cols))
      param[0,:].merge(ylabel)
      fmt = self.formatForPlotModes[plotMode]

      for c, (fname, vals) in enumerate(cols):
        param[1,c].write(fname)
        param[2:,c].write(vals, self.getFormat(fmt))

      chart = charts.addChart('param',
                              ylabel=ylabel, yformat=fmt,
                              width=400, height=400,
                              legend=True, markers=True)
      chart.add(changes_x, param[1:,:])
      chart.complete(xoff=410*(i%2), yoff=410*(i//2))

      param = param.right()




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


    chart = self.Normalize[3,0].addChart('source')
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


    chart = R2.below()[1,0].addChart('source', legend=True)
    chart.add(x, y)
    chart.add(x, funcs)
    chart.add(x, fit)
    chart.add(x, diff)
    chart.complete()
