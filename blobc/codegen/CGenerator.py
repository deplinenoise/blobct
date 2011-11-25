import blobc
import blobc.Typesys
import md5


class CGenerator(object):

    def __init__(self, fh, filename, aux_fh, output_fn):
        self.filename = filename
        self.output_fn = output_fn
        self.fh = fh
        self.aux_fh = aux_fh
        self.__structs = []
        self.__weights = {}
        m = md5.new()
        m.update(self.filename)
        self.guard = 'BLOBC_%s' % (m.hexdigest())
        self.fh.write('#ifndef %s\n#define %s\n' % (self.guard, self.guard))
        self.fh.write('\n#include <inttypes.h>\n\n')

        if self.aux_fh:
            # create a set of target machines to cover ptr size and alignment variations
            self.__tms = []
            for ptr_size in (4, 8):
                for ptr_align in (4, 8):
                    t = blobc.TargetMachine(pointer_size = ptr_size, pointer_align = ptr_align)
                    self.__tms.append(t)
                    
            if output_fn:
                self.aux_fh.write('#include "%s"\n\n' % (output_fn))

            self.aux_fh.write('#ifndef ALIGNOF\n')
            self.aux_fh.write('#if defined(__GNUC__) || defined(_MSC_VER)\n')
            self.aux_fh.write('#define ALIGNOF(x) __alignof(x)\n')
            self.aux_fh.write('#elif defined(AMIGA)\n')
            self.aux_fh.write('#define ALIGNOF(x) 4\n')
            self.aux_fh.write('#else\n')
            self.aux_fh.write('#error please define ALIGNOF for your compiler\n')
            self.aux_fh.write('#endif\n')
            self.aux_fh.write('#endif\n\n')

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
        self.__structs.append(t)

    def __weight_of(self, t):
        w = self.__weights.get(t)
        if w is None:
            w = 1
            for m in t.members:
                if isinstance(m.mtype, blobc.Typesys.StructType):
                    w += self.__weight_of(m.mtype)
            w *= 2
            self.__weights[t] = w
        return w

    def __compare_structs(self, a, b):
        return cmp(self.__weight_of(a), self.__weight_of(b))

    def finish(self):
        # Sort structs in complexity order so later structs can embed eariler structs.
        self.__structs.sort(self.__compare_structs)

        self.fh.write('\n')

        for t in self.__structs:
            self.fh.write('struct %s_TAG;\n' % (t.name))

        self.fh.write('\n')

        for t in self.__structs:
            self.fh.write('\ntypedef struct %s_TAG {\n' % (t.name))
            for m in t.members:
                self.fh.write('\t')
                self.fh.write(self.vardef(m.mtype, ' ' + m.mname))
                self.fh.write(';\n');
            self.fh.write('} %s;\n' % (t.name))

        self.fh.write('\n#endif\n')

        aux = self.aux_fh
        if not aux:
            return

        for t in self.__structs:
            sizes = [(tm, tm.size_align(t)) for tm in self.__tms]
            aux.write('typedef char __sizecheck_%s [\n' % (t.name))
            for tm, (size, align) in sizes:
                aux.write('(sizeof(void*) == %d && ALIGNOF(void*) == %d && \n' % (
                    tm.pointer_size(), tm.pointer_align()))
                aux.write(' sizeof(%s) == %d && ALIGNOF(%s) == %d) ? 1 :\n' %
                    (t.name, size, t.name, align))
            aux.write('-1];\n')

