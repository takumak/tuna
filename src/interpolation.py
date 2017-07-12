import numpy as np

from methodbase import MethodBase
from line import Line



class InterpBase(MethodBase):
  def do(self, line, dx, xrange = None):
    if len(line.x) == 0:
      return Line([], [], line.name)

    if xrange is not None:
      X1, X2 = xrange
    else:
      X1, X2 = min(line.x), max(line.x)

    x = np.arange(X1, X2, dx)
    y = self.calcY(line, x)
    return Line(x, y, line.name)

  def calcY(self, line, x):
    raise NotImplementedError()



class InterpLinear(InterpBase):
  name    = 'linear'
  label   = 'Linear'

  def calcY(self, line, x):
    from scipy.interpolate import interp1d
    return interp1d(line.x, line.y, 'linear')(x)



class InterpScipy(InterpBase):
  def calcY(self, line, x):
    import scipy.interpolate as interp
    return getattr(interp, self.clsname)(line.x, line.y)(x)

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
