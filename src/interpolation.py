import numpy as np

from methodbase import MethodBase, ParamInt, ParamFloat


class InterpBase(MethodBase):
  def func(self, x, y):
    raise NotImplementedError()



class InterpLinear(InterpBase):
  name  = 'linear'
  label = 'Linear'

  def func(self, x, y):
    from scipy.interpolate import interp1d
    return interp1d(x, y, 'linear')



class InterpUnivariateSpline(InterpBase):
  name  = 'univariate_spline'
  label = 'Univariate spline'

  def __init__(self):
    super().__init__()
    self.addParam(ParamInt('k', 'Spline degree', 3, min_=3, max_=5))
    self.addParam(ParamFloat('s', 'Smoothing factor', 10, min_=0, emptyIsNone=True))

  def func(self, x, y):
    from scipy.interpolate import UnivariateSpline
    return UnivariateSpline(x, y, k=self.k.intValue(), s=self.s.floatValue())



class InterpScipy(InterpBase):
  def func(self, x, y):
    import scipy.interpolate as interp
    return getattr(interp, self.clsname)(x, y)

class InterpCubicSpline(InterpScipy):
  name    = 'cubic_spline'
  label   = 'Cubic spline'
  clsname = 'CubicSpline'

class InterpBarycentric(InterpScipy):
  name    = 'barycentric'
  label   = 'Barycentric'
  clsname = 'BarycentricInterpolator'

class InterpKrogh(InterpScipy):
  name    = 'krogh'
  label   = 'Krogh'
  clsname = 'KroghInterpolator'

class InterpPchip(InterpScipy):
  name    = 'pchip'
  label   = 'Pchip'
  clsname = 'PchipInterpolator'

class InterpAkima(InterpScipy):
  name    = 'akima'
  label   = 'Akima'
  clsname = 'Akima1DInterpolator'
