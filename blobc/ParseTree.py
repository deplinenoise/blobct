class RawDefPrimitive(object):
    def __init__(self, name, pclass, size, loc):
        self.name = name
        self.pclass = pclass
        self.size = size
        self.loc = loc

class RawOptionParam(object):
    def __init__(self, name, value, loc):
        self.name, self.value, self.loc = name, value, loc

class RawNamedOption(object):
    def __init__(self, name, params, loc):
        self.name, self.loc = name, loc
        self.__params = params
        self.__pos_params = [p.value for p in params if not p.name]
        self.__kw_params = dict((p.name, p.value) for p in params if p.name is not None)

    def pos_param_count(self):
        return len(self.__pos_params)

    def pos_param(self, i):
        return self.__pos_params[i]

    def pos_params(self):
        return self.__pos_params

    def iter_pos_params(self, name):
        return iter(self.__pos_params)

    def iter_params(self, name):
        return iter(self.__params)

    def kw_params(self):
        return self.__kw_params

    def has_kw_param(self, name):
        return self.__kw_params.has_key(name)

    def kw_param(self, name, default=None):
        if default is not None:
            return self.__kw_params.get(name, default)
        else:
            return self.__kw_params[name]

class RawEnumType(object):
    def __init__(self, name, members, loc):
        self.name, self.members, self.loc = name, members, loc

class RawEnumMember(object):
    def __init__(self, name, value, loc):
        self.name, self.value, self.loc = name, value, loc

class RawStructType(object):
    def __init__(self, name, members, options, loc):
        self.name = name
        self.members = members
        self.loc = loc
        self.options = options

    def get_options(self, tag):
        if self.options:
            return [o for o in self.options if o.name == tag]
        else:
            return []

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

class RawImportStmt(object):
    def __init__(self, filename, loc):
        self.filename = filename
        self.loc = loc

class RawVoidType(RawType):
    pass

RawVoidType.instance = RawVoidType(None)

class SourceLocation(object):
    def __init__(self, filename, lineno, is_import):
        self.filename, self.lineno, self.is_import = filename, lineno, is_import

class GeneratorConfig(object):
    def __init__(self, generator_name, options, loc):
        self.generator_name, self.options, self.loc = generator_name, options, loc
