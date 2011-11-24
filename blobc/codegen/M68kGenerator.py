import blobc

class M68kGenerator(object):
    def __init__(self, filename):
        self.filename = filename
        self.targmach = blobc.TargetMachine(pointer_size=4, endian='big')

    def set_output(self, fh):
        self.fh = fh
        self.fh.write('; Generated automatically by blobc.py from %s; do not edit.\n' % (self.filename))

    def print_equ(self, label, value):
        self.fh.write(label)
        self.fh.write(' ' * (50 - len(label)))
        self.fh.write('EQU % 8d\n' % (value))

    def visit_primitive(self, t):
        pass

    def finish(self):
        pass

    def visit_struct(self, t):
        sz, align = self.targmach.size_align(t)
        self.fh.write('\n; struct: %s (size: %d, align: %d)\n' % (t.name, sz, align))
        for m in t.members:
            self.print_equ(t.name + '_' + m.mname, m.offset)
        self.print_equ(t.name + '_SIZE', sz)
        self.print_equ(t.name + '_ALIGN', align)

