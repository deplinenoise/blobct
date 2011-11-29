import blobc
from . import GeneratorBase

class M68kGenerator(GeneratorBase):
    MNEMONIC = 'm68k'

    def __init__(self, fh, filename, aux_fh, output_fn):
        self._filename = filename
        self._targmach = blobc.TargetMachine(pointer_size=4, endian='big')
        self._include_suffix = '.i'
        self._sizeof_suffix = '_SIZE'
        self._alignof_suffix = '_ALIGN'
        self._user_literals = []
        self._print_comments = True
        self._equ_label = 'EQU'
        self.fh = fh

    def configure_no_comments(self, loc):
        self._print_comments = False

    def configure_equ_label(self, loc, value):
        self._equ_label = str(value)

    def configure_include_suffix(self, loc, value):
        self._include_suffix = str(value)

    def configure_emit(self, loc, *text):
        if not loc.is_import:
            self._user_literals.extend(text)

    def configure_sizeof_suffix(self, loc, suffix):
        self._sizeof_suffix = str(suffix)

    def configure_alignof_suffix(self, loc, suffix):
        self._alignof_suffix = str(suffix)

    def start(self):
        if self._print_comments:
            self.fh.write('; Generated automatically by blobc.py from %s; do not edit.\n\n' %
                (self._filename))

        if len(self._user_literals) > 0:
            if self._print_comments:
                self.fh.write('\n; User literals (from "emit")\n')
            for l in self._user_literals:
                self.fh.write(l)
                self.fh.write('\n')
            self.fh.write('\n\n')

    def print_equ(self, label, value):
        self.fh.write(label)
        self.fh.write(' ' * (50 - len(label)))
        self.fh.write('%s % 8d\n' % (self._equ_label, value))

    def visit_import(self, fn):
        self.fh.write('\t\tINCLUDE "%s%s"\n' % (fn, self._include_suffix))

    def visit_primitive(self, t):
        pass

    def visit_enum(self, t):
        if t.location.is_import:
            return 

        if self._print_comments:
            self.fh.write('\n; enum %s\n' % (t.name))
        for m in t.members:
            self.print_equ('%s_%s' % (t.name, m.name), m.value)

    def visit_constant(self, name, value, is_import):
        if is_import:
            return
        if self._print_comments:
            self.fh.write('\n; constant\n')
        self.print_equ(name, value)

    def visit_struct(self, t):
        if t.location.is_import:
            return 
        sname = t.name
        sz, align = self._targmach.size_align(t)
        if self._print_comments:
            self.fh.write('\n; struct: %s (size: %d, align: %d)\n' % (t.name, sz, align))
        for m in t.members:
            name_opt = m.get_options('m68k_name')
            if len(name_opt) > 0:
                name = str(name_opt[0].pos_params[0])
            else:
                name = sname + '_' + m.mname
            self.print_equ(name, m.offset)
        self.print_equ(sname + self._sizeof_suffix, sz)
        self.print_equ(sname + self._alignof_suffix, align)

