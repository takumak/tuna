def getTableColumnLabel(c):
  label = ''
  while True:
    label += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[c % 26]
    if c <= 26:
      break
    c = int(c/26)
  return label

def parseTableColumnLabel(label):
  ret = 0
  for c in map(ord, reversed(label)):
    if 0x41 <= c <= 0x5A:
      ret = ret*26 + (c-0x41)
    else:
      raise ValueError('Invalid label: %s' % label)
  return ret
