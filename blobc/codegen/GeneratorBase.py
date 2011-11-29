import blobc

class GeneratorException(Exception):
    pass

class GeneratorBase(object):
    def __init__(self):
        self._curr_option = None

    def bad_option(self, msg):
        o = self._curr_option
        loc = o.location
        raise blobc.ParseError(loc.filename, loc.lineno, msg)

    def apply_option(self, option):
        name = option.name
        self._curr_option = option
        method_name = 'configure_' + name
        if not hasattr(self, method_name):
            self.bad_option('"%s": no such generator option' % (name))
        try:
            method = getattr(self, method_name)
            method(option.location, *option.pos_params, **option.kw_params)
        except Exception as ex:
            self.bad_option('"%s": %s' % (name, ex))

    def generate_code(self, parse_tree, type_system, merge_imports=False):
        # find generator options from the parse tree
        mnemonic = type(self).MNEMONIC
        gen_options = [x for x in parse_tree
                         if isinstance(x, blobc.ParseTree.GeneratorConfig) \
                            and x.generator_name == mnemonic]

        for line in gen_options:
            for option in line.options:
                self.apply_option(option)

        self.start()

        imports = []
        prims, enums, structs = [], [], []

        # optionally drop import information
        if not merge_imports:
            for t in type_system.itertypes():
                loc = t.location
                if loc.is_import:
                    if loc.filename not in imports:
                        self.visit_import(loc.filename)
                        imports.append(loc.filename)
        else:
            # override import flag to pretend everything was local
            for t in type_system.itertypes():
                t.location.is_import = False
        
        for t in type_system.itertypes():
            if isinstance(t, blobc.Typesys.StructType):
                self.visit_struct(t)
            elif isinstance(t, blobc.Typesys.EnumType):
                self.visit_enum(t)
            elif isinstance(t, blobc.Typesys.PrimitiveType):
                self.visit_primitive(t)

        for name, value, location in type_system.iterconsts():
            self.visit_constant(name, value, location.is_import)

        self.finish()

    def start(self):
        pass

    def visit_import(self, fn):
        pass

    def visit_primitive(self, t):
        pass

    def visit_enum(self, t):
        pass

    def visit_struct(self, t):
        pass

    def visit_constant(self, c):
        pass

    def finish(self):
        pass
