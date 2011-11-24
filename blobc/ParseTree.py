class RawDefPrimitive(object):
    def __init__(self, name, pclass, size, loc):
        self.name = name
        self.pclass = pclass
        self.size = size
        self.loc = loc

class RawStructType(object):
    def __init__(self, name, members, loc):
        self.name = name
        self.members = members
        self.loc = loc

class RawType(object):
    def __init__(self, loc):
        self.loc = loc

class RawSimpleType(RawType):
    def __init__(self, name, loc):
        RawType.__init__(self, loc)
        self.name = name

class RawPointerType(RawType):
    def __init__(self, basetype, loc):
        RawType.__init__(self, loc)
        self.basetype = basetype

class RawArrayType(RawType):
    def __init__(self, basetype, dims, loc):
        RawType.__init__(self, loc)
        self.basetype = basetype
        self.dims = dims

class RawStructMember(object):
    def __init__(self, type, name, loc):
        object.__init__(self)
        self.type = type
        self.name = name
        self.loc = loc
