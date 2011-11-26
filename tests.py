
import blobc
import unittest

import blobc
from struct import pack
from blobc.ParseTree import *
from blobc.Parser import ParseError
from blobc.Typesys import TypeSystemException

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

    def test_character(self):
        for size in (1, 2, 4):
            self.__testprim("bar", "character", size)

    def test_float(self):
        for size in (4, 8):
            self.__testprim("bar", "float", size)

    def test_illegal_sizes(self):
        self.assertRaises(ParseError, self.__testprim, "foo", "sint", 3)
        self.assertRaises(ParseError, self.__testprim, "foo", "uint", 9)
        self.assertRaises(ParseError, self.__testprim, "foo", "float", 1)
        self.assertRaises(ParseError, self.__testprim, "foo", "character", 8)
        self.assertRaises(ParseError, self.__testprim, "foo", "sint", -1)

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
        options = foo.get_options('fiskrens')
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].name, "fiskrens")
        self.assertEqual(options[0].pos_param_count(), 0)

    def test_option_one_param_no_value(self):
        p = blobc.parse_string("""struct foo : fiskrens("bar") { }""")
        foo = p[0]
        options = foo.get_options('fiskrens')
        self.assertEqual(options[0].name, "fiskrens")
        self.assertEqual(options[0].pos_param_count(), 1)
        self.assertEqual(options[0].pos_param(0), "bar")
    
    def test_option_one_param_with_value(self):
        p = blobc.parse_string("""struct foo : fiskrens(bar=yep) { }""")
        foo = p[0]
        options = foo.get_options('fiskrens')
        self.assertEqual(options[0].name, "fiskrens")
        self.assertEqual(options[0].pos_param_count(), 0)
        self.assertEqual(options[0].kw_param("bar"), "yep")

    def test_option_multi_params(self):
        p = blobc.parse_string('''
                struct foo :
                    a("foo", bar=89, baz=tjoho),
                    qux,
                    qux(visst="serru")
                { }''')
        foo = p[0]
        options = foo.get_options("a")
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].pos_param_count(), 1)
        self.assertEqual(options[0].pos_param(0), "foo")
        self.assertEqual(options[0].kw_param("bar"), 89)
        self.assertEqual(options[0].kw_param("baz"), "tjoho")

        options = foo.get_options("qux")
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0].name, "qux")
        self.assertEqual(options[0].pos_param_count(), 0)

        self.assertEqual(options[1].name, "qux")
        self.assertEqual(options[1].pos_param_count(), 0)
        self.assertEqual(options[1].kw_param("visst"), "serru")

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

    def test_void_parse_error(self):
        # Make sure void cannot be used standalone.
        with self.assertRaises(blobc.ParseError):
            p = blobc.parse_string('''struct foo { void foo; }''')

    def test_void_star(self):
        p = blobc.parse_string('''struct foo { void *foo; }''')
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0].name, "foo")
        self.assertEqual(len(p[0].members), 1)
        m0 = p[0].members[0]
        self.assertIsInstance(m0.type, RawPointerType)
        self.assertIsInstance(m0.type.basetype, RawVoidType)

    def test_member_option(self):
        p = blobc.parse_string('''struct foo {
                void *foo : foo, bar("foo", a="another string");
        }''')
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0].name, "foo")
        self.assertEqual(len(p[0].members), 1)
        m0 = p[0].members[0]
        options = m0.get_options('foo')
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].pos_param_count(), 0)

        options = m0.get_options('bar')
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].pos_param_count(), 1)
        self.assertEqual(options[0].pos_param(0), "foo")
        self.assertTrue(options[0].has_kw_param("a"))
        self.assertEqual(options[0].kw_param("a"), "another string")

    def test_cstring(self):
        p = blobc.parse_string('''struct foo {
                __cstring<char> a;
        }''')
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0].name, "foo")
        self.assertEqual(len(p[0].members), 1)
        m0 = p[0].members[0]
        self.assertIsInstance(m0.type, RawPointerType)
        self.assertTrue(m0.type.is_cstring)

    def test_const(self):
        p = blobc.parse_string('''
        iconst a = 7;
        ''')
        self.assertEqual(len(p), 1)
        self.assertIsInstance(p[0], RawConstant)
        self.assertEqual(p[0].name, "a")
        self.assertEqual(p[0].value, 7)

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

    def test_struct_base(self):
        tsys = self.__setup("""
            defprimitive u32 uint 4;
            struct foo_base {
                u32 a;
            }
            struct foo : base(foo_base) {
                u32 b;
            }
        """)
        ta = tsys.lookup('foo')
        self.assertIsInstance(ta, blobc.Typesys.StructType)
        self.assertEqual(len(ta.members), 2)
        self.assertEqual(ta.members[0].mname, 'a')
        self.assertEqual(ta.members[1].mname, 'b')
        self.assertIs(ta.members[0].mtype, ta.members[1].mtype)

    def test_struct_base_error(self):
        with self.assertRaises(TypeSystemException):
            self.__setup("""
                defprimitive u32 uint 4;
                struct foo_base {
                    u32 a;
                }
                struct foo : base(foo_base), base(foo_base) {
                    u32 b;
                }
            """)

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

    def test_enum(self):
        tsys = self.__setup("""
            struct foo {
                void *a;
                void **b;
            }
        """)
        ta = tsys.lookup('foo')
        self.assertEqual(ta.members[0].mname, 'a')
        self.assertEqual(ta.members[1].mname, 'b')
        self.assertIsInstance(ta.members[0].mtype, blobc.Typesys.PointerType)
        self.assertIs(ta.members[0].mtype.base_type, blobc.Typesys.VoidType.instance)
        self.assertIsInstance(ta.members[1].mtype, blobc.Typesys.PointerType)
        self.assertIsInstance(ta.members[1].mtype.base_type, blobc.Typesys.PointerType)
        self.assertIs(ta.members[1].mtype.base_type.base_type, blobc.Typesys.VoidType.instance)

    def test_cstring(self):
        tsys = self.__setup('''
        defprimitive char character 1;
        struct foo {
                __cstring<char> a;
        }''')
        foo = tsys.lookup('foo')
        self.assertIsInstance(foo.members[0].mtype, blobc.Typesys.CStringType)
        self.assertIsInstance(foo.members[0].mtype.base_type, blobc.Typesys.CharacterType)

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

    def test_struct_base_ptr(self):
        c = self.__setup("""
            defprimitive u32 uint 4;
            struct foo_base {
                u32 a;
            }
            struct foo : base(foo_base) {
                u32 b;
            }
            struct bar {
                foo_base *test;
            }
        """)
        foo, bar = c['foo'], c['bar']
        data = bar(test=foo(a=1, b=2))

    def test_struct_base_ptr_recursively(self):
        c = self.__setup("""
            defprimitive u32 uint 4;
            struct foo_base1 {
                u32 a;
            }
            struct foo_base2 : base(foo_base1) {
                u32 b;
            }
            struct foo : base(foo_base2) {
                u32 c;
            }
            struct bar {
                foo_base1 *test;
            }
        """)
        foo, bar = c['foo'], c['bar']
        data = bar(test=foo(a=1, b=2, c=3))

    def test_struct_base_ptr_error(self):
        c = self.__setup("""
            defprimitive u32 uint 4;
            struct foo_base {
                u32 a;
            }
            struct foo : base(foo_base) {
                u32 b;
            }
            struct bar {
                foo *test;
            }
        """)
        foo_base, bar = c['foo_base'], c['bar']
        with self.assertRaises(TypeSystemException):
            data = bar(test=foo_base(a=1))

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

    def test_void_ptr_null(self):
        c = self.__setup("""
            defprimitive ulong uint 4;
            struct bar {
                void* ptr;
            }
        """)
        data = c['bar'](ptr=None)
        tm = blobc.TargetMachine(endian='big', pointer_size=4)
        blob, relocs = blobc.layout(data, tm)
        self.assertEqual(blob, pack('>I', 0))
        self.assertEqual(relocs, '')

    def test_void_ptr_instance(self):
        c = self.__setup("""
            defprimitive ulong uint 4;
            struct foo {
                ulong a;
            }
            struct bar {
                void* ptr;
            }
        """)
        f = c['foo'](a=42);
        data = c['bar'](ptr=f)
        tm = blobc.TargetMachine(endian='big', pointer_size=4)
        blob, relocs = blobc.layout(data, tm)
        self.assertEqual(blob, pack('>II', 4, 42))
        self.assertEqual(relocs, pack('>I', 0))

    def test_void_ptr_array(self):
        c = self.__setup("""
            defprimitive ulong uint 4;
            struct foo {
                ulong[3] a;
            }
            struct bar {
                void* ptr;
            }
        """)
        f = c['foo'](a=[1, 2, 3]);
        data = c['bar'](ptr=(f.a, 2))
        tm = blobc.TargetMachine(endian='big', pointer_size=4)
        blob, relocs = blobc.layout(data, tm)
        self.assertEqual(blob, pack('>IIII', 12, 1, 2, 3))
        self.assertEqual(relocs, pack('>I', 0))

    def test_cstring(self):
        c = self.__setup("""
            defprimitive char8 character 1;
            struct foo {
                __cstring<char8> a;
            }
        """)
        data = c['foo'](a="text string");
        tm = blobc.TargetMachine(endian='big', pointer_size=4)
        blob, relocs = blobc.layout(data, tm)
        self.assertEqual(blob, pack('>I', 4) + "text string\0")
        self.assertEqual(relocs, pack('>I', 0))

    def test_ptr_inside_cstring(self):
        c = self.__setup("""
            defprimitive char8 character 1;
            struct foo {
                __cstring<char8> a;
                char8* substr;
            }
        """)
        f = c['foo'](a="this is a value");
        f.substr = (f.a, 4)
        tm = blobc.TargetMachine(endian='big', pointer_size=4)
        blob, relocs = blobc.layout(f, tm)
        self.assertEqual(blob, pack('>II', 8, 12) + "this is a value\0")
        self.assertEqual(relocs, pack('>II', 0, 4))

if __name__ == '__main__':
    unittest.main()
