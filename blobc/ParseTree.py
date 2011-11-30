import blobc

class OptionContainer(object):
    def __init__(self, options):
        self._options = options

    def get_options(self, tag):
        if self._options:
            return [o for o in self._options if o.name == tag]
        else:
            return []

class RawDefPrimitive(OptionContainer):
    def __init__(self, name, pclass, size, options, loc):
        OptionContainer.__init__(self, options)
        self.name = name
        self.pclass = pclass
        self.size = size
        self.location = loc

class RawOptionParam(object):
    def __init__(self, name, value, loc):
        self.name, self.value, self.loc = name, value, loc

class RawNamedOption(object):
    def __init__(self, name, params, loc):
        self.name, self.location = name, loc
        self.params = params
        self.pos_params = [p.value for p in params if not p.name]
        self.kw_params = dict((p.name, p.value) for p in params if p.name is not None)

    def has_kw_param(self, name):
        return self.kw_params.has_key(name)

    def kw_param(self, name, default=None):
        if default is not None:
            return self.kw_params.get(name, default)
        else:
            return self.kw_params[name]

class RawEnumType(object):
    def __init__(self, name, members, loc):
        self.name, self.members, self.location = name, members, loc

class RawEnumMember(object):
    def __init__(self, name, expr, loc):
        self.name, self.expr, self.location = name, expr, loc

class RawStructType(OptionContainer):
    def __init__(self, name, members, options, loc):
        OptionContainer.__init__(self, options)
        self.name = name
        self.members = members
        self.location = loc

class RawType(object):
    def __init__(self, loc):
        self.location = loc

class RawSimpleType(RawType):
    def __init__(self, name, loc):
        RawType.__init__(self, loc)
        self.name = name

class RawPointerType(RawType):
    def __init__(self, basetype, loc, is_cstring=False):
        RawType.__init__(self, loc)
        self.is_cstring = is_cstring
        self.basetype = basetype

class RawArrayType(RawType):
    def __init__(self, basetype, dims, loc):
        RawType.__init__(self, loc)
        self.basetype = basetype
        self.dims = dims

class RawStructMember(OptionContainer):
    def __init__(self, type, name, options, loc):
        OptionContainer.__init__(self, options)
        self.type = type
        self.name = name
        self.location = loc

class RawImportStmt(object):
    def __init__(self, filename, loc):
        self.filename = filename
        self.location = loc

class RawVoidType(RawType):
    pass

class RawConstant(object):
    def __init__(self, name, expr, loc):
        self.name, self.expr, self.location = name, expr, loc

RawVoidType.instance = RawVoidType(None)

class SourceLocation(object):
    def __init__(self, filename, lineno, is_import):
        self.filename, self.lineno, self.is_import = filename, lineno, is_import

class GeneratorConfig(object):
    def __init__(self, generator_name, options, loc):
        self.generator_name, self.options, self.location = generator_name, options, loc

class RawExpr(object):
    def __init__(self, loc):
        self.location = loc

class RawIntLiteralExpr(RawExpr):
    def __init__(self, loc, value):
        RawExpr.__init__(self, loc)
        self.value = value

    def eval(self, env):
        return self.value

class RawNamedConstantExpr(RawExpr):
    def __init__(self, loc, name):
        RawExpr.__init__(self, loc)
        self.name = name

    def eval(self, env):
        return env.lookup_value(self.location, self.name)

class RawNegateExpr(RawExpr):
    def __init__(self, loc, expr):
        RawExpr.__init__(self, loc)
        self.expr = expr

    def eval(self, env):
        return -self.expr.eval(env)

class RawBinOpExpr(RawExpr):
    def __init__(self, loc, l, r):
        RawExpr.__init__(self, loc)
        self.lhs, self.rhs = l, r

    def eval_l(self, env):
        return self.lhs.eval(env)

    def eval_r(self, env):
        return self.rhs.eval(env)

class RawMulExpr(RawBinOpExpr):
    TOKEN = '*'
    def eval(self, env):
        return self.eval_l(env) * self.eval_r(env)

class RawDivExpr(RawBinOpExpr):
    TOKEN = '/'
    def eval(self, env):
        l = self.eval_l(env)
        r = self.eval_r(env)
        if r == 0:
            raise blobc.ParseError(self.location.filename, self.location.lineno, "division by zero")
        return l / r

class RawAddExpr(RawBinOpExpr):
    TOKEN = '+'
    def eval(self, env):
        return self.eval_l(env) + self.eval_r(env)

class RawSubExpr(RawBinOpExpr):
    TOKEN = '-'
    def eval(self, env):
        return self.eval_l(env) - self.eval_r(env)

class RawShiftLeftExpr(RawBinOpExpr):
    TOKEN = '<<'
    def eval(self, env):
        return self.eval_l(env) << self.eval_r(env)

class RawShiftRightExpr(RawBinOpExpr):
    TOKEN = '>>'
    def eval(self, env):
        return self.eval_l(env) >> self.eval_r(env)
