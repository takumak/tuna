import sys
import logging
import re
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QValidator

import log
from line import Line
from toolbase import ToolBase
import fitfunctions
from fitgraphitems import *
from settingitems import *
from functions import blockable



class InvalidConstraints(Exception):
  def __init__(self, msg):
    super().__init__()
    self.reason = msg



class OptimizeThread(QThread):
  def __init__(self, tool, params):
    super().__init__()
    self.tool = tool
    self.params = params
    self.prepare()
    self.exc_info = None

  @classmethod
  def parseConstraints(cls, constraints, variables, tool):
    from sympy import Symbol, sympify
    exprs = constraints.strip()
    if not exprs: return []

    constraints = []
    for line in [l.strip() for l in re.split(r'[;,\n]', exprs)]:
      if not line or line[0] == '#': continue
      pair = line.split('=')
      if len(pair) != 2:
        raise InvalidConstraints('"%s" is not valid equation (statement must contain "=")' % line)
      lhs, rhs = map(sympify, pair)
      if not isinstance(lhs, Symbol):
        raise InvalidConstraints('lhs must be a symbol: "%s"' % pair[0])

      params = []
      subs = []
      for sym in [lhs] + list(rhs.free_symbols):
        m = re.match(r'F(\d+)_(.*)', sym.name)
        if not m:
          raise InvalidConstraints('Unknown symbol: %s; '
                                   'Function parameters are in format of "F1_name"'
                                   % sym.name)
        i, pn = int(m.group(1)), m.group(2)
        if i > len(tool.peakFunctions):
          raise InvalidConstraints('Function id out of range: %s' % sym.name)
        f = tool.peakFunctions[i - 1]
        if pn not in f.paramsNameMap:
          raise InvalidConstraints('"%s" does not have such a parameter: %s' % (f.label, sym.name))
        p = f.paramsNameMap[pn]

        if sym == lhs:
          lhs = p
        elif p in variables:
          params.append((sym.name, variables.index(p)))
        else:
          subs.append((sym, p.value()))

      constraints.append((lhs, rhs.subs(subs), params))

    return constraints

  def wrapFuncWithConstraints(self, func, params, constraints):
    cparams = [lhs for lhs, rhs, subs in constraints if lhs in func.params]
    uparams = [p for p in params if p in func.params and p not in cparams]

    func_ = func.lambdify(uparams + cparams)

    pindices = [params.index(p) for p in uparams]
    cindices = [i for i, (l, r, s) in enumerate(constraints) if l in cparams]
    def wrap(x, values, cvalues):
      args = [values[i] for i in pindices]
      args += [cvalues[i] for i in cindices]
      return func_(x, *args)

    return wrap

  def calcConstraintValues(self, pvalues):
    pairs = []
    for lhs, rhs, subs in self.constraints:
      v = rhs.subs([(n, pvalues[i]) for n, i in subs])
      pairs.append((lhs, float(v)))
    return pairs

  def prepare(self):
    line = self.tool.activeLine()
    params = self.params

    self.constraints = self.parseConstraints(self.tool.constraints.strValue(), params, self.tool)
    constraints = self.constraints
    for lhs, rhs, subs in constraints:
      if lhs in params:
        params.remove(lhs)

    logging.debug('Optimize: %s using %s' % (
      ','.join(['%s' % p.name for p in params]), self.tool.optimizeMethod))

    self.srcfuncs = []
    funcs = []
    for func in self.tool.peakFunctions:
      for p in params + [lhs for lhs, rhs, subs in constraints]:
        if p in func.params:
          self.srcfuncs.append(func)
          break
      funcs.append(self.wrapFuncWithConstraints(func, params, constraints))

    x, y = np.array([(x, y) for x, y in zip(line.x, line.y2)
                     if self.tool.fitRange.inRange(x)]).T
    def R2(a):
      cvals = [v for p, v in self.calcConstraintValues(a)]
      return np.sum((np.sum([f(x, a, cvals) for f in funcs], axis=0) - y)**2)
    a0 = np.array([p.value() for p in params])

    self.R2 = R2
    self.a0 = a0
    self.optimizeMethod = self.tool.optimizeMethod

  def run(self):
    try:
      from scipy.optimize import minimize
      self.res = minimize(self.R2, self.a0, method=self.optimizeMethod)
    except:
      self.exc_info = sys.exc_info()



class FitTool(ToolBase):
  name = 'fit'
  label = 'Fit'

  funcClasses = [getattr(fitfunctions, name) for name in fitfunctions.__all__]

  optimizeMethods = [
    'Nelder-Mead',
    'Powell',
    'CG',
    'BFGS',
    'L-BFGS-B',
    'TNC',
    'COBYLA',
    'SLSQP',
    # requires Jacobian
    # 'Newton-CG',
    # 'dogleg',
    # 'trust-ncg'
  ]

  intersectionsUpdated = pyqtSignal()
  peakPositionsUpdated = pyqtSignal()


  def __init__(self, graphWidget):
    super().__init__(graphWidget)
    self.bgsub = None
    self.smooth = None
    self.normWindow = []
    self.peakFunctions = []
    self.sumCurveItem = None
    self.diffCurveItem = None
    self.lineCurveItems = []
    self.activeLineName = None
    self.peakFuncParams = {}
    self.pressures = {}
    self.mode = 'peaks'
    self.plotParams = None
    self.optimizer = None

    self.optimizeMethod = self.optimizeMethods[0]
    self.R2 = SettingItemFloat('R2', 'R^2', '0')
    self.IAD = SettingItemFloat('IAD', 'IAD', '0')
    self.addSettingItem(SettingItemRange('fitRange', 'Fit range', '-inf:inf'))
    self.addSettingItem(SettingItemStr('isecFunc', 'Function', '1'))
    self.addSettingItem(SettingItemStr('constraints', 'Constraints', '',
                                       validator=self.validateConstraints))
    self.isecPoints = []
    self.peakPos = []

  def setMethod(self, name, method):
    curr = getattr(self, name)
    if curr:
      curr.disconnectAllValueChanged(self.methodParameterChanged)
    setattr(self, name, method)
    self.methodParameterChanged()
    method.connectAllValueChanged(self.methodParameterChanged)

  def methodParameterChanged(self):
    self.normalizeLines()
    self.updateDiffCurve()

  def clear(self):
    super().clear()
    self.sumCurveItem = None
    self.diffCurveItem = None
    self.lineCurveItems = []

  def add(self, *args):
    line = super().add(*args)
    item = PlotCurveItem(line.x, line.y, self.graphWidget, '#000', line.name)
    self.lineCurveItems.append(item)
    return line

  def getPressure(self, name):
    if name in self.pressures:
      p = self.pressures[name]
    else:
      p = SettingItemFloat(
        'pressure', 'Pressure', '',
        min_=0, emptyIsNone=True)
      m = re.search(r'^([\+\-]?\d*(?:\.\d+)?)', name)
      if m:
        p.setStrValue(m.group(1))
      self.pressures[name] = p
    return p

  def validateConstraints(self, value):
    try:
      OptimizeThread.parseConstraints(value, [], self)
      return QValidator.Acceptable, 'OK'
    except InvalidConstraints as ex:
      return QValidator.Invalid, ex.reason
    except:
      log.warnException()
      return QValidator.Invalid, 'Unknown error'

  def optimize(self, params, callback=None):
    if self.optimizer:
      raise RuntimeError('Now an optimize job is running')

    line = self.activeLine()
    if not line:
      raise RuntimeError('Line not selected')

    self.optimizer = OptimizeThread(self, params)
    self.optimizer.callback = callback
    self.optimizer.finished.connect(self.optimizeComplete)
    self.optimizer.start()

  def optimizeComplete(self):
    optimizer = self.optimizer
    self.optimizer = None

    if optimizer.exc_info:
      log.logException(*optimizer.exc_info)
      return

    logging.debug('Optimize done: %s' % ','.join(map(str, optimizer.res.x)))

    self.parameterChanged_peaks.block()
    for p, v in zip(optimizer.params, optimizer.res.x):
      p.setValue(v)
    for p, v in optimizer.calcConstraintValues(optimizer.res.x):
      p.setValue(v)
    self.parameterChanged_peaks.unblock()

    for f in optimizer.srcfuncs:
      self.parameterChanged_peaks(f)

    self.calcIntersections()
    self.calcPeakPositions()

    if optimizer.callback:
      optimizer.callback(optimizer.exc_info is None, optimizer.params, optimizer.res.x)

  def functions(self):
    if self.mode == 'normwin':
      return self.normWindow
    if self.mode == 'peaks':
      return self.peakFunctions
    raise RuntimeError('[Bug] Invalid plot mode')

  def savePeakFuncParams(self, func):
    name = self.activeLineName
    if name:
      # logging.debug('Save func params: %s (%s)' % (name, func.name))
      if name not in self.peakFuncParams:
        self.peakFuncParams[name] = {}
      params = self.peakFuncParams[name]
      for func in self.peakFunctions:
        params[func.id] = func.getParams()
    else:
      for line in self.lines:
        if line.name not in self.peakFuncParams:
          self.peakFuncParams[line.name] = {}
        self.peakFuncParams[line.name][func.id] = func.getParams()

  def restorePeakFuncParams(self):
    if self.activeLineName:
      name = self.activeLineName
    elif len(self.lines) > 0:
      name = self.lines[0].name
    else:
      return

    if name in self.peakFuncParams:
      logging.debug('Restore func params')
      params = self.peakFuncParams[name]
      self.parameterChanged_peaks.block()
      for func in self.peakFunctions:
        if func.id in params:
          func.setParams(params[func.id])
        else:
          params[func.id] = func.getParams()
      self.parameterChanged_peaks.unblock()

      if self.activeLineName:
        self.savePeakFuncParams(None)

  def createFunction(self, funcName):
    for cls in self.funcClasses:
      if cls.name == funcName:
        return cls(self.graphWidget)
    raise RuntimeError('Function named "%s" is not defined' % funcName)

  def clearNormWindow(self):
    for func in self.normWindow:
      func.parameterChanged.disconnect(self.parameterChanged_normwin)
    self.normWindow = []

  def setNormWindow(self, functions):
    self.clearNormWindow()
    self.normWindow = functions
    for func in self.normWindow:
      func.parameterChanged.connect(self.parameterChanged_normwin)
    self.parameterChanged_normwin()
    if self.mode == 'normwin':
      self.normalizeLines()

  def parameterChanged_normwin(self):
    self.normalizeLines()

  def clearPeakFunctions(self):
    for func in self.peakFunctions:
      func.parameterChanged.disconnect(self.parameterChanged_peaks)
    self.peakFunctions = []

  def setPeakFunctions(self, functions):
    self.clearPeakFunctions()
    self.peakFunctions = functions
    self.restorePeakFuncParams()
    for func in self.peakFunctions:
      func.parameterChanged.connect(self.parameterChanged_peaks)
    self.updateSumCurve()
    self.updateDiffCurve()

  @blockable
  def parameterChanged_peaks(self, func):
    self.savePeakFuncParams(func)
    self.updateSumCurve()
    self.updateDiffCurve()

  def normalizeXY(self, x, y):
    if len(self.normWindow) == 0:
      yn = np.ones(len(x))
    else:
      yn = np.sum([f.y(x) for f in self.normWindow], axis=0)
      ynmax = max(yn)
      if ynmax > 0:
        yn = yn/max(yn)
    sumy = sum(y*yn)
    return y/(sum(y) if sumy == 0 else sumy)

  def normalizeLines(self):
    logging.debug('Smooth: %s' % self.smooth.name)
    for i, (line, curve) in enumerate(zip(self.lines, self.lineCurveItems)):
      x, y = line.x, line.y
      if self.bgsub:
        f = self.bgsub.func(line, None, x)
        y = y - f(line.x)
      y = self.normalizeXY(x, y)
      if i == 0: S = sum(y)
      y = y/S
      line.y = y
      line.y_ = None
      if self.smooth:
        y = self.smooth.smooth(x, y)
      line.y2 = y
      curve.setXY(line.x, y)

  def updateSumCurve(self):
    if self.sumCurveItem is None:
      return

    x = self.sumCurveItem.x
    y = np.sum([f.y(x) for f in self.functions()], axis=0)
    self.sumCurveItem.setXY(x, y)

  def updateDiffCurve(self):
    active = self.activeLine()
    if self.diffCurveItem is None or active is None:
      return

    x = active.x
    y = active.y
    diff = np.sum([f.y(x) for f in self.functions()], axis=0) - y
    R2 = 1 - np.sum(diff**2)/np.sum((y - sum(y)/len(y))**2)
    self.R2.setStrValue('%.4f' % R2)
    self.IAD.setStrValue(str(sum(diff)))
    self.diffCurveItem.setXY(x, diff)

  def activeLine(self):
    if self.activeLineName and self.activeLineName in self.lineNameMap:
      return self.lineNameMap[self.activeLineName]
    return None

  def getLines(self):
    if self.plotParams:
      lines = []
      for param in self.plotParams:
        func = param.func
        x, y = [], []

        for line in self.lines:
          x_ = self.getPressure(line.name).value()
          if x_ is None: continue

          if line.name not in self.peakFuncParams: continue
          params = self.peakFuncParams[line.name]
          if func.id not in params: continue
          y_ = params[func.id].get(param.name)
          if y_ is None: continue

          x.append(x_)
          y.append(y_)

        lines.append(Line(param.name, x, param.plotValues(y), None))
      return lines

    return []

  def getGraphItems(self, colorpicker):
    if self.plotParams:
      return super().getGraphItems(colorpicker)

    self.normalizeLines()
    if self.mode == 'normwin':
      for item in self.lineCurveItems:
        item.setPenColor(colorpicker.next())
      return self.lineCurveItems + self.getGraphItems_functions(colorpicker, self.normWindow)
    elif self.mode == 'peaks':
      return self.getGraphItems_peaks(colorpicker)
    else:
      raise RuntimeError('[Bug] Invalid plot mode - "%s"' % self.mode)

  def getGraphItems_peaks(self, colorpicker):
    active = self.activeLine()
    if active:
      items = [self.lineCurveItems[self.lines.index(active)]]
    else:
      self.restorePeakFuncParams()
      items = list(self.lineCurveItems)
    for item in items:
      item.setPenColor(colorpicker.next())

    items += self.getGraphItems_functions(colorpicker, self.peakFunctions)

    if active:
      if self.diffCurveItem is None:
        logging.debug('Generate diff curve')
        x = active.x
        self.diffCurveItem = PlotCurveItem(x, np.zeros(len(x)), self.graphWidget, '#000', 'Diff')

      self.updateDiffCurve()
      self.diffCurveItem.setPenColor(colorpicker.next())
      items.append(self.diffCurveItem)

    return items

  def getGraphItems_functions(self, colorpicker, functions):
    x1, x2 = self.getXrange()
    x = np.linspace(x1, x2, 500)

    items = []
    for f in functions:
      items += f.getGraphItems(x, colorpicker.next())

    if len(functions) >= 2:
      if self.sumCurveItem is None:
        logging.debug('Generate sum curve')
        self.sumCurveItem = PlotCurveItem(x, np.zeros(len(x)), self.graphWidget, '#000', 'Sum')
      self.updateSumCurve()
      self.sumCurveItem.setPenColor(colorpicker.next())
      items.append(self.sumCurveItem)

    return items

  def setActiveLineName(self, name):
    self.activeLineName = name
    self.restorePeakFuncParams()

  def calcIntersections(self):
    active = self.activeLine()
    # if line is None or self.isecFunc.strValue() == '':
    #   self.isecPoints = []
    #   self.intersectionsUpdated()
    #   return

    from sympy import Symbol
    from sympy.parsing.sympy_parser import parse_expr
    expr = parse_expr(self.isecFunc.strValue())
    if isinstance(expr, tuple): expr = expr[0]

    usex = False
    subs = []
    for sym in expr.free_symbols:
      if sym.name == 'x':
        usex = True
        continue

      m = re.match(r'F(\d+)_(.*)', sym.name)
      if m:
        pn = int(m.group(1))
        if pn <= 0 or pn > len(self.peakFunctions):
          logging.error('Function index out of range (%s)' % sym.name)
          return
        f = self.peakFunctions[pn - 1]
        name = m.group(2)
        if name not in f.paramsNameMap:
          logging.error('Invalid argument name "%s" (%s)' % (name, sym.name))
          return
        subs.append((sym, f.paramsNameMap[name].value()))
      else:
        logging.error('Invalid symbol: %s; Symbol name must be "x" or "F1_name"' % (sym.name))
        return

    expr = expr.subs(subs)
    if usex:
      func = lambdify([Symbol('x')], expr, 'numpy')
    else:
      cval = expr.evalf()
      func = lambda x: cval

    ptslist = []
    for line in self.lines:
      xx = zip(line.x[:-1], line.x[1:])
      yy = zip(line.y2[:-1], line.y2[1:])
      pts = []
      for (x1, x2), (y1, y2) in zip(xx, yy):
        Y1 = y1 - func(x1)
        Y2 = y2 - func(x2)
        if Y1*Y2 > 0: continue

        r = abs(Y1)/(abs(Y1)+abs(Y2))
        x0 = (x2 - x1)*r + x1
        y0 = (y2 - y1)*r + y1
        pts.append((x0, y0))
      ptslist.append((line, pts))

    self.isecPoints = ptslist
    self.intersectionsUpdated.emit()

  def calcPeakPositions(self):
    peakpos = []
    for line in self.lines:
      x = np.linspace(min(line.x), max(line.y), 500)
      y = np.sum([f.y(x, self.peakFuncParams.get(line.name)) for f in self.functions()], axis=0)
      mx, my = max(zip(x, y), key=lambda p: p[1])
      peakpos.append((line, (mx, my)))
    self.peakPos = peakpos
    self.peakPositionsUpdated.emit()

  def saveState(self):
    linenames = [l.name for l in self.lines]
    funcids = [f.id for f in self.peakFunctions]

    state = super().saveState()
    state['norm_window'] = [(f.name, f.getParams()) for f in self.normWindow]
    state['peak_functions'] = [(f.name, f.id) for f in self.peakFunctions]
    state['peak_func_params'] = dict([(k, dict([(fid, fp) for fid, fp in p.items() if fid in funcids]))
                                      for k, p in self.peakFuncParams.items() if k in linenames])
    state['plot_modes'] = dict([(f.id, dict([(p.name, (p.plotMode, p.plotLabel)) for p in f.params]))
                                for f in self.peakFunctions])
    state['pressures'] = dict([(n, p.strValue()) for n, p in self.pressures.items()])
    if self.activeLineName:
      state['active_line'] = self.activeLineName
    return state

  def restoreState(self, state):
    super().restoreState(state)

    if 'norm_window' in state:
      functions = []
      for name, params in state['norm_window']:
        try:
          f = self.createFunction(name)
          f.setParams(params)
          functions.append(f)
        except:
          log.warnException()
      self.setNormWindow(functions)

    self.peakFuncParams = state.get('peak_func_params', {})
    self.activeLineName = state.get('active_line')

    plotModes = state.get('plot_modes', {})
    functions = []
    if 'peak_functions' in state:
      for name, id in state['peak_functions']:
        try:
          f = self.createFunction(name)
          f.id = id
          if f.id in plotModes:
            modes = plotModes[f.id]
            for p in f.params:
              if p.name in modes:
                p.plotMode, p.plotLabel = modes[p.name]
          functions.append(f)
        except:
          log.warnException()
    self.setPeakFunctions(functions)

    if 'pressures' in state:
      for name, val in state['pressures'].items():
        self.getPressure(name).setStrValue(str(val))

  def newSession(self):
    super().newSession()
    self.clearNormWindow()
    self.clearPeakFunctions()
    self.peakFuncParams = {}
    self.pressures = {}
