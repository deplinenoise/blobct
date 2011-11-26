import blobc
import blobc.Typesys
from . import GeneratorBase
import md5


class CGenerator(GeneratorBase):

    c_reserved_words = '''
    auto break case char const continue default do double else
    enum extern float for goto if int long register return short
    signed sizeof static struct switch typedef union unsigned void
    volatile while
    '''.split()

    def __init__(self, fh, filename, aux_fh, output_fn):
        GeneratorBase.__init__(self)
        self.filename = filename
        self.output_fn = output_fn
        self.fh = fh
        self.aux_fh = aux_fh
        self.__imports = []
        self.__enums = []
        self.__primitives = []
        self.__structs = []
        self.__weights = {}
        self.__indent = '\t'
        self.__obrace = ' {\n'
        self.__ctypename = {}
        m = md5.new()
        m.update(self.filename)
        self.guard = 'BLOBC_%s' % (m.hexdigest())

    def start(self):
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

    def configure_indent_style(self, style, size=4):
        if style == 'spaces':
            self.__indent = size * ' '
        elif style == 'tabs':
            self.__indent = '\t'
        else:
            self.bad_option("unsupported style '%s'; use one of 'spaces' or 'tabs'" %
                    (style))

    def configure_brace_style(self, style):
        if style == 'k&r':
            self.__obrace = ' {\n'
        elif style == 'newline':
            self.__obrace = '\n{\n'
        else:
            self.bad_option(o, "unsupported indentation style '%s'" % (style))

    def ctypename(self, t):
        n = self.__ctypename.get(t)
        if n is None:
            if t.name in CGenerator.c_reserved_words:
                n = "blobc_c_wrap_" + t.name
            else:
                n = t.name
            self.__ctypename[t] = n
        return n

    def vardef(self, t, var):
        if isinstance(t, blobc.Typesys.StructType):
            return 'struct %s_TAG %s' % (self.ctypename(t), var)
        elif isinstance(t, blobc.Typesys.ArrayType):
            return '%s[%d]' % (self.vardef(t.base_type, var), t.dim)
        elif isinstance(t, blobc.Typesys.PointerType):
            return '%s*%s' % (self.vardef(t.base_type, ''), var)
        elif isinstance(t, blobc.Typesys.PrimitiveType):
            return '%s%s' % (self.ctypename(t), var)
        elif t is blobc.Typesys.VoidType.instance:
            return 'void%s' % (var)
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
        elif type(t) == blobc.Typesys.CharacterType:
            size = t.size()
            if size == 1:
                return 'char'
            elif size == 2:
                return 'BLOBC_CHAR2_T'
            elif size == 4:
                return 'BLOBC_CHAR4_T'
        else:
            assert false

    def visit_import(self, fn):
        self.__imports.append(fn)

    def visit_primitive(self, t):
        if not t.loc.is_import:
            self.__primitives.append(t)

    def visit_enum(self, t):
        if not t.loc.is_import:
            self.__enums.append(t)

    def visit_struct(self, t):
        if not t.loc.is_import:
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

    def __separator(self, tag):
        l = len(tag)
        left = 70 / 2 - l / 2
        right = 70 - l - left
        self.fh.write('\n/*%s %s %s*/\n\n' % ('-' * left, tag, '-' * right))

    def finish(self):
        # Sort structs in complexity order so later structs can embed eariler structs.
        self.__structs.sort(self.__compare_structs)

        self.fh.write('\n')

        if len(self.__imports) > 0:
            self.__separator('imports')

        for filename in self.__imports:
            self.fh.write('#include "%s.h"\n' % (filename))

        if len(self.__primitives) > 0:
            self.__separator('primitives')

        for t in self.__primitives:
            prim_name = self.find_prim(t)
            if prim_name != t.name:
                self.fh.write('typedef %s %s;\n' % (prim_name, self.ctypename(t)))
            else:
                # map e.g. char -> char
                self.__ctypename[t] = prim_name

        if len(self.__structs) > 0:
            self.__separator('predeclarations')

        for t in self.__structs:
            self.fh.write('struct %s_TAG;\n' % (t.name))

        if len(self.__enums) > 0:
            self.__separator('enums')

        for t in self.__enums:
            self.fh.write('typedef enum%s' % (self.__obrace))
            first = True
            for x in xrange(0, len(t.members)):
                m = t.members[x]
                self.fh.write('%s%s_%s = %d' % (self.__indent, t.name, m.name, m.value))
                if x < len(t.members) - 1:
                    self.fh.write(',');
                self.fh.write('\n')
            self.fh.write('} %s;\n' % (t.name))

        if len(self.__structs) > 0:
            self.__separator('structs')

        for t in self.__structs:
            self.fh.write('\ntypedef struct %s_TAG%s' % (t.name, self.__obrace))
            for m in t.members:
                self.fh.write(self.__indent)
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

