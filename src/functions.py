def getTableColumnLabel(c):
  label = ''
  while True:
    label += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[c % 26]
    if c <= 26:
      break
    c = int(c/26)
  return label
