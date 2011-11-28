import blobc

class GeneratorException(Exception):
    pass

class GeneratorBase(object):
    def __init__(self):
        self.__curr_option = None

    def bad_option(self, msg):
        o = self.__curr_option
        raise blobc.ParseError(o.loc.filename, o.loc.lineno, msg)

    def __apply_config(self, option):
        name = option.name
        self.__curr_option = option
        method_name = 'configure_' + name
        if not hasattr(self, method_name):
            self.bad_option('"%s": no such generator option' % (name))
        try:
            getattr(self, method_name)(option.loc, *option.pos_params(), **option.kw_params())
        except Exception as ex:
            self.bad_option('"%s": %s' % (name, ex))

    def apply_configuration(self, cfg_lines):
        for line in cfg_lines:
            for option in line.options:
                self.__apply_config(option)

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
