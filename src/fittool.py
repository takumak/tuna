import logging
import numpy as np
import pyqtgraph as pg

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
    self.activeLineName = None
    self.funcParams = {}
    self.view = None

  def setView(self, view):
    self.view = view

  def addFunc(self, funcName):
    for cls in self.funcClasses:
      if cls.name == funcName:
        return cls(self.getLines(), self.view)
    raise RuntimeError('Function named "%s" is not defined' % funcName)

  def saveFuncParams(self):
    if self.activeLineName:
      logging.info('Save func params')
      if self.activeLineName not in self.funcParams:
        self.funcParams[self.activeLineName] = {}
      params = self.funcParams[self.activeLineName]
      for func in self.functions:
        params[func.id] = func.getParams()

  def restoreFuncParams(self):
    if self.activeLineName and self.activeLineName in self.funcParams:
      logging.info('Restore func params')
      params = self.funcParams[self.activeLineName]
      active = self.activeLineName
      self.activeLineName = None # prevent saving old func params
      for func in self.functions:
        if func.id in params:
          func.setParams(params[func.id])
      self.activeLineName = active

  def setFunctions(self, functions):
    for func in self.functions:
      func.parameterChanged.disconnect(self.parameterChanged)
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

  def activeLine(self):
    if self.activeLineName and self.activeLineName in self.lineNameMap:
      return self.lineNameMap[self.activeLineName]
    return None

  def getLines(self):
    line = self.activeLine()
    if line:
      return [line.normalize()]
    else:
      return [l.normalize() for l in self.lines]

  def getGraphItems(self, colorpicker):
    items = []
    x1, x2 = self.getXrange()
    x = np.linspace(x1, x2, 500)
    for i, f in enumerate(self.functions):
      items += f.getGraphItems(x, colorpicker.next())

    if self.fitCurveItem is None and len(self.functions) > 0:
      self.fitCurveItem = pg.PlotCurveItem(
        x=x, y=np.zeros(len(x)), name='Fit', antialias=True)

    if self.fitCurveItem:
      self.updateFitCurve()
      self.fitCurveItem.setPen(color=colorpicker.next(), width=2)
      items.append(self.fitCurveItem)

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
      self.functions = []
      for name, id in state['functions']:
        try:
          f = self.addFunc(name)
        except:
          log.warnException()
        f.id = id
        self.functions.append(f)
    if 'func_params' in state:
      self.funcParams = state['func_params']
    if 'active_line' in state:
      self.setActiveLineName(state['active_line'])
