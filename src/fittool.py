import logging
import numpy as np
import pyqtgraph as pg

import log
from line import Line
from toolbase import ToolBase
from fitfunctions import *



class FitTool(ToolBase):
  name = 'fit'
  label = 'Fit'
  funcClasses = [FitFuncGaussian, FitFuncTwoLines]

  def __init__(self):
    super().__init__()
    self.functions = []
    self.fitCurveItem = None
    self.diffCurveItem = None
    self.activeLineName = None
    self.funcParams = {}
    self.view = None

  def optimize(self, params):
    line = self.activeLine()
    if not line:
      logging.warning('Line not selected')
      return

    logging.debug('Optimize: %s' % ','.join(['%s=%g' % (p.name, p.value()) for p in params]))

    def wrap(func, args_i):
      return lambda a: func(line.x, *[a[i] for i in args_i])

    funcs = []
    for func in self.functions:
      args, args_i = [], []
      p = list(zip(*[(p, i) for i, p in enumerate(params) if p in func.params]))
      if len(p) > 0: args, args_i = p
      # if func.name == 'gaussian':
      #   logging.debug('a=%f; %s' % (func.a.value(), ','.join([a.name for a in args])))
      # else:
      #   logging.debug('name=%s; %s' % (func.name, ','.join([a.name for a in args])))
      funcs.append(wrap(func.lambdify(args), args_i))

    from scipy.optimize import minimize
    func = lambda a: np.sum((np.sum([f(a) for f in funcs], axis=0) - line.y)**2)
    a0 = np.array([p.value() for p in params])

    # x = line.x
    # y = np.sum([f(a0+3) for f in funcs], axis=0)
    # self.fitCurveItem.setData(x=x, y=y)

    res = minimize(func, a0)
    logging.info('Optimize done: %s' % ','.join(map(str, res.x)))

    for p, v in zip(params, res.x):
      p.setValue(v)

  def setView(self, view):
    self.view = view

  def saveFuncParams(self):
    if self.activeLineName:
      logging.debug('Save func params')
      if self.activeLineName not in self.funcParams:
        self.funcParams[self.activeLineName] = {}
      params = self.funcParams[self.activeLineName]
      for func in self.functions:
        params[func.id] = func.getParams()

  def restoreFuncParams(self):
    if self.activeLineName and self.activeLineName in self.funcParams:
      logging.debug('Restore func params')
      params = self.funcParams[self.activeLineName]
      active = self.activeLineName
      self.activeLineName = None # prevent saving old func params
      for func in self.functions:
        if func.id in params:
          func.setParams(params[func.id])
      self.activeLineName = active

  def clearFunctions(self):
    for func in self.functions:
      func.parameterChanged.disconnect(self.parameterChanged)
    self.functions = []

  def addFunction(self, funcName):
    for cls in self.funcClasses:
      if cls.name == funcName:
        f = cls(self.getLines(), self.view)
        f.parameterChanged.connect(self.parameterChanged)
        self.functions.append(f)
        return f
    raise RuntimeError('Function named "%s" is not defined' % funcName)

  def setFunctions(self, functions):
    self.clearFunctions()
    self.functions = functions
    self.restoreFuncParams()
    for func in self.functions:
      func.parameterChanged.connect(self.parameterChanged)
    self.updateFitCurve()

  def parameterChanged(self):
    self.saveFuncParams()
    self.updateFitCurve()

  def updateFitCurve(self):
    if self.fitCurveItem is None:
      return

    x, y = self.fitCurveItem.getData()
    y = np.sum([f.y(x) for f in self.functions], axis=0)
    self.fitCurveItem.setData(x=x, y=y)

  def updateDiffCurve(self):
    if self.diffCurveItem is None:
      return

    x, y = self.diffCurveItem.getData()
    y = np.sum([f.y(x) for f in self.functions], axis=0) - self.activeLine().y
    self.diffCurveItem.setData(x=x, y=y)

  def activeLine(self):
    if self.activeLineName and self.activeLineName in self.lineNameMap:
      return self.lineNameMap[self.activeLineName].normalize()
    return None

  def getLines(self):
    line = self.activeLine()
    if line:
      return [line]
    else:
      return [l.normalize() for l in self.lines]

  def getGraphItems(self, colorpicker):
    items = []
    x1, x2 = self.getXrange()
    x = np.linspace(x1, x2, 500)
    for i, f in enumerate(self.functions):
      items += f.getGraphItems(x, colorpicker.next())

    if len(self.functions) >= 2:
      if self.fitCurveItem is None:
        logging.debug('Generate "Fit" curve')
        self.fitCurveItem = pg.PlotCurveItem(
          x=x, y=np.zeros(len(x)), name='Fit', antialias=True)

      self.updateFitCurve()
      self.fitCurveItem.setPen(color=colorpicker.next(), width=2)
      items.append(self.fitCurveItem)

    if self.diffCurveItem is None:
      logging.debug('Generate "Diff" curve')
      x = self.activeLine().x
      self.diffCurveItem = pg.PlotCurveItem(
        x=x, y=np.zeros(len(x)), name='Diff', antialias=True)

    self.updateDiffCurve()
    self.diffCurveItem.setPen(color=colorpicker.next(), width=2)
    items.append(self.diffCurveItem)

    return items

  def setActiveLineName(self, name):
    self.activeLineName = name
    self.restoreFuncParams()

  def saveState(self):
    state = super().saveState()
    state['functions'] = [(f.name, f.id) for f in self.functions]
    state['func_params'] = self.funcParams
    if self.activeLineName:
      state['active_line'] = self.activeLineName
    return state

  def restoreState(self, state):
    super().restoreState(state)
    if 'functions' in state:
      self.clearFunctions()
      for name, id in state['functions']:
        try:
          f = self.addFunction(name)
          f.id = id
        except:
          log.warnException()
    if 'func_params' in state:
      self.funcParams = state['func_params']
    if 'active_line' in state:
      self.activeLineName = state['active_line']
    self.restoreFuncParams()
