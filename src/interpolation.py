import numpy as np

from methodbase import MethodBase
from line import Line



class InterpBase(MethodBase):
  # def do(self, line, dx, xrange = None):
  #   if len(line.x) == 0:
  #     return Line([], [], line.name)

  #   if xrange is not None:
  #     X1, X2 = xrange
  #   else:
  #     X1, X2 = min(line.x), max(line.x)

  #   x = np.arange(X1, X2, dx)
  #   y = self.func(line)(x)
  #   return Line(x, y, line.name)

  def func(self, line):
    raise NotImplementedError()



class InterpLinear(InterpBase):
  name    = 'linear'
  label   = 'Linear'

  def func(self, line):
    from scipy.interpolate import interp1d
    return interp1d(line.x, line.y, 'linear')



class InterpScipy(InterpBase):
  def func(self, line):
    import scipy.interpolate as interp
    return getattr(interp, self.clsname)(line.x, line.y)

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
