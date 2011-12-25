
import types
import struct

from ParseTree import *

class PythonMappingException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class TypeSystemException(Exception):
    def __init__(self, loc, msg):
        if loc is not None:
            Exception.__init__(self, "%s(%d): %s" % (loc.filename, loc.lineno, msg))
        else:
            Exception.__init__(self, msg)

class BaseType(object):
    def __init__(self):
        self._ptr_type = None
        self._cstr_type = None
        self._array_types = {}

    def pointer_type(self, loc):
        if self._ptr_type is None:
            self._ptr_type = PointerType(self, loc)
        return self._ptr_type

    def cstring_type(self, loc):
        if self._cstr_type is None:
            self._cstr_type = CStringType(self, loc)
        return self._cstr_type

    def array_type(self, dim, loc = None):
        r = self._array_types.get(dim, None)
        if not r:
            r = ArrayType(self, dim, loc)
            self._array_types[dim] = r
        return r

class Array(object):
    def __init__(self, ntype, items):
        self.items = [ntype.create_value(x) for x in items]
        self.item_type = ntype

    def __repr__(self): # pragma: no cover
        return "<%s>%s" % (str(self.item_type), repr(self.items))

    def __str__(self):
        return str(self.items)

class String(Array):
    def __init__(self, char_type, text):
        Array.__init__(self, char_type, text + '\0')

    def __repr__(self): # pragma: no cover
        return "'%s'" % (self.items[:-1])

    def __str__(self):
        return self.items[:-1]

class VoidType(BaseType):
    def __init__(self):
        BaseType.__init__(self)
        self.location = SourceLocation('none', 0, True)

    def __str__(self):
        return '<any>'

    def compute_size(self, targmach):
        raise TypeSystemException(None, 'void type cannot be instantiated')

    def default_value(self):
        raise TypeSystemException(None, 'void type cannot be instantiated')

    def create_value(self, v):
        raise TypeSystemException(None, 'void type cannot be instantiated')

    def serialize(self, serializer, v):
        raise TypeSystemException(None, 'void type cannot be instantiated')

VoidType.instance = VoidType()

class PointerType(BaseType):
    def __init__(self, base, loc):
        BaseType.__init__(self)
        self.base_type = base
        self.location = loc
        self._str = str(self.base_type) + '*'

    def compute_size(self, targmach):
        return (targmach.pointer_size, targmach.pointer_align)

    def default_value(self):
        return None

    def _can_point_to(self, target_type):
        return target_type is self.base_type or \
                self.base_type is VoidType.instance or \
                (isinstance(self.base_type, StructType) and target_type.is_superset_of(self.base_type))

    def create_value(self, v):
        # pointers allow flexible data

        # None -- null pointers are ok
        if v is None:
            return

        # Can also point to a list of data
        elif isinstance(v, list):
            return Array(self.base_type, v)

        # Or to an individual array element
        elif isinstance(v, tuple):
            if not isinstance(v[0], Array):
                raise TypeSystemException(None, '%s cannot point to %s' % (str(self), str(v)))

            if self._can_point_to(v[0].item_type):
                return v
            else:
                raise TypeSystemException(None, '%s cannot point to %s' % (str(self), str(v)))

        # Or to an individual value, currently must be struct
        else:
            if self._can_point_to(type(v).srctype):
                return (v, 0)
            else:
                raise TypeSystemException(None, '%s cannot point to %s' % (str(self), str(v)))

    def __repr__(self): # pragma: no cover
        return self._str

    def __str__(self):
        return self._str

    def serialize(self, serializer, v):
        if v is None:
            serializer.write_null_ptr()
            return

        loc = None

        if isinstance(v, Array):
            loc = serializer.divert()
            if len(v.items) > 0:
                v.item_type.array_type(len(v.items)).serialize(serializer, v)
            serializer.resume()
            serializer.write_ptr(loc)

        elif isinstance(v, tuple):
            target = v[0]
            index = v[1]
            loc = serializer.location_of(target)
            if isinstance(target, Array):
                index *= serializer.targmach.sizeof(target.item_type)
            elif index != 0:
                raise TypeSystemException(None, 'offset pointer requires array target')

            serializer.write_ptr(loc, index)

        else:
            loc = serializer.divert()
            target_type = type(v).target_type
            self.target_type.serialize(serializer, v)
            serializer.resume()
            serializer.write_ptr(loc)

class CStringType(PointerType):
    def __init__(self, base, loc):
        PointerType.__init__(self, base, loc)

    def create_value(self, v):
        if isinstance(v, str):
            return String(self.base_type, v)
        else:
            return PointerType.create_value(self, v)

class ArrayType(BaseType):
    def __init__(self, base, dim, loc):
        BaseType.__init__(self)
        self.base_type = base
        self.dim = dim
        self.location = loc
        self._str = '%s[%d]' % (str(self.base_type), dim)

    def compute_size(self, targmach):
        size, align = self.base_type.compute_size(targmach)
        size *= self.dim
        return (size, align)

    def default_value(self):
        return [self.base_type.default_value for x in xrange(0, self.dim)]

    def create_value(self, v):
        if len(v) != self.dim:
            raise PythonMappingException("expected list of length %d; got list of %d items" % (self.dim, len(v)))
        return Array(self.base_type, v)

    def serialize(self, serializer, datum):
        serializer.align(serializer.targmach.alignof(self.base_type))
        serializer.update_location(datum)
        assert isinstance(datum, Array)
        for item in datum.items:
            self.base_type.serialize(serializer, item)

    def __repr__(self): # pragma: no cover
        return self._str

    def __str__(self):
        return self._str

class EnumMember(object):
    def __init__(self, name, value, loc):
        self.name, self.value, self.location = name, value, loc

class EnumType(BaseType):
    def __init__(self, name, loc, parent_env):
        BaseType.__init__(self)
        self.name, self.location = name, loc
        self.members = []
        self._env = ConstantEnv(name, parent_env)

    def add_member(self, m):
        self.members.append(m)

    def constant_env(self):
        return self._env

    def compute_size(self, targmach):
        return 4, 4

    def default_value(self):
        return self.members[0].value

    def create_value(self, v):
        return v

    def serialize(self, serializer, v):
        fmt = '>I' if serializer.targmach.big_endian else '<I'
        serializer.write(struct.pack(fmt, v.value))

class StructMember(object):
    def __init__(self, raw_member, mtype):
        self.mtype = mtype
        self.parse_node = raw_member
        self.mname = raw_member.name
        self.location = raw_member.location
        self.offset = -1 

    def has_option(self, name):
        return self.parse_node.has_option(name)

    def get_options(self, name):
        return self.parse_node.get_options(name)

class ConstantEnv:
    def __init__(self, name = None, parent = None):
        self._order = []
        self._e = {}
        self._parent = parent
        self._children = {}
        if parent is not None:
            self._root = parent._root
            assert name is not None
            parent._add_child(name, self)
        else:
            self._root = self

    def _add_child(self, name, child):
        self._children[name] = child

    def _get_child(self, loc, name):
        ns = self._children.get(name)
        if ns is None:
            raise TypeSystemException(loc, "unknown namespace '%s'" % (name))
        return ns

    def lookup_value(self, loc, name):
        dotidx = name.find('.')
        if dotidx == -1:
            return self._scope_lookup(loc, name)
        else:
            parts = name.split('.')
            ns = self._root
            for part in parts[:-1]:
                ns = ns._get_child(loc, part)
            value = ns._e.get(parts[-1])
            if value is None:
                raise TypeSystemException(loc, "unknown identifier '%s'" % (name))
            return value[1]

    def _scope_lookup(self, loc, name):
        e = self
        while e is not None:
            v = e._e.get(name)
            if v is None:
                e = self._parent
            else:
                return v[1]
        raise TypeSystemException(loc, "undefined constant: '%s'" % (name))

    def define(self, loc, name, value):
        assert name.find('.') == -1
        if self._e.has_key(name):
            raise TypeSystemException(loc, "duplicate constant: '%s'")
        self._order.append(name)
        self._e[name] = (loc, value)

    def iter(self):
        for name in self._order:
            loc, value = self._e[name]
            yield name, value, loc

class StructType(BaseType):
    def __init__(self, name, loc):
        BaseType.__init__(self)
        self.name = name
        self.location = loc
        self.members = []
        self._memhash = {}
        self.base_type = None # struct type included in this type
        self.classobj = None
        self._str = name

    def member_by_name(self, name):
        return self._memhash.get(name)

    def set_base_struct(self, t):
        if self.base_type is not None:
            raise TypeSystemException(None, '%s already has a base' % (self.name))
        self.base_type = t

    def is_superset_of(self, other):
        if self is other:
            return True

        if not isinstance(other, StructType):
            return False
        
        # Check if the other type is a base of this type, recursively.
        t = self
        base = t.base_type
        while base is not None:
            if base is other:
                return True
            base = base.base_type

        return False

    def set_class_object(self, cls):
        self.classobj = cls

    def compute_size(self, targmach):
        off = 0
        maxalign = 1
        for mem in self.members:
            t = mem.mtype
            tsize, align = targmach.size_align(t)
            off = (off + align - 1) & ~(align - 1)
            mem.offset = off
            off += tsize
            maxalign = max(align, maxalign)

        size = (off + (maxalign - 1)) & ~(maxalign - 1)
        alignment = maxalign

        return (size, alignment)

    def add_member(self, mem):
        if self._memhash.has_key(mem.mname):
            raise TypeSystemException(mem.location, "duplicate struct member %s" % (mem.mname))
        self._memhash[mem.mname] = mem
        self.members.append(mem)

    def get_field_type(self, name):
        m = self._memhash.get(name)
        if m is None:
            raise PythonMappingException("struct '%s' has no field '%s'" % (self.name, name))
        return m.mtype

    def default_value(self):
        """Generate a default struct value (all zeroes)"""
        instance = self.classobj()
        for m in self.members:
            instance[m.mname] = m.mtype.default_value
        return instance

    def create_value(self, v):
        if type(v) != self.classobj:
            raise TypeSystemException(None, '%s cannot be assigned to %s' % (type(v), self.name))
        return v

    def serialize(self, serializer, datum):
        sz, align = serializer.targmach.size_align(self)
        serializer.align(align)
        start = serializer.here()
        serializer.update_location(datum)
        for mem in self.members:
            mem.mtype.serialize(serializer, datum.__getattr__(mem.mname))
        end = serializer.here()
        actual_size = end[1] - start[1]
        if sz != actual_size:
            raise TypeSystemException(None, "%s serialized to %d bytes; expected %d" % (self.name, actual_size, sz))

    def __repr__(self): # pragma: no cover
        return self._str

    def __str__(self):
        return self._str

class PrimitiveType(BaseType):
    def __init__(self, name, size, loc):
        BaseType.__init__(self)
        self.name = name
        self.location = loc
        self.size = size

    def compute_size(self, targmach):
        return self.size, self.size

    def __repr__(self): # pragma: no cover
        return self.name

    def __str__(self):
        return self.name

class IntegerType(PrimitiveType):
    def __init__(self, name, size, loc, min, max):
        PrimitiveType.__init__(self, name, size, loc)
        self.min = min
        self.max = max

    def default_value(self):
        return 0

    def create_value(self, v):
        v = int(v)
        if v < self.min or v > self.max:
            raise TypeSystemException(None, 'value %d is out of range for datatype %s (min: %d, max: %d)' %
                    (v, self.name, self.min, self.max))
        return v

int_format_codes = {
    'u1': 'B',
    'u2': 'H',
    'u4': 'I',
    'u8': 'Q',
    's1': 'b',
    's2': 'h',
    's4': 'i',
    's8': 'q',
}

class SignedIntType(IntegerType):
    def __init__(self, name, size, loc):
        fmt = int_format_codes['s%d' % (size)]
        self._fmt_le = '<' + fmt
        self._fmt_be = '>' + fmt
        min = -(1 << (size * 8 - 1))
        max = (1 << (size * 8 - 1)) - 1
        IntegerType.__init__(self, name, size, loc, min, max)

    def serialize(self, serializer, datum):
        fmt = self._fmt_be if serializer.targmach.big_endian else self._fmt_le
        data = struct.pack(fmt, datum)
        serializer.align(self.size)
        serializer.write(data)

class CharacterType(PrimitiveType):
    def __init__(self, name, size, loc):
        PrimitiveType.__init__(self, name, size, loc)
        self._nil = '\0'

    def default_value(self):
        return self._nil

    def create_value(self, v):
        if isinstance(v, str) and len(v) == 1:
            return v
        elif v is int:
            return chr(v)
        else:
            raise PythonMappingException('characters must be one-char strings: %s', str(v))

    def serialize(self, serializer, datum):
        serializer.write(datum)

class UnsignedIntType(IntegerType):
    def __init__(self, name, size, loc):
        fmt = int_format_codes['u%d' % (size)]
        self._fmt_le = '<' + fmt
        self._fmt_be = '>' + fmt
        min = 0
        max = (1 << (size * 8)) - 1
        IntegerType.__init__(self, name, size, loc, min, max)

    def serialize(self, serializer, datum):
        fmt = self._fmt_be if serializer.targmach.big_endian else self._fmt_le
        data = struct.pack(fmt, datum)
        serializer.align(self.size)
        serializer.write(data)

class FloatingType(PrimitiveType):
    def __init__(self, name, size, loc):
        PrimitiveType.__init__(self, name, size, loc)
        if 4 == size:
            self._fmt_le = '<f'
            self._fmt_be = '>f'
        elif 8 == size:
            self._fmt_le = '<d'
            self._fmt_be = '>d'
        else:
            assert False

    def default_value(self):
        return 0.0

    def create_value(self, v):
        return float(v)

    def serialize(self, serializer, datum):
        fmt = self._fmt_be if serializer.targmach.big_endian else self._fmt_le
        data = struct.pack(fmt, datum)
        serializer.align(self.size)
        serializer.write(data)

class IntegerConstant(object):
    def __init__(self, name, value):
        self.name, self.value = name, value

class TypeSystem(object):
    def __init__(self, raw_data):
        object.__init__(self)
        self._types = {}
        self._typeorder = []
        self._structs = []
        self._enums = []
        self._raw_types = {}
        self._bases_applies = {}
        self._global_env = ConstantEnv()

        for p in raw_data:
            if isinstance(p, RawStructType):
                self._raw_types[p.name] = p

        # pass 1: add primitives & struct shells so we can resolve all named types
        for p in raw_data:
            if isinstance(p, RawDefPrimitive):
                self._add_primitive(p)
            elif isinstance(p, RawStructType):
                self._add_struct(p)
            elif isinstance(p, RawEnumType):
                self._add_enum(p)
            elif isinstance(p, RawImportStmt):
                raise TypeSystemException(p.location, "unresolved import statements present")
            elif isinstance(p, GeneratorConfig):
                continue
            elif isinstance(p, RawConstant):
                continue
            else:
                assert False

        # pass 2: evaluate all integer constants and enums
        for p in raw_data:
            if isinstance(p, RawEnumType):
                self._add_enum_members(p)
            elif isinstance(p, RawConstant):
                self._add_constant(p)

        # pass 3: resolve all struct member types
        for p in raw_data:
            if isinstance(p, RawStructType):
                self._add_struct_members(p)

        # pass 4: check non-recursive struct definitions
        self._check_structs()

    def _add_constant(self, c):
        expr = c.expr
        value = expr.eval(self._global_env)
        self._global_env.define(c.location, c.name, value)

    def itertypes(self):
        for name in self._typeorder:
            yield self._types[name]

    def iterconsts(self):
        return self._global_env.iter()

    def lookup(self, name):
        return self._types[name]

    def _add_type(self, name, type_obj):
        assert isinstance(name, str)
        assert isinstance(type_obj, BaseType)
        self._typeorder.append(name)
        self._types[name] = type_obj 

    def _add_primitive(self, p):
        name = p.name
        size = p.size
        pclass = p.pclass
        loc = p.location

        if self._types.has_key(name):
            raise TypeSystemException(loc, "duplicate type name %s" % (name))

        o = None
        if 'uint' == pclass:
            o = UnsignedIntType(name, size, loc)
        elif 'sint' == pclass:
            o = SignedIntType(name, size, loc)
        elif 'float' == pclass:
            o = FloatingType(name, size, loc)
        elif 'character' == pclass:
            o = CharacterType(name, size, loc)
        else:
            raise TypeSystemException(loc, "%s: unsupported primitive class '%s'" % (name, pclass))

        self._add_type(name, o)

    def _add_struct(self, p):
        name = p.name
        loc = p.location
        if self._types.has_key(name):
            raise TypeSystemException(loc, "duplicate type name %s" % (name))
        t = StructType(name, loc)
        self._add_type(name, t)
        self._structs.append(t)

    def _add_enum(self, p):
        loc = p.location
        name = p.name
        if self._types.has_key(name):
            raise TypeSystemException(loc, "duplicate type name %s" % (name))

        t = EnumType(name, loc, self._global_env)
        self._add_type(name, t)
        self._enums.append(t)

    def _add_enum_members(self, p):
        enum_name = p.name
        e = self._types[enum_name]
        env = e.constant_env()

        for m in p.members:
            name = m.name
            expr = m.expr
            value = expr.eval(env)
            env.define(m.location, name, value)
            e.add_member(EnumMember(name, value, p.location))

    def _resolve_type(self, t):
        loc = t.location
        if isinstance(t, RawSimpleType):
            res = self._types.get(t.name)
            if res is None:
                raise TypeSystemException(loc, "undefined type '%s'" % (t.name))
            return res
        elif isinstance(t, RawPointerType):
            if t.is_cstring:
                return self._resolve_type(t.basetype).cstring_type(loc)
            else:
                return self._resolve_type(t.basetype).pointer_type(loc)
        elif isinstance(t, RawArrayType):
            at = self._resolve_type(t.basetype)
            for dim in t.dims:
                dim_int = dim.eval(self._global_env)
                at = at.array_type(dim_int, loc)
            return at
        elif t is RawVoidType.instance:
            return VoidType.instance
        else:
            assert False

    def _apply_struct_base(self, target, srcelem, depth=0):
        first = True
        loc = srcelem.location
        for opt in srcelem.get_options('base'):
            # Check that base is only given once.
            if not first:
                raise TypeSystemException(loc, "'base' can only be specified once")
            first = False

            if len(opt.pos_params) != 1:
                raise TypeSystemException(loc,
                        "'base' option must have a single "\
                        "positional parameter, the base struct")

            base_name = opt.pos_params[0]
            raw_base = self._raw_types.get(base_name)
            if raw_base is None:
                raise TypeSystemException(loc, "'base' struct %s is undefined" % (base_name))

            if 0 == depth:
                target.set_base_struct(self._types[base_name])

            # apply bases recursively
            self._apply_struct_base(target, raw_base, depth+1)

            # add all inherited members
            for mem in raw_base.members:
                t = self._resolve_type(mem.type)
                target.add_member(StructMember(mem, t))

    def _add_struct_members(self, p):
        struct = self._types[p.name]

        # make sure all base structs are in place
        self._apply_struct_base(struct, p)

        # add all regular members
        for mem in p.members:
            t = self._resolve_type(mem.type)
            struct.add_member(StructMember(mem, t))

    def _check_struct(self, s):
        self._tstack.append(s)
        for mem in s.members:
            t = mem.mtype
            if isinstance(t, StructType):
                if t in self._tstack:
                    raise TypeSystemException(mem.location, "recursive structure not allowed")
                self._check_struct(t)
        self._tstack.pop()

    def _check_structs(self):
        self._tstack = []
        for s in self._structs:
            self._check_struct(s)
        del self._tstack

def compile_types(raw_data):
    return TypeSystem(raw_data)


