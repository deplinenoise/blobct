import blobc
import re
from ..Typesys import *
from . import GeneratorBase, GeneratorException

RE_LOWERCASE_UNDERSCORE = re.compile(r'^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$')
RE_UNDERSCORE_CHAR = re.compile(r'_([a-z0-9])')

class AlignRank:
    def __init__(self, name, value):
        self._name = name
        self._value = value

    def name(self):
        return self._name

    def value(self):
        return self._value

AlignRank.ByteAlign = AlignRank("1", 1)
AlignRank.CharAlign = AlignRank("b.CharAlignment", 2)
AlignRank.ShortAlign = AlignRank("b.ShortAlignment", 3)
AlignRank.IntAlign = AlignRank("b.IntAlignment", 4)
AlignRank.FloatAlign = AlignRank("b.FloatAlignment", 5)
AlignRank.PointerAlign = AlignRank("b.PointerAlignment", 6)

def csharpify_name(name):
    if RE_LOWERCASE_UNDERSCORE.match(name):
        def rep(m):
            return m.group(1)[0].upper() + m.group(1)[1:]
        return name[0].upper() + re.sub(RE_UNDERSCORE_CHAR, rep, name[1:])
    else:
        return name

class CSharpGenerator(GeneratorBase):
    MNEMONIC = 'csharp'

    def __init__(self, fh, filename, aux_fh, output_fn):
        self.fh = fh
        self._filename = filename
        self._user_literals = []
        self._print_comments = True
        self._namespace = None
        self._enums = []
        self._constants = []
        self._structs = []

    def configure_namespace(self, loc, value):
        self._namespace = value

    def configure_no_comments(self, loc):
        self._print_comments = False

    def configure_emit(self, loc, *text):
        if not loc.is_import:
            self._user_literals.extend(text)

    def _comment(self, s):
        if self._print_comments:
            self.fh.write(s)

    def start(self):
        pass

    def visit_import(self, fn):
        # C# handles imports automatically when compiling files together
        pass

    def visit_primitive(self, t):
        pass

    def visit_enum(self, t):
        if t.location.is_import:
            return 
        self._enums.append(t)

    def visit_constant(self, name, value, is_import):
        if is_import:
            return
        self._constants.append((name, value))

    def visit_struct(self, t):
        if t.location.is_import:
            return 
        self._structs.append(t)

    def _generate_enums(self):
        for t in self._enums:
            self.fh.write('public enum %s\n{\n' % (csharpify_name(t.name)))

            for m in t.members:
                self.fh.write('\t%s = %d,\n' % (csharpify_name(m.name), m.value))

            self.fh.write('}\n')

    def _member_name(self, m):
        if m.has_option('csharp_name'):
            return str(m.get_options('csharp_name')[0].pos_params[0])
        else:
            return csharpify_name(m.mname)

    def _primitive_type_name(self, t):
        if isinstance(t, SignedIntType):
            if t.size == 4:
                return 'int'
            elif t.size == 2:
                return 'short'
            elif t.size == 1:
                return 'sbyte'
        if isinstance(t, UnsignedIntType):
            if t.size == 4:
                return 'uint'
            elif t.size == 2:
                return 'ushort'
            elif t.size == 1:
                return 'byte'
        if isinstance(t, FloatingType):
            if t.size == 4:
                return 'float'
        if isinstance(t, CharacterType):
            if t.size == 1:
                return 'char'
        raise GeneratorException("primitive type %s not supported" % (str(t)))

    def _csharp_type_impl(self, t):
        if isinstance(t, StructType):
            return csharpify_name(t.name)
        elif isinstance(t, EnumType):
            return csharpify_name(t.name)
        elif isinstance(t, PrimitiveType):
            return self._primitive_type_name(t)
        elif isinstance(t, ArrayType):
            return 'BlobCt.BlobArray<%s>' % (self._csharp_type_impl(t.base_type))
        elif isinstance(t, CStringType):
            return 'string'
        elif isinstance(t, PointerType):
            if isinstance(t.base_type, VoidType):
                return 'BlobCt.GenericPointer'
            else:
                return 'BlobCt.Pointer<%s>' % (self._csharp_type_impl(t.base_type))
        elif isinstance(t, VoidType):
            raise GeneratorException("void fields are not upported")
        else:
            raise GeneratorException("type %s not supported" % (str(t)))

    def _csharp_type(self, m, t):
        if m.has_option('csharp_array'):
            if isinstance(t, PointerType):
                return 'BlobCt.BlobArray<%s>' % (self._csharp_type_impl(t.base_type))
            else:
                raise GeneratorException("csharp_array can only be used on pointer types")
        else:
            return self._csharp_type_impl(t)

    def _csharp_writefunc(self, t):
        if isinstance(t, StructType):
            return 'Write'
        elif isinstance(t, PrimitiveType):
            if isinstance(t, SignedIntType):
                if t.size == 4:
                    return 'WriteInt'
                elif t.size == 2:
                    return 'WriteShort'
                elif t.size == 1:
                    return 'WriteSbyte'
            elif isinstance(t, UnsignedIntType):
                if t.size == 4:
                    return 'WriteUint'
                elif t.size == 2:
                    return 'WriteUshort'
                elif t.size == 1:
                    return 'WriteByte'
            elif isinstance(t, FloatingType):
                if t.size == 4:
                    return 'WriteFloat'
            elif isinstance(t, CharacterType):
                if t.size == 1:
                    return 'WriteChar'
            raise GeneratorException("type %s not supported" % (str(t)))
        elif isinstance(t, ArrayType):
            return 'Write'
        elif isinstance(t, CStringType):
            return 'WriteStringPointer'
        elif isinstance(t, PointerType):
            return 'WritePointer'
        else:
            raise GeneratorException("type %s not supported" % (str(t)))

    def _csharp_align_expr(self, t):
        if isinstance(t, StructType):
            return max((self._csharp_align_expr(m.mtype) for m in t.members), key=AlignRank.value)
        elif isinstance(t, PrimitiveType):
            if isinstance(t, SignedIntType) or isinstance(t, UnsignedIntType):
                if t.size == 4:
                    return AlignRank.IntAlign
                elif t.size == 2:
                    return AlignRank.ShortAlign
                elif t.size == 1:
                    return AlignRank.ByteAlign
            elif isinstance(t, FloatingType):
                if t.size == 4:
                    return AlignRank.FloatAlign
            elif isinstance(t, CharacterType):
                if t.size == 1:
                    return AlignRank.CharAlign
        elif isinstance(t, ArrayType):
            return self._csharp_align_expr(t.base_type)
        elif isinstance(t, PointerType):
            return AlignRank.PointerAlign
        raise GeneratorException("type %s not supported" % (str(t)))

    def _generate_constants(self):
        if len(self._constants) == 0:
            return
        fh = self.fh
        fh.write('public partial class Constants\n{\n')
        for t in self._constants:
            fh.write('\tconst int %s = %d;\n' % (csharpify_name(t[0]), t[1]))
        fh.write('}\n\n')

    def _generate_initializers(self, ctor_list, lvalue, m, mtype, indent=''):
        if isinstance(mtype, PointerType) and len(m.get_options('csharp_array')) > 0:
            ctor_list.append('%s%s = new %s();' % (indent, lvalue, self._csharp_type(m, mtype)))
        elif isinstance(mtype, ArrayType):
            ctor_list.append('%s%s = new %s(%d);' % (indent, lvalue, self._csharp_type(m, mtype), mtype.dim))
            base = mtype.base_type
            if isinstance(base, ArrayType) or isinstance(base, StructType):
                ctor_list.append('%sfor (int x = 0; x < %d; ++x)' % (indent, mtype.dim))
                ctor_list.append('%s{' % (indent))
                self._generate_initializers(ctor_list, lvalue + '[x]', m, mtype.base_type, indent = indent + '\t')
                ctor_list.append('%s}' % (indent))
        elif isinstance(mtype, StructType):
            ctor_list.append('%s%s = new %s();' % (indent, lvalue, self._csharp_type(m, mtype)))

    def _generate_structs(self):
        fh = self.fh
        for t in self._structs:
            sname = csharpify_name(t.name)
            ctor = []
            writer = []
            fh.write('public class %s : BlobCt.IPointerTarget<%s>\n{\n' % (sname, sname))
            for m in t.members:
                mname = self._member_name(m)
                mtypename = self._csharp_type(m, m.mtype)
                field_name = mname + '_'

                if not m.has_option('csharp_array_count'):
                    fh.write('\tprivate %s %s;\n' % (mtypename, field_name))

                if isinstance(m.mtype, ArrayType) or m.has_option('csharp_array'):
                    fh.write('\tpublic %s %s { get { return %s; } }\n\n' % (mtypename, mname, field_name))
                elif isinstance(m.mtype, StructType):
                    fh.write('\tpublic %s %s {\n' % (mtypename, mname))
                    fh.write('\t\tget { return %s; }\n' % (field_name))
                    fh.write('\t\tset {\n')
                    fh.write('\t\t\tif (value == null) throw new BlobCt.BlobException("%s");\n' % (mname))
                    fh.write('\t\t\t%s = value;\n' % (field_name))
                    fh.write('\t\t}\n\t}\n')
                elif m.has_option('csharp_array_count'):
                    targ_field = m.get_options('csharp_array_count')[0].pos_params[0]
                    fh.write('\tpublic %s %s { get { return (%s) %s.Count; } }\n\n' %
                            (mtypename, mname, mtypename, csharpify_name(targ_field)))
                else:
                    fh.write('\tpublic %s %s { get { return %s; } set { %s = value; } }\n\n' %
                            (mtypename, mname, field_name, field_name))

                self._generate_initializers(ctor, field_name, m, m.mtype)

                write_func = self._csharp_writefunc(m.mtype)

                writer.append('b.%s(%s)' % (write_func, mname))

            # constructor
            fh.write('\n\tpublic %s()\n\t{\n' % (sname))
            for line in ctor:
                fh.write('\t\t%s\n' % (line))
            fh.write('\t}\n\n')

            # implementing IPointerTarget
            fh.write('\t%s BlobCt.IPointerTarget<%s>.this [int index]\n\t{\n' % (sname, sname))
            for kw in ('get', 'set'):
                fh.write('\t\t%s { throw new BlobCt.BlobException("cannot index value"); }\n' % (kw))
            fh.write('\t}\n\n')

            fh.write('\tvoid BlobCt.IGenericPointerTarget.ValidateOffset(int offset)\n\t{\n')
            fh.write('\t}\n\n')

            fh.write('\tvoid BlobCt.IGenericPointerTarget.Align(BlobCt.BlobSerializer b)\n\t{\n')
            fh.write('\t\tb.Align(%s);\n' % (self._csharp_align_expr(t).name()))
            fh.write('\t}\n\n')

            fh.write('\tvoid BlobCt.IGenericPointerTarget.WriteValue(BlobCt.BlobSerializer b)\n\t{\n')
            for line in writer:
                fh.write('\t\t%s;\n' % (line))
            fh.write('\t}\n\n')

            fh.write('}\n\n')

    def finish(self):
        fh = self.fh
        self._comment('// Generated automatically by blobc.py from %s; do not edit.\n\n' %
                (self._filename))

        fh.write('using System;\n\n')

        if self._namespace:
            fh.write('namespace %s\n{\n\n' % (self._namespace))

        if len(self._user_literals) > 0:
            self._comment('\n// User literals (from "emit")\n')
            for l in self._user_literals:
                fh.write(l)
                fh.write('\n')
            fh.write('\n\n')
        self._generate_enums()
        self._generate_constants()
        self._generate_structs()

        if self._namespace:
            fh.write('}\n')
