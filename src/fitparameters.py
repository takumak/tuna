import operator

from settingitems import *



__all__ = ['FitParameter', 'FitParameterConst', 'FitParameterFunc']



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

    from numbers import Number
    if not isinstance(value, Number):
      raise TypeError('Fit parameter value must be a number, but got %s' % value)

    super().setStrValue(str(value))



class FitParameterConst(FitParameter):
  def setValue(self, value):
    pass



class FitParameterFunc(FitParameter):
  def __init__(self, name, get_, set_, refargs):
    self.get_ = get_
    self.set_ = set_
    super().__init__(name, self.value())
    for a in refargs:
      a.valueChanged.connect(lambda: self.valueChanged.emit())

  def value(self):
    return self.get_()

  def setValue(self, value):
    if self.set_:
      self.set_(value)
