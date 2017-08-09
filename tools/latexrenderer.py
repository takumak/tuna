import sys, os
from io import BytesIO
import sympy
from PIL import Image, ImageOps, ImageChops


rootdir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
srcdir = os.path.join(rootdir, 'src')
sys.path.insert(0, srcdir)


latexsources = []

import fitfunctions
for name in fitfunctions.__all__:
  cls = getattr(fitfunctions, name)
  latexsources.append(('fitfunc_%s' % cls.name, cls.expr_latex))


with open(os.path.join(srcdir, 'lateximgs.py'), 'w') as f:
  for name, src in latexsources:
    buf = BytesIO()
    sympy.preview('\\[\n%s\n\\]' % src.strip(),
                  output='png',
                  viewer='BytesIO',
                  outputbuffer=buf,
                  euler=False)

    im = Image.open(buf)
    alpha = ImageOps.invert(im.convert('L'))
    im = ImageChops.constant(im, 0)
    im.putalpha(alpha)
    buf2 = BytesIO()
    im.save(buf2, 'png')

    f.write('%s = %s\n' % (name, repr(buf2.getvalue())))
