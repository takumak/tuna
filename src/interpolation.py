import numpy as np

from settingobj import SettingObj
from settingitems import *
from commonwidgets import *



__all__ = ['InterpLinear', 'InterpUnivariateSpline',
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
    w.addLabel('This runs <code>scipy.interpolate.interp1d(x, y, "linear")</code>.', richtext=True)
    url = 'https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.interp1d.html'
    w.addLabel('For more details, see <a href="%s">scipy document</a>.' % url, richtext=True)
    return w



class InterpUnivariateSpline(InterpBase):
  name = 'univariate_spline'
  label = 'Univariate spline'

  def __init__(self):
    super().__init__()
    self.addSettingItem(SettingItemInt('k', 'Spline degree', 3, min_=3, max_=5))
    self.addSettingItem(SettingItemFloat('s', 'Smoothing factor', 10, min_=0, emptyIsNone=True))

  def func(self, x, y):
    from scipy.interpolate import UnivariateSpline
    return UnivariateSpline(x, y, k=self.k.value(), s=self.s.value())



class InterpScipy(InterpBase):
  def func(self, x, y):
    import scipy.interpolate as interp
    return getattr(interp, self.clsname)(x, y)

  def descriptionWidget(self):
    modname = 'scipy.interpolate.%s' % self.clsname
    w = DescriptionWidget()
    w.addTitle(self.label)
    w.addLabel('This uses <code>%s</code>.' % modname, richtext=True)
    url = 'https://docs.scipy.org/doc/scipy/reference/generated/%s.html' % modname
    w.addLabel('For more details, see <a href="%s">scipy document</a>.' % url, richtext=True)
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
