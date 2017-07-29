import operator

from settingitems import SettingItemFloat



__all__ = ['FitParameter', 'FitParameterConst', 'FitParameterFunc', 'FitParameterOp']



class FitParameter(SettingItemFloat):
  def __init__(self, *args, **kwargs):
    if len(args) == 1 and isinstance(args[0], FitParameter):
      self.parent = args[0]
      self.parent.valueChanged.connect(lambda: self.valueChanged.emit())

      p = self.parent
      super().__init__(
        p.name, p.label, p.default, validator=p.validator,
        min_=p.min_, max_=p.max_, emptyIsNone=p.emptyIsNone)
    else:
      self.parent = None
      name, default = args
      super().__init__(name, name, default, **kwargs)

  def value(self):
    if self.parent:
      return self.parent.value()
    return super().value()

  def setValue(self, value):
    if self.max_ is not None and value > self.max_: value = self.max_
    if self.min_ is not None and value < self.min_: value = self.min_

    if self.parent:
      self.parent.setValue(value)
      return
    super().setStrValue(str(value))

  def __add__(self, b):
    return FitParameterOp(operator.add, operator.sub, '+', self, b)

  def __radd__(self, b):
    return FitParameterOp(operator.add, operator.sub, '+', self, b)

  def __sub__(self, b):
    return FitParameterOp(operator.sub, lambda v,b: b-v, '-', self, b)

  def __rsub__(self, b):
    return FitParameterOp(lambda s,b: b-s, operator.add, '-', self, b)

  def __mul__(self, b):
    return FitParameterOp(operator.mul, operator.truediv, '*', self, b)

  def __rmul__(self, b):
    return FitParameterOp(operator.mul, operator.truediv, '*', self, b)

  def __truediv__(self, b):
    return FitParameterOp(operator.truediv, operator.mul, '/', self, b)

  def __neg__(self):
    return self*(-1)

  def __pow__(self, b):
    return FitParameterOp(operator.pow, lambda v,b: v**(1/b), '/', self, b)


class FitParameterConst(FitParameter):
  def setValue(self, value):
    pass


class FitParameterFunc(FitParameter):
  def __init__(self, name, f, fi, *args):
    self.f = f
    self.fi = fi
    self.args = args
    super().__init__(name, self.value())
    for a in self.args:
      a.valueChanged.connect(lambda: self.valueChanged.emit())

  def value(self):
    return self.f(*[a.value() for a in self.args])

  def setValue(self, value):
    if self.fi:
      self.args[0].setValue(self.fi(value, *[a.value() for a in self.args[1:]]))


class FitParameterOp(FitParameter):
  def __init__(self, op, opi, opname, a, b):
    if not isinstance(a, FitParameter):
      a = FitParameterConst(repr(a), a)
    if not isinstance(b, FitParameter):
      b = FitParameterConst(repr(b), b)

    super().__init__('(%s%s%s)' % (a.name, opname, b.name), 0)

    self.op  = op
    self.opi = opi
    self.a   = a
    self.b   = b

    a.valueChanged.connect(lambda: self.valueChanged.emit())
    b.valueChanged.connect(lambda: self.valueChanged.emit())

  def value(self):
    return self.op(self.a.value(), self.b.value())

  def setValue(self, value):
    self.a.setValue(self.opi(value, self.b.value()))
