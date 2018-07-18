def memoize(f):
    cache = {}
    def g(*args):
        if args in cache:
            return cache[args]
        else:
            res = f(*args)
            cache[args] = res
            return res
    #Set the cache as a function attribute so we can access it later (say for serialization)
    g.cache = cache
    return g

@memoize
def readRom(romFileName):
    words = []
    with open(romFileName, 'rb') as rom:
        while True:
            word = rom.read(4)
            if word == b'':
                break
            words.append(word)
    return words

@memoize
def pointerOffsets(romFileName, value):
    return tuple(pointerIter(romFileName, value))

def pointerIter(romFileName, value):
    target = value.to_bytes(4, 'little')
    words = readRom(romFileName)
    return (i<<2 for i,x in enumerate(words) if x==target)
