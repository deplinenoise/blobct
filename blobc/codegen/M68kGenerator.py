import blobc
from . import GeneratorBase

class M68kGenerator(GeneratorBase):
    def __init__(self, fh, filename, aux_fh, output_fn):
        self.__filename = filename
        self.__targmach = blobc.TargetMachine(pointer_size=4, endian='big')
        self.__include_suffix = '.i'
        self.__user_literals = []
        self.fh = fh

    def configure_include_suffix(self, value):
        self.__include_suffix = str(value)

    def configure_emit(self, *text):
        self.__user_literals.extend(text)

    def start(self):
        self.fh.write('; Generated automatically by blobc.py from %s; do not edit.\n\n' %
                (self.__filename))

        if len(self.__user_literals) > 0:
            self.fh.write('\n; User literals (from "emit")\n')
            for l in self.__user_literals:
                self.fh.write(l)
                self.fh.write('\n')
            self.fh.write('\n\n')

    def print_equ(self, label, value):
        self.fh.write(label)
        self.fh.write(' ' * (50 - len(label)))
        self.fh.write('EQU % 8d\n' % (value))

    def visit_import(self, fn):
        self.fh.write('\t\tINCLUDE "%s%s"\n' % (fn, self.__include_suffix))

    def visit_primitive(self, t):
        pass

    def visit_enum(self, t):
        if t.loc.is_import:
            return 
        self.fh.write('\n; enum %s\n' % (t.name))
        for m in t.members:
            self.print_equ('%s_%s' % (t.name, m.name), m.value)

    def visit_constant(self, c):
        self.fh.write('\n; constant\n')
        self.print_equ(c.name, c.value)

    def visit_struct(self, t):
        if t.loc.is_import:
            return 
        sz, align = self.__targmach.size_align(t)
        self.fh.write('\n; struct: %s (size: %d, align: %d)\n' % (t.name, sz, align))
        for m in t.members:
            self.print_equ(t.name + '_' + m.mname, m.offset)
        self.print_equ(t.name + '_SIZE', sz)
        self.print_equ(t.name + '_ALIGN', align)

