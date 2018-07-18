import struct
caches = {}

def getOrSetNew(dicToCheck, key, newFunc):
    if key not in dicToCheck:
        dicToCheck[key] = newFunc()
    return dicToCheck[key]

def memoize(name = None):
    def decorator(f):
        global caches
        # If we are given a valid name for the function, associate it with that entry in the cache.
        if name is not None:
            cache = getOrSetNew(caches, name, lambda: {})
        else:
            cache = {}
        def g(*args):
            return getOrSetNew(cache, args, lambda: f(*args))
        # Set the cache as a function attribute so we can access it later (say for serialization)
        g.cache = cache
        return g
    return decorator

@memoize()
def readRom(romFileName):
    words = []
    with open(romFileName, 'rb') as rom:
        while True:
            word = rom.read(4)
            if word == b'':
                break
            words.append(struct.unpack('<I', word)[0]) #Use the raw data;
            # <I is little-endian 32 bit unsigned integer
    return words

@memoize(name = 'pointerOffsets')
def pointerOffsets(romFileName, value):
    return tuple(pointerIter(romFileName, value))

def pointerIter(romFileName, value):
    words = readRom(romFileName)
    return (i<<2 for i,x in enumerate(words) if x==value)

def writeCache():
    import pickle
    with open("./.cache", 'wb') as f:
        pickle.dump(caches, f, pickle.HIGHEST_PROTOCOL)

cachesLoaded = False
def loadCache():
    global cachesLoaded
    if not cachesLoaded:
        import os, pickle
        if os.path.exists("./.cache"):
            try:
                with open("./.cache", 'rb') as f:
                    caches = pickle.load(f)
                    if type(caches) != dict: raise Exception
            except Exception:
                caches = {}
        cachesLoaded = True

loadCache()

def deleteCache():
    for name in caches:
        caches[name] = {}
    writeCache()
