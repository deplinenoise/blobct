import blobc.Typesys

class CGenerator(object):

    def __init__(self, filename):
        self.filename = filename
        self.__structs = []

    def set_output(self, fh):
        import md5
        self.fh = fh
        m = md5.new()
        m.update(self.filename)
        self.guard = 'BLOBC_%s' % (m.hexdigest())
        self.fh.write('#ifndef %s\n#define %s\n' % (self.guard, self.guard))
        self.fh.write('\n#include <inttypes.h>\n\n')

    def vardef(self, t, var):
        if isinstance(t, blobc.Typesys.StructType):
            return 'struct %s_TAG %s' % (t.name, var)
        elif isinstance(t, blobc.Typesys.ArrayType):
            return '%s[%d]' % (self.vardef(t.base_type, var), t.dim)
        elif isinstance(t, blobc.Typesys.PointerType):
            return '%s*%s' % (self.vardef(t.base_type, ''), var)
        elif isinstance(t, blobc.Typesys.PrimitiveType):
            return '%s%s' % (t.name, var)
        else:
            assert False

    def find_prim(self, t):
        if type(t) == blobc.Typesys.FloatingType:
            if t.size() == 4:
                return 'float'
            else:
                return 'double'
        elif type(t) == blobc.Typesys.SignedIntType:
            return 'int%d_t' % (t.size() * 8)
        elif type(t) == blobc.Typesys.UnsignedIntType:
            return 'uint%d_t' % (t.size() * 8)
        else:
            assert false

    def visit_primitive(self, t):
        self.fh.write('typedef %s %s;\n' % (self.find_prim(t), t.name))

    def visit_struct(self, t):
        self.fh.write('struct %s_TAG;\n' % (t.name))
        self.__structs.append(t)

    def finish(self):
        for t in self.__structs:
            self.fh.write('\ntypedef struct %s_TAG {\n' % (t.name))
            for m in t.members:
                self.fh.write('\t')
                self.fh.write(self.vardef(m.mtype, ' ' + m.mname))
                self.fh.write(';\n');
            self.fh.write('} %s;\n' % (t.name))

        self.fh.write('\n#endif\n')

