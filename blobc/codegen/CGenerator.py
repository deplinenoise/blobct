import blobc
import blobc.Typesys
from . import GeneratorBase, GeneratorException
import md5

class CGenerator(GeneratorBase):
    MNEMONIC = 'c'

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
        self._imports = []
        self._user_literals = []
        self._enums = []
        self._primitives = []
        self._structs = []
        self._constants = []
        self._struct_order = {}
        self._struct_order_list = [] # in nested dependency order, least complex first
        self._indent = '\t'
        self._obrace = ' {\n'
        self._struct_suffix = '_TAG'
        self._ctypename = {}
        self._print_separators = True
        self._print_guard = True
        self._print_inttypes = True
        m = md5.new()
        m.update(self.filename)
        self.guard = 'BLOBC_%s' % (m.hexdigest())

    def start(self):
        if self._print_guard:
            self.fh.write('#ifndef %s\n#define %s\n' % (self.guard, self.guard))

        if self._print_inttypes:
            self.fh.write('\n#include <inttypes.h>\n\n')

        if self.aux_fh:
            # create a set of target machines to cover ptr size and alignment variations
            self._tms = []
            for ptr_size in (4, 8):
                for ptr_align in (4, 8):
                    t = blobc.TargetMachine(pointer_size = ptr_size, pointer_align = ptr_align)
                    self._tms.append(t)
                    
            if self.output_fn is not None:
                self.aux_fh.write('#include "%s"\n\n' % (self.output_fn))

            self.aux_fh.write('#ifndef ALIGNOF\n')
            self.aux_fh.write('#if defined(__GNUC__) || defined(_MSC_VER)\n')
            self.aux_fh.write('#define ALIGNOF(x) __alignof(x)\n')
            self.aux_fh.write('#elif defined(AMIGA)\n')
            self.aux_fh.write('#define ALIGNOF(x) 4\n')
            self.aux_fh.write('#else\n')
            self.aux_fh.write('#error please define ALIGNOF for your compiler\n')
            self.aux_fh.write('#endif\n')
            self.aux_fh.write('#endif\n\n')

    def configure_emit(self, loc, *text):
        if not loc.is_import:
            self._user_literals.extend(text)

    def configure_struct_suffix(self, loc, suffix):
        self._struct_suffix = suffix

    def configure_indent_style(self, loc, style, size=4):
        if style == 'spaces':
            self._indent = size * ' '
        elif style == 'tabs':
            self._indent = '\t'
        else:
            self.bad_option("unsupported style '%s'; use one of 'spaces' or 'tabs'" %
                    (style))

    def configure_no_separators(self, loc):
        self._print_separators = False

    def configure_no_include_guard(self, loc):
        self._print_guard = False

    def configure_no_inttypes(self, loc):
        self._print_inttypes = False

    def configure_brace_style(self, loc, style):
        if style == 'k&r':
            self._obrace = ' {\n'
        elif style == 'newline':
            self._obrace = '\n{\n'
        else:
            self.bad_option(o, "unsupported indentation style '%s'" % (style))

    def ctypename(self, t):
        n = self._ctypename.get(t)
        if n is None:
            if t.name in CGenerator.c_reserved_words:
                n = "blobc_c_wrap_" + t.name
            else:
                n = t.name
            self._ctypename[t] = n
        return n

    def vardef(self, t, var):
        if isinstance(t, blobc.Typesys.StructType):
            return 'struct %s%s %s' % (self.ctypename(t), self._struct_suffix, var)
        elif isinstance(t, blobc.Typesys.ArrayType):
            return '%s[%d]' % (self.vardef(t.base_type, var), t.dim)
        elif isinstance(t, blobc.Typesys.PointerType):
            return '%s*%s' % (self.vardef(t.base_type, ''), var)
        elif isinstance(t, blobc.Typesys.PrimitiveType):
            return '%s%s' % (self.ctypename(t), var)
        elif t is blobc.Typesys.VoidType.instance:
            return 'void%s' % (var)
        elif isinstance(t, blobc.Typesys.EnumType):
            return '%s%s' % (t.name, var)
        else:
            raise GeneratorException("type %s not supported" % (str(t)))

    def find_prim(self, t):
        if type(t) == blobc.Typesys.FloatingType:
            if t.size == 4:
                return 'float'
            else:
                return 'double'
        elif type(t) == blobc.Typesys.SignedIntType:
            return 'int%d_t' % (t.size * 8)
        elif type(t) == blobc.Typesys.UnsignedIntType:
            return 'uint%d_t' % (t.size * 8)
        elif type(t) == blobc.Typesys.CharacterType:
            size = t.size
            if size == 1:
                return 'char'
            elif size == 2:
                return 'BLOBC_CHAR2_T'
            elif size == 4:
                return 'BLOBC_CHAR4_T'
        else:
            assert false

    def visit_import(self, fn):
        self._imports.append(fn)

    def visit_primitive(self, t):
        self._primitives.append(t)

    def visit_enum(self, t):
        if not t.location.is_import:
            self._enums.append(t)

    def visit_struct(self, t):
        if not t.location.is_import:
            self._structs.append(t)

    def _visit_struct(self, t):
        if self._struct_order.has_key(t):
            return
        for m in t.members:
            if isinstance(m.mtype, blobc.Typesys.StructType):
                self._visit_struct(m.mtype)
        if not self._struct_order.has_key(t):
            self._struct_order[t] = True
            self._struct_order_list.append(t)

    def _compare_structs(self, a, b):
        return cmp(self._weight_of(a), self._weight_of(b))

    def _separator(self, tag):
        if self._print_separators:
            l = len(tag)
            left = 70 / 2 - l / 2
            right = 70 - l - left
            self.fh.write('\n/*%s %s %s*/\n\n' % ('-' * left, tag, '-' * right))

    def _emit_imports(self):
        if len(self._imports) == 0:
            return
        self._separator('imports')
        for filename in self._imports:
            self.fh.write('#include "%s.h"\n' % (filename))

    def _emit_primitives(self):
        if len(self._primitives) == 0:
            return

        self._separator('primitives')

        for t in self._primitives:
            if not t.is_external:
                prim_name = self.find_prim(t)
                if prim_name != t.name:
                    if not t.location.is_import:
                        self.fh.write('typedef %s %s;\n' % (prim_name, self.ctypename(t)))
                    else:
                        self.ctypename(t)
                else:
                    # map e.g. char -> char
                    self._ctypename[t] = prim_name
            else:
                self._ctypename[t] = t.name

    def _emit_constants(self):
        if len(self._constants) == 0:
            return

        self._separator('constants')

        self.fh.write('enum%s' % (self._obrace))
        for x in xrange(0, len(self._constants)):
            name, value = self._constants[x]
            self.fh.write('%s%s = %d%s\n' % 
                    (self._indent, name, value,
                     ', ' if (x + 1) < len(self._constants) else ''))
        self.fh.write('};\n')

    def _emit_predecl(self):
        if len(self._structs) == 0:
            return
        self._separator('predeclarations')
        for t in self._struct_order_list:
            self.fh.write('struct %s%s;\n' % (t.name, self._struct_suffix))

    def _emit_user_literals(self):
        if len(self._structs) == 0:
            return
        self._separator('user literals')
        for t in self._user_literals:
            self.fh.write(t)
            self.fh.write('\n')

    def _emit_enums(self):
        if len(self._enums) == 0:
            return

        self._separator('enums')

        for t in self._enums:
            self.fh.write('typedef enum%s' % (self._obrace))
            mcount = len(t.members)
            for x in xrange(0, mcount):
                m = t.members[x]
                self.fh.write('%s%s_%s = %d' % (self._indent, t.name, m.name, m.value))
                if x + 1 < mcount:
                    self.fh.write(',');
                self.fh.write('\n')
            self.fh.write('} %s;\n' % (t.name))

    def _emit_structs(self):
        if len(self._structs) == 0:
            return

        self._separator('structs')

        for t in self._struct_order_list:
            if t.location.is_import:
                continue
            self.fh.write('\ntypedef struct %s%s%s' % (t.name, self._struct_suffix, self._obrace))
            for m in t.members:
                self.fh.write(self._indent)
                ct = m.get_options('c_decl')
                if len(ct) == 0:
                    self.fh.write(self.vardef(m.mtype, ' ' + m.mname))
                else:
                    self.fh.write(ct[0].pos_params[0])
                self.fh.write(';\n');
            self.fh.write('} %s;\n' % (t.name))

    def finish(self):
        # Sort structs in complexity order so later structs can embed eariler structs.
        for t in self._structs:
            self._visit_struct(t)

        self.fh.write('\n')

        self._emit_imports()
        self._emit_primitives()
        self._emit_constants()
        self._emit_predecl()
        self._emit_user_literals()
        self._emit_enums()
        self._emit_structs()

        if self._print_guard:
            self.fh.write('\n#endif\n')

        aux = self.aux_fh
        if not aux:
            return

        for t in self._structs:
            if t.location.is_import:
                continue
            name = t.name
            sizes = [(tm, tm.size_align(t)) for tm in self._tms]
            aux.write('typedef char sizecheck_%s_ [\n' % (name))
            for tm, (size, align) in sizes:
                aux.write('(sizeof(void*) == %d && ALIGNOF(void*) == %d && \n' % (
                    tm.pointer_size, tm.pointer_align))
                aux.write(' sizeof(%s) == %d && ALIGNOF(%s) == %d) ? 1 :\n' %
                    (name, size, name, align))
            aux.write('-1];\n')

    def visit_constant(self, name, value, is_import):
        if not is_import:
            self._constants.append((name, value))
