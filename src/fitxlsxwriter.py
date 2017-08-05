from xlsxwriter.utility import xl_rowcol_to_cell as cellName, xl_range_abs as rangeNameAbs



class FitXlsxWriter:
  recalcMsg = 'Press F9 (for Excel) or Ctrl+Shift+F9 (for LibreOffice) to re-calculate cell formulae'

  def __init__(self, tool):
    self.tool = tool

  def write(self, wb):
    self.prepare()
    self.writeParameters(wb, wb.add_worksheet('Parameters'), 0, 0)
    for line in self.lines:
      ws = wb.add_worksheet(line.name)
      ws.write(0, 0, self.recalcMsg)
      self.writeFitSheet(wb, ws, 0, 1, line)

  def prepare(self):
    lines = []
    params = self.tool.peakFuncParams
    funcs = self.tool.peakFunctions
    pressures = {}

    for line in self.tool.lines:
      if line.name not in params: continue
      p = self.tool.getPressure(line.name).value()
      if p is None: continue
      pressures[line.name] = p
      for func in funcs:
        if func.id not in params[line.name]: break
      else:
        lines.append(line)

    self.lines = lines
    self.params = params
    self.funcs = funcs
    self.pressures = pressures

  def writeParameters(self, wb, ws, c0, r0):
    for i, line in enumerate(self.lines):
      ws.write(r0+2+i, c0, self.pressures[line.name])

    self.paramCells = {}

    cc = c0+1
    for i, func in enumerate(self.funcs):
      fparams = [p for p in func.params if not p.hidden]
      ws.merge_range(r0, cc, r0, cc+len(fparams)-1, 'F%d' % i)
      for j, param in enumerate(fparams):
        ws.write(r0+1, cc+j, param.name)
        for k, line in enumerate(self.lines):
          v = self.params[line.name][func.id][param.name]
          ws.write(r0+2+k, cc+j, v)
          cellname = "'%s'!%s" % (ws.name, cellName(r0+2+k, cc+j, True, True))
          self.paramCells[(line.name, func.id, param.name)] = cellname
      cc += len(fparams)

  def writeFitSheet(self, wb, ws, c0, r0, line):
    from sympy.parsing.sympy_parser import parse_expr
    from sympy import Symbol

    r1 = r0+1

    ws.write(r0, c0+0, 'x')
    ws.write(r0, c0+1, 'y')
    cols = [line.x, line.y]

    for c, func in enumerate(self.funcs):
      ws.write(r0, c0+2+c, 'F%d' % c)
      expr = func.excelExpr()

      subs = []
      for p in func.params:
        if p.hidden: continue
        cell = self.paramCells[(line.name, func.id, p.name)]
        subs.append((p.name, cell))
      subs = dict(subs)

      y = []
      for r in range(len(line.x)):
        subs['x'] = cellName(r1+r, c0)
        y.append('=%s' % (expr % subs))
      cols.append(y)

    for r, vals in enumerate(zip(*cols)):
      for c, v in enumerate(vals):
        ws.write(cellName(r1+r, c0+c), v)


    ws.write(r0, c0+len(cols), 'fit')
    ws.write(r0, c0+len(cols)+1, 'diff')
    for r in range(len(line.x)):
      n1 = cellName(r1+r, c0+2)
      n2 = cellName(r1+r, c0+len(cols)-1)
      ws.write(r1+r, c0+len(cols), '=sum(%s:%s)' % (n1, n2))

      y = cellName(r1+r, c0+1)
      fit = cellName(r1+r, c0+len(cols))
      ws.write(r1+r, c0+len(cols)+1, '=%s-%s' % (y, fit))



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

    r2 = r1+len(line.x)-1
    for c in range(len(self.funcs)+3):
      chart.add_series({
        'name':       "='%s'!%s" % (ws.name, cellName(r0, c0+1+c, True, True)),
        'categories': "='%s'!%s" % (ws.name, rangeNameAbs(r1, c0, r2, c0)),
        'values':     "='%s'!%s" % (ws.name, rangeNameAbs(r1, c0+1+c, r2, c0+1+c)),
        'line':       {'width': 1}
      })

    ws.insert_chart(cellName(r0, c0+len(self.funcs)+5), chart)
