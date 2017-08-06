import logging
import re
import numpy as np
import pyqtgraph as pg

import log
from line import Line
from toolbase import ToolBase
from fitfunctions import *
from settingitems import *
from functions import blockable



class FitTool(ToolBase):
  name = 'fit'
  label = 'Fit'

  funcClasses = [
    FitFuncGaussian, FitFuncPseudoVoigt,
    FitFuncBoltzmann2,
    FitFuncConstant, FitFuncHeaviside,
    FitFuncRectangularWindow
  ]

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


  def __init__(self):
    super().__init__()
    self.bgsub = None
    self.normWindow = []
    self.peakFunctions = []
    self.sumCurveItem = None
    self.diffCurveItem = None
    self.lineCurveItems = []
    self.activeLineName = None
    self.peakFuncParams = {}
    self.pressures = {}
    self.view = None
    self.mode = 'peaks'
    self.plotParams = None

    self.optimizeMethod = self.optimizeMethods[0]
    self.addSettingItem(SettingItemFloat(
      'optimize_tol', 'Tolerance', '',
      min_=0, emptyIsNone=True))
    self.diffSquareSum = SettingItemFloat(
      'diffsqsum', 'Result', '0')

  def setBGSub(self, bgsub):
    if self.bgsub:
      self.bgsub.disconnectAllValueChanged(self.bgsubParameterChanged)
    self.bgsub = bgsub
    self.bgsubParameterChanged()
    self.bgsub.connectAllValueChanged(self.bgsubParameterChanged)

  def bgsubParameterChanged(self):
    self.normalizeLines()
    self.updateDiffCurve()

  def clear(self):
    super().clear()
    self.sumCurveItem = None
    self.diffCurveItem = None
    self.lineCurveItems = []

  def add(self, *args):
    line = super().add(*args)
    item = pg.PlotCurveItem(x=line.x, y=line.y, name=line.name)
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

  def optimize(self, params):
    line = self.activeLine()
    if not line:
      logging.warning('Line not selected')
      return

    logging.debug('Optimize: %s using %s' % (
      ','.join(['%s' % p.name for p in params]), self.optimizeMethod))

    def wrap(func, args_i):
      return lambda a: func(line.x, *[a[i] for i in args_i])

    srcfuncs = []
    funcs = []
    for func in self.peakFunctions:
      args, args_i = [], []
      p = list(zip(*[(p, i) for i, p in enumerate(params) if p in func.params]))
      if len(p) > 0:
        args, args_i = p
        srcfuncs.append(func)
      funcs.append(wrap(func.lambdify(args), args_i))

    from scipy.optimize import minimize
    func = lambda a: np.sum((np.sum([f(a) for f in funcs], axis=0) - line.y)**2)
    a0 = np.array([p.value() for p in params])

    res = minimize(
      func, a0,
      method=self.optimizeMethod,
      tol=self.optimize_tol.value()
    )
    logging.debug('Optimize done: %s' % ','.join(map(str, res.x)))

    self.parameterChanged_peaks.block()
    for p, v in zip(params, res.x):
      p.setValue(v)
    self.parameterChanged_peaks.unblock()
    for f in srcfuncs:
      self.parameterChanged_peaks(f)

  def setView(self, view):
    self.view = view

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
      params[func.id] = func.getParams()

  def restorePeakFuncParams(self):
    if self.activeLineName and self.activeLineName in self.peakFuncParams:
      logging.debug('Restore func params')
      params = self.peakFuncParams[self.activeLineName]
      active = self.activeLineName
      self.activeLineName = None # prevent saving old func params
      for func in self.peakFunctions:
        if func.id in params:
          func.setParams(params[func.id])
        else:
          params[func.id] = func.getParams()
      self.activeLineName = active

  def createFunction(self, funcName):
    for cls in self.funcClasses:
      if cls.name == funcName:
        return cls(self.view)
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
    for i, (line, curve) in enumerate(zip(self.lines, self.lineCurveItems)):
      x, y = line.x, line.y
      if self.bgsub:
        f = self.bgsub.func(line, None, x)
        y = y - f(line.x)
      y = self.normalizeXY(x, y)
      if i == 0: S = sum(y)
      line.y = y/S
      line.y_ = None
      curve.setData(x=line.x, y=line.y)

  def updateSumCurve(self):
    if self.sumCurveItem is None:
      return

    x, y = self.sumCurveItem.getData()
    y = np.sum([f.y(x) for f in self.functions()], axis=0)
    self.sumCurveItem.setData(x=x, y=y)

  def updateDiffCurve(self):
    active = self.activeLine()
    if self.diffCurveItem is None or active is None:
      return

    x = active.x
    y = np.sum([f.y(x) for f in self.functions()], axis=0) - active.y
    self.diffSquareSum.setStrValue('%.3e' % np.sum(y**2))
    self.diffCurveItem.setData(x=x, y=y)

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

        lines.append(Line(param.name, x, y, None))
      return lines

    return []

  def getGraphItems(self, colorpicker):
    if self.plotParams:
      return super().getGraphItems(colorpicker)

    self.normalizeLines()
    if self.mode == 'normwin':
      for item in self.lineCurveItems:
        item.setPen(color=colorpicker.next(), width=2)
      return self.lineCurveItems + self.getGraphItems_functions(colorpicker, self.normWindow)
    elif self.mode == 'peaks':
      return self.getGraphItems_peaks(colorpicker)
    else:
      raise RuntimeError('[Bug] Invalid plot mode - "%s"' % self.mode)

  def getGraphItems_peaks(self, colorpicker):
    line = self.activeLine()

    if not line:
      for item in self.lineCurveItems:
        item.setPen(color=colorpicker.next(), width=2)
      return self.lineCurveItems

    active = self.lineCurveItems[self.lines.index(line)]
    active.setPen(color=colorpicker.next(), width=2)

    items = [active]
    items += self.getGraphItems_functions(colorpicker, self.peakFunctions)

    if self.diffCurveItem is None:
      logging.debug('Generate diff curve')
      x = line.x
      self.diffCurveItem = pg.PlotCurveItem(
        x=x, y=np.zeros(len(x)), name='Diff')
    self.updateDiffCurve()
    self.diffCurveItem.setPen(color=colorpicker.next(), width=2)
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
        self.sumCurveItem = pg.PlotCurveItem(
          x=x, y=np.zeros(len(x)), name='Sum')
      self.updateSumCurve()
      self.sumCurveItem.setPen(color=colorpicker.next(), width=2)
      items.append(self.sumCurveItem)

    return items

  def setActiveLineName(self, name):
    self.activeLineName = name
    self.restorePeakFuncParams()

  def saveState(self):
    state = super().saveState()
    state['norm_window'] = [(f.name, f.getParams()) for f in self.normWindow]
    state['peak_functions'] = [(f.name, f.id) for f in self.peakFunctions]
    state['peak_func_params'] = self.peakFuncParams
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

    if 'peak_func_params' in state:
      self.peakFuncParams = state['peak_func_params']

    if 'active_line' in state:
      self.activeLineName = state['active_line']

    if 'peak_functions' in state:
      functions = []
      for name, id in state['peak_functions']:
        try:
          f = self.createFunction(name)
          f.id = id
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
