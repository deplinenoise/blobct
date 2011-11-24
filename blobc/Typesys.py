
import types
import struct

from ParseTree import *

class PythonMappingException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class TypeSystemException(Exception):
    def __init__(self, loc, msg):
        if loc is not None:
            Exception.__init__(self, "%s(%d): %s" % (loc[0], loc[1], msg))
        else:
            Exception.__init__(self, msg)

class TypeCheckException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class BaseType(object):
    def __init__(self):
        self.__ptr_type = None
        self.__array_types = {}

    def pointer_type(self, loc):
        if self.__ptr_type is None:
            self.__ptr_type = PointerType(self, loc)
        return self.__ptr_type

    def array_type(self, dim, loc = None):
        r = self.__array_types.get(dim, None)
        if not r:
            r = ArrayType(self, dim, loc)
            self.__array_types[dim] = r
        return r

class Array(object):
    def __init__(self, ntype, items):
        self.items = [ntype.create_value(x) for x in items]
        self.item_type = ntype

    def __repr__(self):
        return "<%s>%s" % (str(self.item_type), repr(self.items))

    def __str__(self):
        return str(self.items)

class PointerType(BaseType):
    def __init__(self, base, loc):
        BaseType.__init__(self)
        self.base_type = base
        self.loc = loc
        self.__str = str(self.base_type) + '*'

    def compute_size(self, targmach):
        return (targmach.pointer_size(), targmach.pointer_align())

    def default_value(self):
        return None

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
            if type(v[0]) is Array and v[0].item_type is self.base_type:
                return v
            else:
                raise TypeCheckException('%s cannot point to %s' % (str(self), str(v)))

        # Or to an individual value, currently must be struct
        else:
            tv = type(v)
            if tv.srctype is self.base_type:
                return (v, 0)
            else:
                raise TypeCheckException('%s cannot point to %s', str(self), str(v))

    def __repr__(self):
        return self.__str

    def __str__(self):
        return self.__str

    def serialize(self, serializer, v):
        if v is None:
            serializer.write_null_ptr()
            return

        loc = None

        if isinstance(v, Array):
            loc = serializer.divert()
            self.base_type.array_type(len(v.items)).serialize(serializer, v)
            serializer.resume()
            serializer.write_ptr(loc)

        elif isinstance(v, tuple):
            targ_array = v[0]
            index = v[1]
            loc = serializer.location_of(targ_array)
            item_size = serializer.targmach().sizeof(self.base_type)
            serializer.write_ptr(loc, index * item_size)

        else:
            loc = serializer.divert()
            self.base_type.serialize(serializer, v)
            serializer.resume()
            serializer.write_ptr(loc)



class ArrayType(BaseType):
    def __init__(self, base, dim, loc):
        BaseType.__init__(self)
        self.base_type = base
        self.dim = dim
        self.loc = loc
        self.__str = '%s[%d]' % (str(self.base_type), dim)

    def compute_size(self, targmach):
        size, align = self.base_type.compute_size(targmach)
        size *= self.dim
        return (size, align)

    def default_value(self):
        return [self.base_type.default_value() for x in xrange(0, self.dim)]

    def create_value(self, v):
        if len(v) != self.dim:
            raise PythonMappingException("expected list of length %d; got list of %d items" % (self.dim, len(v)))
        return Array(self.base_type, v)

    def serialize(self, serializer, datum):
        serializer.align(serializer.targmach().alignof(self.base_type))
        serializer.update_location(datum)
        assert isinstance(datum, Array)
        for item in datum.items:
            self.base_type.serialize(serializer, item)

    def __repr__(self):
        return self.__str

    def __str__(self):
        return self.__str

class StructMember(object):
    def __init__(self, mname, mtype, loc):
        self.mname = mname
        self.mtype = mtype
        self.loc = loc
        self.offset = -1 

class StructType(BaseType):
    def __init__(self, name, loc):
        BaseType.__init__(self)
        self.name = name
        self.members = []
        self.loc = loc
        self.members = []
        self.memhash = {}
        self.__classobj = None
        self.__str = 'struct ' + name

    def set_class_object(self, cls):
        self.__classobj = cls

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

        #print "%s is %d bytes, align %d" % (self.name, size, alignment)
        #for mem in self.members:
        #    print '   %s at offset %d' % (mem.mname, mem.offset)

        return (size, alignment)

    def add_member(self, mem):
        if self.memhash.has_key(mem.mname):
            raise TypeSystemException(mem.loc, "duplicate struct member %s" % (mem.mname))
        self.memhash[mem.mname] = mem
        self.members.append(mem)

    def get_field_type(self, name):
        m = self.memhash.get(name)
        if m is None:
            raise PythonMappingException("struct '%s' has no field '%s'" % (self.name, name))
        return m.mtype

    def default_value(self):
        """Generate a default struct value (all zeroes)"""
        instance = self.__classobj()
        for m in self.members:
            instance[m.mname] = m.mtype.default_value()
        return instance

    def create_value(self, v):
        if type(v) != self.__classobj:
            raise TypeCheckException('%s cannot be assigned to %s' % (type(v), self.name))
        return v

    def serialize(self, serializer, datum):
        sz, align = serializer.targmach().size_align(self)
        serializer.align(align)
        start = serializer.here()
        serializer.update_location(datum)
        for mem in self.members:
            mem.mtype.serialize(serializer, datum.__getattr__(mem.mname))
        end = serializer.here()
        actual_size = end[1] - start[1]
        if sz != actual_size:
            raise TypeSystemException(None, "%s serialized to %d bytes; expected %d" % (self.name, actual_size, sz))

    def __repr__(self):
        return self.__str

    def __str__(self):
        return self.__str

class PrimitiveType(BaseType):
    def __init__(self, name, size, loc):
        BaseType.__init__(self)
        self.name = name
        self.loc = loc
        self.__size = size

    def size(self):
        return self.__size

    def compute_size(self, targmach):
        return self.__size, self.__size

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

class IntegerType(PrimitiveType):
    def __init__(self, name, size, loc, min, max):
        PrimitiveType.__init__(self, name, size, loc)
        self.__min = min
        self.__max = max

    def default_value(self):
        return 0

    def create_value(self, v):
        v = int(v)
        if v < self.__min or v > self.__max:
            raise TypeCheckException('value %d is out of range for datatype %s (min: %d, max: %d)' %
                    (v, self.name, self.__min, self.__max))
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
        self.__fmt_le = '<' + fmt
        self.__fmt_be = '>' + fmt
        min = -(1 << (size * 8 - 1))
        max = (1 << (size * 8 - 1)) - 1
        IntegerType.__init__(self, name, size, loc, min, max)

    def serialize(self, serializer, datum):
        fmt = self.__fmt_be if serializer.targmach().big_endian() else self.__fmt_le
        data = struct.pack(fmt, datum)
        serializer.align(self.size())
        serializer.write(data)

class UnsignedIntType(IntegerType):
    def __init__(self, name, size, loc):
        fmt = int_format_codes['u%d' % (size)]
        self.__fmt_le = '<' + fmt
        self.__fmt_be = '>' + fmt
        min = 0
        max = (1 << (size * 8)) - 1
        IntegerType.__init__(self, name, size, loc, min, max)

    def serialize(self, serializer, datum):
        fmt = self.__fmt_be if serializer.targmach().big_endian() else self.__fmt_le
        data = struct.pack(fmt, datum)
        serializer.align(self.size())
        serializer.write(data)

class FloatingType(PrimitiveType):
    def __init__(self, name, size, loc):
        PrimitiveType.__init__(self, name, size, loc)
        if 4 == size:
            self.__fmt_le = '<f'
            self.__fmt_be = '>f'
        elif 8 == size:
            self.__fmt_le = '<d'
            self.__fmt_be = '>d'
        else:
            assert False

    def default_value(self):
        return 0.0

    def create_value(self, v):
        return float(v)

    def serialize(self, serializer, datum):
        fmt = self.__fmt_be if serializer.targmach().big_endian() else self.__fmt_le
        data = struct.pack(fmt, datum)
        serializer.align(self.size())
        serializer.write(data)

class TypeSystem(object):
    def __init__(self, raw_data):
        object.__init__(self)
        self.__types = {}
        self.__structs = []

        # pass 1: add primitives & struct shells so we can resolve all named types
        for p in raw_data:
            if isinstance(p, RawDefPrimitive):
                self.__add_primitive(p)
            elif isinstance(p, RawStructType):
                self.__add_struct(p)
            else:
                assert False

        # pass 2: resolve all struct member types
        for p in raw_data:
            if isinstance(p, RawStructType):
                self.__add_struct_members(p)

        # pass 3: check non-recursive struct definitions
        self.__check_structs()

    def itertypes(self):
        return self.__types.itervalues()

    def lookup(self, name):
        return self.__types[name]

    def __add_primitive(self, p):
        if self.__types.has_key(p.name):
            raise TypeSystemException(p.loc, "duplicate type name %s" % (p.name))
        o = None
        if 'uint' == p.pclass:
            o = UnsignedIntType(p.name, p.size, p.loc)
        elif 'sint' == p.pclass:
            o = SignedIntType(p.name, p.size, p.loc)
        elif 'float' == p.pclass:
            o = FloatingType(p.name, p.size, p.loc)
        else:
            raise TypeSystemException(p.loc, "%s: unsupported primitive class %s" % (p.name, p.pclass))

        self.__types[p.name] = o

    def __add_struct(self, p):
        if self.__types.has_key(p.name):
            raise TypeSystemException(p.loc, "duplicate type name %s" % (p.name))
        t = StructType(p.name, p.loc)
        self.__types[p.name] = t
        self.__structs.append(t)

    def __resolve_type(self, t):
        if isinstance(t, RawSimpleType):
            return self.__types[t.name]
        elif isinstance(t, RawPointerType):
            return self.__resolve_type(t.basetype).pointer_type(t.loc)
        elif isinstance(t, RawArrayType):
            at = self.__resolve_type(t.basetype)
            for dim in t.dims:
                at = at.array_type(dim, t.loc)
            return at

    def __add_struct_members(self, p):
        struct = self.__types[p.name]

        for mem in p.members:
            t = self.__resolve_type(mem.type)
            struct.add_member(StructMember(mem.name, t, mem.loc))

    def __check_struct(self, s):
        self.__tstack.append(s)
        for mem in s.members:
            t = mem.mtype
            if isinstance(t, StructType):
                if t in self.__tstack:
                    raise TypeSystemException(mem.loc, "recursive structure not allowed")
                self.__check_struct(t)
        self.__tstack.pop()

    def __check_structs(self):
        self.__tstack = []
        for s in self.__structs:
            self.__check_struct(s)
        del self.__tstack

def compile_types(raw_data):
    return TypeSystem(raw_data)


