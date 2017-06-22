from PyQt5.QtWidgets import QGraphicsItem
import operator

class FitParameter:
  def __init__(self, name, value, handlefunc = None, handlefunc_i = None):
    self.name = name
    self.value_ = value
    self.handlefunc = handlefunc
    self.handlefunc_i = handlefunc_i

  def value(self):
    return self.value_

  def setValue(self, value):
    self.value_ = value

  def getHandleValue(self):
    if self.handlefunc:
      return self.handlefunc(self.value())
    return self.value()

  def setHandleValue(self, value):
    if self.handlefunc_i:
      value = self.handlefunc_i(value)
    self.setValue(value)


  def __add__(self, b):
    return FitParameterOp(operator.add, '+', self, b)

  def __sub__(self, b):
    return FitParameterOp(operator.sub, '-', self, b)

  def __mul__(self, b):
    return FitParameterOp(operator.mul, '*', self, b)

  def __div__(self, b):
    return FitParameterOp(operator.div, '/', self, b)


class FitParameterConst(FitParameter):
  def setValue(self, value):
    pass


class FitParameterOp(FitParameterConst):
  def __init__(self, op, opname, a, b):
    super().__init__('(%s%s%s)' % (a.name, opname, b.name), 0)
    self.op = op
    self.a  = a
    self.b  = b

  def value(self):
    return self.op(self.a.value(), self.b.value())


class FitHandleBase:
  def getGraphicsItem(self):
    raise NotImplementedError()


class FitHandlePosition(FitHandleBase):
  def __init__(self, param_x, param_y):
    self.param_x = param_x
    self.param_y = param_y

  def getGraphicsItem(self):
    item = QGraphicsItem()
    # QGraphicsEllipseItem


class FitHandleLength(FitHandleBase):
  def __init__(self, param_cx, param_cy, param_theta, param_len):
    self.cx = cx
    self.cy = cy
    self.theta = theta


class FitFunctionBase:
  def __init__(self, lines):
    self.params = []
    self.paramsNameMap = {}
    self.handles = []

  def __getattr__(self, name):
    if name in self.paramsNameMap:
      return self.paramsNameMap[name]
    raise AttributeError()

  def addParam(self, param):
    self.params.append(param)
    self.paramsNameMap[param.name] = param

  def addHandle(self, handle):
    self.handles.append(handle)

  def getXrange(self, lines):
    l1, l2 = zip(*[l.getXrange() for l in lines])
    return min(l1), max(l2)

  def getYrange(self, lines):
    l1, l2 = zip(*[l.getYrange() for l in lines])
    return min(l1), max(l2)

  def getWidth(self, lines):
    x1, x2 = self.get_Xrange(lines)
    return x2 - x1

  def getHeight(self, lines):
    y1, y2 = self.get_Yrange(lines)
    return y2 - y1


class FitFuncGaussian(FitFunctionBase):
  def __init__(self, lines):
    super().__init__(lines)

    x1, x2 = self.getXrange(lines)
    self.addParam(FitParameter('a', self.getHeight(lines)*0.6))
    self.addParam(FitParameter('b', (x1 + x2)/2))
    self.addParam(FitParameter('c', (x2 - x1)*0.6), self.HWHM, self.HWHM_i)

    self.addHandle(FitHandlePosition(self.b, self.a))
    self.addHandle(FitHandlePosition(self.c, None))

  def y(self, x):
    return self.a.value()*np.exp(-(x-self.b.value())**2/(2*self.c.value()**2))

  def HWHM(self, value):
    return (2*np.ln(2))**.5*value

  def HWHM_i(self, value):
    return value/(2*np.ln(2))**.5
