
class TargetMachine(object):
    def __init__(self, **kwargs):
        self.__pointer_size = kwargs.get('pointer_size', 4)
        self.__pointer_align = kwargs.get('pointer_align', self.__pointer_size)
        self.__isbig = 'big' == kwargs.get('endian', 'little')
        self.__sizes = {}

    def pointer_size(self):
        return self.__pointer_size

    def pointer_align(self):
        return self.__pointer_align

    def big_endian(self):
        return self.__isbig

    def size_align(self, ntype):
        sz = self.__sizes.get(ntype)
        if sz is None:
            sz = self.__sizes[ntype] = ntype.compute_size(self)
        return sz

    def sizeof(self, ntype):
        return self.size_align(ntype)[0]

    def alignof(self, ntype):
        return self.size_align(ntype)[1]

