
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

    def test_enum_empty(self):
        # Make sure empty enum declarations are not parsed.
        # We need at least one member in order to generate default values.
        with self.assertRaises(blobc.ParseError):
            blobc.parse_string("""enum foo { }""")

    def test_enum_single(self):
        p = blobc.parse_string("""
            enum foo {
                bar
                }""")
        self.assertEqual(len(p), 1)
        self.assertEqual(type(p[0]), RawEnumType)
        self.assertEqual(len(p[0].members), 1)
        self.assertEqual(type(p[0].members[0]), RawEnumMember)
        self.assertEqual(p[0].members[0].name, 'bar')
        self.assertEqual(p[0].members[0].value, None)

    def test_enum_single_trailing_comma(self):
        p = blobc.parse_string("""
            enum foo {
                bar,
                }""")
        self.assertEqual(len(p), 1)
        self.assertEqual(type(p[0]), RawEnumType)
        self.assertEqual(len(p[0].members), 1)
        self.assertEqual(type(p[0].members[0]), RawEnumMember)
        self.assertEqual(p[0].members[0].name, 'bar')
        self.assertEqual(p[0].members[0].value, None)

    def test_enum_double(self):
        p = blobc.parse_string("""
            enum foo {
                bar, baz
                }""")
        self.assertEqual(len(p), 1)
        self.assertEqual(type(p[0]), RawEnumType)
        self.assertEqual(len(p[0].members), 2)
        self.assertEqual(type(p[0].members[0]), RawEnumMember)
        self.assertEqual(p[0].members[0].name, 'bar')
        self.assertEqual(p[0].members[0].value, None)
        self.assertEqual(p[0].members[1].name, 'baz')
        self.assertEqual(p[0].members[1].value, None)

    def test_enum_assigned(self):
        p = blobc.parse_string("""
            enum foo {
                bar = 7, baz = 7
                }""")
        self.assertEqual(len(p), 1)
        self.assertEqual(type(p[0]), RawEnumType)
        self.assertEqual(len(p[0].members), 2)
        self.assertEqual(type(p[0].members[0]), RawEnumMember)
        self.assertEqual(p[0].members[0].name, 'bar')
        self.assertEqual(p[0].members[0].value, 7)
        self.assertEqual(p[0].members[1].name, 'baz')
        self.assertEqual(p[0].members[1].value, 7)

    def test_option_bare(self):
        p = blobc.parse_string("""struct foo : fiskrens { }""")
        foo = p[0]
        self.assertEqual(len(foo.options), 1)
        self.assertEqual(foo.options[0].name, "fiskrens")
        self.assertEqual(foo.options[0].pos_param_count(), 0)

    def test_option_one_param_no_value(self):
        p = blobc.parse_string("""struct foo : fiskrens("bar") { }""")
        foo = p[0]
        self.assertEqual(foo.options[0].name, "fiskrens")
        self.assertEqual(foo.options[0].pos_param_count(), 1)
        self.assertEqual(foo.options[0].pos_param(0), "bar")
    
    def test_option_one_param_with_value(self):
        p = blobc.parse_string("""struct foo : fiskrens(bar=yep) { }""")
        foo = p[0]
        self.assertEqual(foo.options[0].name, "fiskrens")
        self.assertEqual(foo.options[0].pos_param_count(), 0)
        self.assertEqual(foo.options[0].kw_param("bar"), "yep")

    def test_option_multi_params(self):
        p = blobc.parse_string('''
                struct foo :
                    a("foo", bar=89, baz=tjoho),
                    qux,
                    slap(visst="serru")
                { }''')
        foo = p[0]
        self.assertEqual(len(foo.options), 3)

        self.assertEqual(foo.options[0].name, "a")
        self.assertEqual(foo.options[0].pos_param(0), "foo")
        self.assertEqual(foo.options[0].kw_param("bar"), 89)
        self.assertEqual(foo.options[0].kw_param("baz"), "tjoho")

        self.assertEqual(foo.options[1].name, "qux")
        self.assertEqual(foo.options[1].pos_param_count(), 0)

        self.assertEqual(foo.options[2].name, "slap")
        self.assertEqual(foo.options[2].pos_param_count(), 0)
        self.assertEqual(foo.options[2].kw_param("visst"), "serru")

    def test_import(self):
        p = blobc.parse_string('''import "foo/bar"''')
        self.assertEqual(len(p), 1)
        self.assertIsInstance(p[0], blobc.ParseTree.RawImportStmt)
        self.assertEqual(p[0].filename, "foo/bar")

    def test_generator_config(self):
        p = blobc.parse_string('''
            generator foo : pretty_print(flavor="fiskrens", tabsize=4);
            generator bar : other_setting, foo(1, 2, a, b, c);
        ''')
        self.assertEqual(len(p), 2)
        self.assertIsInstance(p[0], blobc.ParseTree.GeneratorConfig)
        self.assertIsInstance(p[1], blobc.ParseTree.GeneratorConfig)

class TestTypeSystem(unittest.TestCase):

    def __setup(self, src):
        pt = blobc.parse_string(src)
        return blobc.compile_types(pt)

    def test_uint(self):
        tsys = self.__setup(""" defprimitive a uint 4; """)
        ta = tsys.lookup('a')
        self.assertIsInstance(ta, blobc.Typesys.UnsignedIntType)
        self.assertEqual(ta.size(), 4)

    def test_sint(self):
        tsys = self.__setup(""" defprimitive a sint 4; """)
        ta = tsys.lookup('a')
        self.assertIsInstance(ta, blobc.Typesys.SignedIntType)
        self.assertEqual(ta.size(), 4)

    def test_float(self):
        tsys = self.__setup(""" defprimitive a float 4; """)
        ta = tsys.lookup('a')
        self.assertIsInstance(ta, blobc.Typesys.FloatingType)
        self.assertEqual(ta.size(), 4)

    def test_struct(self):
        tsys = self.__setup("""
            defprimitive u32 uint 4;
            struct foo {
                u32 a;
                u32 b;
            }
        """)
        ta = tsys.lookup('foo')
        self.assertIsInstance(ta, blobc.Typesys.StructType)
        self.assertEqual(len(ta.members), 2)
        self.assertEqual(ta.members[0].mname, 'a')
        self.assertEqual(ta.members[1].mname, 'b')
        self.assertIs(ta.members[0].mtype, ta.members[1].mtype)

    def test_enum(self):
        tsys = self.__setup("""
            enum foo {
                a,
                b = 8,
                c,
            }
        """)
        ta = tsys.lookup('foo')
        self.assertIsInstance(ta, blobc.Typesys.EnumType)
        self.assertEqual(len(ta.members), 3)
        self.assertEqual(ta.members[0].name, 'a')
        self.assertEqual(ta.members[1].name, 'b')
        self.assertEqual(ta.members[2].name, 'c')
        self.assertEqual(ta.members[0].value, 0)
        self.assertEqual(ta.members[1].value, 8)
        self.assertEqual(ta.members[2].value, 9)

class TestClassGen(unittest.TestCase):
    def __setup(self, src):
        pt = blobc.parse_string(src)
        tsys = blobc.compile_types(pt)
        classes = {}
        blobc.generate_classes(tsys, classes)
        return classes

    def test_struct(self):
        c = self.__setup("""
            defprimitive ubyte uint 1;
            defprimitive ulong uint 4;
            struct foo {
                ubyte a;
                ulong b;
            }
        """)
        self.assertTrue(c.has_key('foo'))

        cls = c['foo']
        self.assertTrue(hasattr(cls, 'srctype'))
        self.assertIsInstance(cls.srctype, blobc.Typesys.StructType)

        inst = cls()
        self.assertTrue(hasattr(inst, 'a'))
        self.assertTrue(hasattr(inst, 'b'))

    def test_enum(self):
        c = self.__setup("""
            enum Foo {
                BAR = 7,
                BAZ,
                FROB,
            }
        """)
        self.assertTrue(c.has_key('Foo'))
        cls = c['Foo']
        self.assertTrue(hasattr(cls, 'BAR'))
        self.assertTrue(hasattr(cls, 'BAZ'))
        self.assertTrue(hasattr(cls, 'FROB'))
        self.assertEqual(cls.BAR.value(), 7)
        self.assertEqual(cls.BAZ.value(), 8)
        self.assertEqual(cls.FROB.value(), 9)

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

    def test_enum(self):
        c = self.__setup("""
            enum meh {
                BAR = 7,
            }
            struct foo {
                meh b;
            }
        """)
        data = c['foo']()
        data.b = c['meh'].BAR
        tm = blobc.TargetMachine(endian='big', pointer_size=4)
        blob, relocs = blobc.layout(data, tm)
        self.assertEqual(blob, pack('>I', 7))
        self.assertEqual(relocs, '')

    def test_enum_array(self):
        c = self.__setup("""
            enum meh {
                A = 3,
                B = 11,
                C = 77,
            }
            struct foo {
                meh* b;
            }
        """)
        data = c['foo']()
        m = c['meh']
        data.b = [m.A, m.B, m.C]
        tm = blobc.TargetMachine(endian='big', pointer_size=4)
        blob, relocs = blobc.layout(data, tm)
        self.assertEqual(blob, pack('>IIII', 4, 3, 11, 77))
        self.assertEqual(relocs, pack('>I', 0))

if __name__ == '__main__':
    unittest.main()
