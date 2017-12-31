import numpy as np

from settingobj import SettingObj
from settingitems import *
from commonwidgets import *



__all__ = ['InterpLinear', 'InterpBSpline',
           'InterpCubicSpline', 'InterpBarycentric',
           'InterpKrogh', 'InterpPchip', 'InterpAkima']



class InterpBase(SettingObj):
  def func(self, x, y):
    raise NotImplementedError()



class InterpLinear(InterpBase):
  name = 'linear'
  label = 'Linear'

  def func(self, x, y):
    from scipy.interpolate import interp1d
    return interp1d(x, y, 'linear')

  def descriptionWidget(self):
    w = DescriptionWidget()
    w.addTitle(self.label)
    url = 'https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.interp1d.html'
    w.addLabel('''
This runs <code>scipy.interpolate.interp1d(x, y, "linear")</code>.<br>
<a href="{0}">{0}</a>
'''.format(url).strip(), richtext=True)
    return w



class InterpBSpline(InterpBase):
  name = 'b_spline'
  label = 'B-spline'

  def __init__(self):
    super().__init__()
    self.addSettingItem(SettingItemStr('w', 'Weight (function of x,y)', '1'))

  def func(self, x, y):
    from sympy import sympify, lambdify
    from scipy.interpolate import splrep, splev
    w = lambdify(['x', 'y'], sympify(self.w.strValue()), 'numpy')(x, y)
    try:
      iter(w)
    except:
      w = np.full(x.shape, w)
    spl = splrep(x, y, w=w)
    return lambda x: splev(x, spl)



class InterpScipy(InterpBase):
  def func(self, x, y):
    import scipy.interpolate as interp
    return getattr(interp, self.clsname)(x, y)

  def descriptionWidget(self):
    modname = 'scipy.interpolate.%s' % self.clsname
    w = DescriptionWidget()
    w.addTitle(self.label)
    url = 'https://docs.scipy.org/doc/scipy/reference/generated/%s.html' % modname
    w.addLabel('''
This uses <code>{0}</code>.<br>
<a href="{1}">{1}</a>
'''.format(modname, url).strip(), richtext=True)
    return w

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
