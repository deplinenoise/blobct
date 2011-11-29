
class TargetMachine(object):
    def __init__(self, **kwargs):
        self.pointer_size = kwargs.get('pointer_size', 4)
        self.pointer_align = kwargs.get('pointer_align', self.pointer_size)
        self.big_endian = 'big' == kwargs.get('endian', 'little')
        self._sizes = {}

    def size_align(self, ntype):
        sz = self._sizes.get(ntype)
        if sz is None:
            sz = self._sizes[ntype] = ntype.compute_size(self)
        return sz

    def sizeof(self, ntype):
        return self.size_align(ntype)[0]

    def alignof(self, ntype):
        return self.size_align(ntype)[1]

