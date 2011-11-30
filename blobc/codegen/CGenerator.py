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
        self._enable_reflection = False
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
            self.aux_fh.write('#define ALIGNOF(x) (sizeof(x) >= 4 ? 4 : sizeof(x))\n')
            self.aux_fh.write('#else\n')
            self.aux_fh.write('#error please define ALIGNOF for your compiler\n')
            self.aux_fh.write('#endif\n')
            self.aux_fh.write('#endif\n\n')

    def configure_enable_reflection(self, loc):
        self._enable_reflection = True

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

    def refnode_name(self, t):
        if isinstance(t, blobc.Typesys.StructType):
            return self.ctypename(t)
        elif isinstance(t, blobc.Typesys.ArrayType):
            return '%s_array%d' % (self.refnode_name(t.base_type), t.dim)
        elif isinstance(t, blobc.Typesys.PointerType):
            return '%s_ptr' % (self.refnode_name(t.base_type))
        elif isinstance(t, blobc.Typesys.PrimitiveType):
            return '%s' % (self.ctypename(t))
        elif t is blobc.Typesys.VoidType.instance:
            return 'void'
        elif isinstance(t, blobc.Typesys.EnumType):
            return t.name
        else:
            raise GeneratorException("type %s not supported" % (str(t)))

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
            ptype = m.mtype
            # drop all array types to get to Foo in e.g. Foo[2, 3]
            # note that this applies only to by-value arrays
            while isinstance(ptype, blobc.Typesys.ArrayType):
                ptype = ptype.base_type
            if isinstance(ptype, blobc.Typesys.StructType):
                self._visit_struct(ptype)
        if not self._struct_order.has_key(t):
            self._struct_order[t] = True
            self._struct_order_list.append(t)

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
            if t.is_external:
                self._ctypename[t] = t.name
                continue

            prim_name = self.find_prim(t)
            if prim_name != t.name:
                if not t.location.is_import:
                    self.fh.write('typedef %s %s;\n' % (prim_name, self.ctypename(t)))
                else:
                    self.ctypename(t)
            else:
                # map e.g. char -> char
                self._ctypename[t] = prim_name
            
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

    _primmap = {
        blobc.Typesys.UnsignedIntType: 'BCT_UNSIGNED',
        blobc.Typesys.SignedIntType: 'BCT_SIGNED',
        blobc.Typesys.FloatingType: 'BCT_FLOAT',
        blobc.Typesys.CharacterType: 'BCT_CHAR',
    }
    
    def _indent_aux(self, str):
        self.aux_fh.write(self._indent)
        self.aux_fh.write(str)

    def _emit_ref_primitive(self, t, pclass):
        self._emit_ref_data(t, 'BCT_PRIMITIVE', pclass=pclass, size=t.size, align=t.size)

    def _emit_ref_unsigned(self, t):
        self._emit_ref_primitive(t, 'BCT_UNSIGNED')

    def _emit_ref_signed(self, t):
        self._emit_ref_primitive(t, 'BCT_SIGNED')

    def _emit_ref_char(self, t):
        self._emit_ref_primitive(t, 'BCT_CHAR')

    def _emit_ref_floating(self, t):
        self._emit_ref_primitive(t, 'BCT_FLOAT')

    def _emit_ref_struct(self, t):
        aux = self.aux_fh
        aux.write('static const struct bct_member bct_members_%s_[] =%s' % (t.name, self._obrace))
        for x in xrange(0, len(t.members)):
            m = t.members[x]
            comma = ',' if x + 1 < len(t.members) else ''
            self._indent_aux('{ "%s", offsetof(%s, %s), &bct_typenode_%s_ }%s\n' % \
                    (m.mname, t.name, m.mname, self.refnode_name(m.mtype), comma))
        aux.write('};\n\n')
        self._emit_ref_data(t, 'BCT_STRUCT')

    def _emit_ref_pointer(self, t):
        self._emit_ref_data(t, 'BCT_POINTER')

    def _emit_ref_cstring(self, t):
        self._emit_ref_data(t, 'BCT_CSTRING')

    def _emit_ref_array(self, t):
        self._emit_ref_data(t, 'BCT_ARRAY')

    def _emit_ref_data(self, t, metatype, pclass='BCT_NONE', size=0, align=0):
        c_name = self.vardef(t, '')
        n = self.refnode_name(t)
        i = self._indent_aux
        if metatype != 'BCT_STRUCT' and metatype != 'BCT_PRIMITIVE':
            self.aux_fh.write('static ');
        self.aux_fh.write('const struct bct_typenode bct_typenode_%s_ =%s' % (n, self._obrace))
        i('%s,\n' % (metatype))
        i('%s,\n' % (pclass))
        i('%d,\n' % (size))
        i('%d,\n' % (align))
        i('sizeof(%s),\n' % (c_name))
        i('ALIGNOF(%s),\n' % (c_name))
        if metatype == 'BCT_STRUCT':
            i('%d,\n' % (len(t.members)))
            i('&bct_members_%s_,\n' % (n))
        elif metatype == 'BCT_ARRAY':
            i('%d,\n' % (t.dim))
            i('&bct_typenode_%s_,\n' % (self.refnode_name(t.base_type)))
        elif metatype == 'BCT_POINTER':
            i('0,\n')
            i('&bct_typenode_%s_,\n' % (self.refnode_name(t.base_type)))
        else:
            i('0,\n')
            i('NULL,\n')
        i('"%s",\n' % (c_name))
        self.aux_fh.write('};\n')

    _refdispatch = {
        blobc.Typesys.UnsignedIntType: _emit_ref_unsigned,
        blobc.Typesys.SignedIntType: _emit_ref_signed,
        blobc.Typesys.FloatingType: _emit_ref_floating,
        blobc.Typesys.CharacterType: _emit_ref_char,
        blobc.Typesys.PointerType: _emit_ref_pointer,
        blobc.Typesys.CStringType: _emit_ref_cstring,
        blobc.Typesys.ArrayType: _emit_ref_array,
        blobc.Typesys.StructType: _emit_ref_struct,
    }

    def _emit_reflection_data(self, t):
        func = CGenerator._refdispatch[type(t)]
        func(self, t)

    def _visit_type_for_reflection(self, t, typehash, typelist):
        if t.location.is_import:
            return
        if typehash.has_key(t):
            return
        typehash[t] = True

        if isinstance(t, blobc.Typesys.StructType):
            for m in t.members:
                self._visit_type_for_reflection(m.mtype, typehash, typelist)
            typelist.append(t)
        elif isinstance(t, blobc.Typesys.ArrayType):
            self._visit_type_for_reflection(t.base_type, typehash, typelist)
            typelist.append(t)
        elif isinstance(t, blobc.Typesys.PointerType):
            self._visit_type_for_reflection(t.base_type, typehash, typelist)
            typelist.append(t)
        elif isinstance(t, blobc.Typesys.PrimitiveType):
            typelist.append(t)
        elif t is blobc.Typesys.VoidType.instance:
            typelist.append(t)
        elif isinstance(t, blobc.Typesys.EnumType):
            typelist.append(t)
        else:
            assert False

    def _type_dependency_order(self):
        typehash = {}
        typelist = []
        for t in self._primitives:
            self._visit_type_for_reflection(t, typehash, typelist)
        for t in self._structs:
            self._visit_type_for_reflection(t, typehash, typelist)
        return typelist

    def _emit_reflection(self):
        self._separator('reflection info')
        fh = self.fh
        aux = self.aux_fh
        fh.write('struct bct_typenode;\n')
        fh.write('struct bct_member;\n')
        if aux:
            aux.write('#include "blobct.h"\n')

        primmap = CGenerator._primmap

        for t in self._type_dependency_order():
            if hasattr(t, 'name'):
                n = t.name
                fh.write('extern const struct bct_typenode bct_typenode_%s_;\n' % (n))
            if not aux:
                continue
            self._emit_reflection_data(t)


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

        if self._enable_reflection:
            self._emit_reflection()

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
