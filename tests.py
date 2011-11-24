
import blobc
import unittest

import blobc
from struct import pack
from blobc.ParseTree import *
from blobc.Parser import ParseError

class TestParser(unittest.TestCase):

    def __testprim(self, name, pclass, size):
        parse_tree = blobc.parse_string("defprimitive %s %s %d\n" % (name, pclass, size))
        self.assertEqual(len(parse_tree), 1)
        self.assertEqual(type(parse_tree[0]), RawDefPrimitive)
        self.assertEqual(parse_tree[0].name, name)
        self.assertEqual(parse_tree[0].pclass, pclass)
        self.assertEqual(parse_tree[0].size, size)

    def test_signed_int(self):
        for size in (1, 2, 4, 8):
            self.__testprim("foo", "sint", size)

    def test_unsigned_int(self):
        for size in (1, 2, 4, 8):
            self.__testprim("bar", "uint", size)

    def test_float(self):
        for size in (4, 8):
            self.__testprim("bar", "float", size)

    def test_illegal_sizes(self):
        self.assertRaises(ParseError, self.__testprim, "foo", "sint", 3)
        self.assertRaises(ParseError, self.__testprim, "foo", "uint", 9)
        self.assertRaises(ParseError, self.__testprim, "foo", "float", 1)

    def test_empty_struct(self):
        p = blobc.parse_string("struct foo {}")
        self.assertEqual(len(p), 1)
        self.assertEqual(type(p[0]), RawStructType)
        self.assertEqual(p[0].name, 'foo')
        self.assertEqual(len(p[0].members), 0)

    def test_recursive_struct(self):
        p = blobc.parse_string("struct foo { foo* field; }")
        self.assertEqual(len(p), 1)
        self.assertEqual(type(p[0]), RawStructType)
        self.assertEqual(p[0].name, 'foo')
        self.assertEqual(p[0].members[0].name, "field")
        self.assertEqual(type(p[0].members[0].type), RawPointerType)

    def test_struct(self):
        p = blobc.parse_string("""
            defprimitive u32 uint 4;
            struct foo {
                u32 a;          // simple field
                u32* b;         // pointer
                u32[1] b;       // one-dimensional array
                u32[1,2,3] b;   // multi-dimensional array
            }""")
        self.assertEqual(len(p), 2)
        self.assertEqual(type(p[0]), RawDefPrimitive)
        self.assertEqual(type(p[1]), RawStructType)

class TestSerializer(unittest.TestCase):

    def __setup(self, src):
        pt = blobc.parse_string(src)
        tsys = blobc.compile_types(pt)
        classes = {}
        blobc.generate_classes(tsys, classes)
        return classes

    def test_simple(self):
        c = self.__setup("""
            defprimitive ubyte uint 1;
            defprimitive ushort uint 2;
            defprimitive ulong uint 4;
            struct foo {
                ubyte a;
                ubyte b;
                ushort c;
                ulong d;
            }
        """)
        data = c['foo'](a=1, b=2, c=3, d=77)
        tm = blobc.TargetMachine(endian='big', pointer_size=4)
        blob, relocs = blobc.layout(data, tm)
        self.assertEqual(blob, pack('>BBHI', 1, 2, 3, 77))
        self.assertEqual(relocs, '')

    def test_padding(self):
        c = self.__setup("""
            defprimitive ubyte uint 1;
            defprimitive ulong uint 4;
            struct foo {
                ubyte a;
                ulong b;
            }
        """)
        data = c['foo'](a=1, b=1)
        tm = blobc.TargetMachine(endian='big', pointer_size=4)
        blob, relocs = blobc.layout(data, tm)
        self.assertEqual(blob, pack('>BBBBI', 1, 0xfd, 0xfd, 0xfd, 1))
        self.assertEqual(relocs, '')

    def test_ptr(self):
        c = self.__setup("""
            defprimitive ulong uint 4;
            struct foo {
                ulong a;
                ulong b;
            }
            struct bar {
                ulong lala;
                foo* ptr;
                ulong bobo;
            }
        """)
        f = c['foo'](a=1, b=2);
        data = c['bar'](ptr=f)
        tm = blobc.TargetMachine(endian='big', pointer_size=4)
        blob, relocs = blobc.layout(data, tm)
        self.assertEqual(blob, pack('>IIIII', 0, 12, 0, 1, 2))
        self.assertEqual(relocs, pack('>I', 4))

    def test_ptr_array(self):
        c = self.__setup("""
            defprimitive ulong uint 4;
            struct foo {
                ulong* a;
            }
        """)
        data = c['foo'](a=[1, 2, 3])
        tm = blobc.TargetMachine(endian='big', pointer_size=4)
        blob, relocs = blobc.layout(data, tm)
        self.assertEqual(blob, pack('>IIII', 4, 1, 2, 3))
        self.assertEqual(relocs, pack('>I', 0))

    def test_ptr_inside_array(self):
        c = self.__setup("""
            defprimitive ulong uint 4;
            struct foo {
                ulong* a;
                ulong* b;
            }
        """)
        data = c['foo']()
        data.a = [1, 2, 3]
        data.b = (data.a, 1)
        tm = blobc.TargetMachine(endian='big', pointer_size=4)
        blob, relocs = blobc.layout(data, tm)
        self.assertEqual(blob, pack('>IIIII', 8, 12, 1, 2, 3))
        self.assertEqual(relocs, pack('>II', 0, 4))

    def test_ptr_inside_array_unanchored(self):
        c = self.__setup("""
            defprimitive ulong uint 4;
            struct foo {
                ulong* b;
            }
        """)
        data = c['foo']()
        data.b = [1, 2, 3]
        data.b = (data.b, 2)
        tm = blobc.TargetMachine(endian='big', pointer_size=4)
        blob, relocs = blobc.layout(data, tm)
        self.assertEqual(blob, pack('>IIII', 12, 1, 2, 3))
        self.assertEqual(relocs, pack('>I', 0))

if __name__ == '__main__':
    unittest.main()
