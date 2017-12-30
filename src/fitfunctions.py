from fitfunctionbase import FitFunctionBase
from fitparameters import *
from fithandles import *



__all__ = [
  'FitFuncGaussian', 'FitFuncPseudoVoigt', 'FitFuncBoltzmann2',
  'FitFuncConstant', 'FitFuncLine', 'FitFuncHeaviside',
  'FitFuncRectangularWindow'
]



class FitFuncGaussian(FitFunctionBase):
  name = 'gaussian'
  label = 'Gaussian'
  expr = 'a*exp(-(x-b)**2/(2*c**2))'
  expr_excel = '%(a)s*exp(-((%(x)s-%(b)s)^2)/(2*(%(c)s^2)))'
  expr_latex = r'y=a\exp\left[-\frac{(x-b)^2}{2c^2}\right]'
  parameters = [
    ('a', 'Max height (at x=b)'),
    ('b', 'Center'),
    ('c', 'Standard deviation')
  ]

  def __init__(self, view):
    super().__init__(view)

    r = view.viewRect()
    x1, x2, y1, y2 = r.left(), r.right(), r.top(), r.bottom()
    self.addParam(FitParam('a', y2*0.6))
    self.addParam(FitParam('b', (x1 + x2)/2))
    self.addParam(FitParam('c', (x2 - x1)*0.1))
    self.addParam(self.eval('Area', 'sqrt(2*pi)*a*c', None))

    half = self.eval('half', 'a/2', None)
    x1 = self.eval('x1', 'b+c*sqrt(2*log(2))', self.c)
    self.addHandle(FitHandlePosition(view, self.b, self.a))
    self.addHandle(FitHandleLine(view, self.b, half, x1, half))



class FitFuncPseudoVoigt(FitFunctionBase):
  name = 'pseudovoigt'
  label = 'PseudoVoigt'
  expr = 'a*(m*(w**2)/(4*(x-x0)**2+w**2) + (1-m)*exp(-4*ln(2)/(w**2)*(x-x0)**2))'
  expr_excel = '%(a)s*(%(m)s*(%(w)s^2)/(4*((%(x)s-%(x0)s)^2)+w^2) + (1-%(m)s)*exp(-4*ln(2)/(%(w)s^2)*((%(x)s-%(x0)s)^2)))'
  expr_latex = r'y=a\left\{ m\frac{w^2}{4(x-x_0)^2 + w^2} + (1-m)\exp\left[-\frac{4\ln2}{w^2}(x-x_0)^2\right] \right\}'
  parameters = [
    ('a', 'Max height (at x=x0)'),
    ('x0', 'Center'),
    ('w', 'HWHM'),
    ('m', 'Mix ratio')
  ]

  def __init__(self, view):
    super().__init__(view)

    r = view.viewRect()
    x1, x2, y1, y2 = r.left(), r.right(), r.top(), r.bottom()
    self.addParam(FitParam('a', y2*0.6))
    self.addParam(FitParam('x0', (x1 + x2)/2))
    self.addParam(FitParam('w', (x2 - x1)*0.1))
    self.addParam(FitParam('m', 0.1))
    self.addParam(self.eval('Area', 'a*(pi*sqrt(ln(2))*m*w + sqrt(pi)*(1-m)*w)/(2*sqrt(ln(2)))', None))

    half = self.eval('half', 'a/2', None)
    x1 = self.eval('x1', 'x0+w/2', self.w)
    self.addHandle(FitHandlePosition(view, self.x0, self.a))
    self.addHandle(FitHandleLine(view, self.x0, half, x1, half))



class FitFuncBoltzmann2(FitFunctionBase):
  name = 'boltzmann2'
  label = 'Boltzmann 2'
  expr = '(a1*x+b1)/(1+exp((x-x0)/dx)) + (a2*x+b2)*(1-1/(1+exp((x-x0)/dx)))'
  expr_latex = r'y=(a_1x+b_1)\frac{1}{1+\exp[(x-x_0)/dx]} + (a_2x+b_2)\left\{1 - \frac{1}{1+\exp[(x-x_0)/dx]}\right\}'
  parameters = [
    ('a1', 'Slope of line 1'),
    ('b1', 'Y-intercept of line 1'),
    ('a2', 'Slope of line 2'),
    ('b2', 'Y-intercept of line 2'),
    ('x0', 'Center'),
    ('dx', 'Transition factor')
  ]

  def __init__(self, view):
    super().__init__(view)

    r = view.viewRect()
    x1, x2, y1, y2 = r.left(), r.right(), r.top(), r.bottom()
    self.addParam(FitParam('a1', 0))
    self.addParam(FitParam('b1', 0))
    self.addParam(FitParam('a2', 0))
    self.addParam(FitParam('b2', y2*0.8))
    self.addParam(FitParam('x0', (x1+x2)/2))
    self.addParam(FitParam('dx', 1))


    y0 = '(a1*x0+b1)/2 + (a2*x0+b2)/2'
    y0 = self.eval('y0', y0, None)
    x1 = self.eval('x1', 'x0+2*dx', self.dx)
    self.addHandle(FitHandleLine(view, self.x0, y0, x1, y0))
    self.addHandle(FitHandlePosition(view, self.x0, y0))


    self.addParam(FitParam('cx1', self.x0.value(), hidden=True))
    self.addParam(FitParam('cy1', self.b1.value(), hidden=True))
    self.a1.valueChanged.connect(lambda: self.setB(1))
    self.b1.valueChanged.connect(lambda: self.setcy(1))
    self.cx1.valueChanged.connect(lambda: self.setB(1))
    self.cy1.valueChanged.connect(lambda: self.setB(1))
    self.addHandle(FitHandleGradient(view, self.cx1, self.cy1, self.a1, 50, False))
    self.addHandle(FitHandlePosition(view, self.cx1, self.cy1))

    self.addParam(FitParam('cx2', self.x0.value(), hidden=True))
    self.addParam(FitParam('cy2', self.b2.value(), hidden=True))
    self.a2.valueChanged.connect(lambda: self.setB(2))
    self.b2.valueChanged.connect(lambda: self.setcy(2))
    self.cx2.valueChanged.connect(lambda: self.setB(2))
    self.cy2.valueChanged.connect(lambda: self.setB(2))
    self.addHandle(FitHandleGradient(view, self.cx2, self.cy2, self.a2, 50))
    self.addHandle(FitHandlePosition(view, self.cx2, self.cy2))

  def setB(self, num):
    cx = getattr(self, 'cx%d' % num)
    cy = getattr(self, 'cy%d' % num)
    a = getattr(self, 'a%d' % num)
    b = getattr(self, 'b%d' % num)
    b.setValue(cy.value() - a.value()*cx.value())

  def setcy(self, num):
    cx = getattr(self, 'cx%d' % num)
    cy = getattr(self, 'cy%d' % num)
    a = getattr(self, 'a%d' % num)
    b = getattr(self, 'b%d' % num)
    cy.setValue(a.value()*cx.value()+b.value())



class FitFuncConstant(FitFunctionBase):
  name = 'constant'
  label = 'Constant'
  expr = 'y0'
  expr_latex = r'y=y_0'
  parameters = [('y0', '')]

  def __init__(self, view):
    super().__init__(view)
    r = view.viewRect()
    x1, x2, y1, y2 = r.left(), r.right(), r.top(), r.bottom()
    self.addParam(FitParam('y0', y2*0.8))
    self.addParam(FitParam('x0', x1, hidden=True))
    self.addHandle(FitHandlePosition(view, self.x0, self.y0))



class FitFuncLine(FitFunctionBase):
  name = 'line'
  label = 'Line'
  expr = 'a*x+b'
  expr_latex = r'ax+b'
  parameters = [
    ('a', None),
    ('b', None)
  ]

  def __init__(self, view):
    super().__init__(view)

    r = view.viewRect()
    x1, x2, y1, y2 = r.left(), r.right(), r.top(), r.bottom()
    self.addParam(FitParam('a', (y2-y1)/(x2-x1)))
    self.addParam(FitParam('b', y1-self.a.value()*x1))


    cx = (x1+x2)/2
    cy = self.a.value()*cx+self.b.value()
    self.addParam(FitParam('cx', cx, hidden=True))
    self.addParam(FitParam('cy', cy, hidden=True))
    self.a.valueChanged.connect(self.setB)
    self.b.valueChanged.connect(self.setcy)
    self.cx.valueChanged.connect(self.setB)
    self.cy.valueChanged.connect(self.setB)
    self.addHandle(FitHandleGradient(view, self.cx, self.cy, self.a, 50))
    self.addHandle(FitHandlePosition(view, self.cx, self.cy))

  def setB(self):
    self.b.setValue(self.cy.value() - self.a.value()*self.cx.value())

  def setcy(self):
    self.cy.setValue(self.a.value()*self.cx.value()+self.b.value())



class FitFuncHeaviside(FitFunctionBase):
  name = 'heaviside'
  label = 'Heaviside'
  expr = 'a*heaviside(x-x0, 1)'
  expr_latex = r'''
y=a\cdot\begin{cases}
  0 & (x < x_0) \\
  1 & (x_0 \le x)
\end{cases}
'''
  parameters = [
    ('a', None),
    ('x0', None)
  ]

  def __init__(self, view):
    super().__init__(view)

    r = view.viewRect()
    x1, x2, y1, y2 = r.left(), r.right(), r.top(), r.bottom()
    self.addParam(FitParam('a', y2*0.8))
    self.addParam(FitParam('x0', (x1 + x2)/2))

    self.addHandle(FitHandlePosition(view, self.x0, self.a))



class FitFuncRectangularWindow(FitFunctionBase):
  name = 'rectangularwinow'
  label = 'Rectangular window'
  expr = 'a*heaviside(x-x0, 1)*heaviside(-(x-x1), 1)'
  expr_latex = r'''
y=a\cdot\begin{cases}
  0 & (x < x_0) \\
  1 & (x_0 \le x \le x_1) \\
  0 & (x_0 < x)
\end{cases}
'''
  parameters = [
    ('a', None),
    ('x0', None),
    ('x1', None)
  ]

  def __init__(self, view):
    super().__init__(view)

    r = view.viewRect()
    x1, x2, y1, y2 = r.left(), r.right(), r.top(), r.bottom()
    self.addParam(FitParam('a', y2*0.8))
    self.addParam(FitParam('x0', x1 + (x2-x1)*0.2))
    self.addParam(FitParam('x1', x2 - (x2-x1)*0.2))

    self.addHandle(FitHandlePosition(view, self.x0, self.a))
    self.addHandle(FitHandlePosition(view, self.x1, self.a))
