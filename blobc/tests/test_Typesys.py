import blobc
import unittest

from blobc.Typesys import ConstantEnv, TypeSystemException
import unittest

class ConstantEnvTest(unittest.TestCase):

    def test_empty(self):
        e = ConstantEnv()
        with self.assertRaises(TypeSystemException):
            e.lookup_value(None, 'a')

    def test_empty(self):
        e = ConstantEnv()
        e.define(None, 'foo', 7)
        self.assertEqual(e.lookup_value(None, 'foo'), 7)

    def test_nested(self):
        root = ConstantEnv()
        child = ConstantEnv('Foo', root)
        child.define(None, 'Bar', 7)
        self.assertEqual(child.lookup_value(None, 'Bar'), 7)
        self.assertEqual(root.lookup_value(None, 'Foo.Bar'), 7)

class TestTypeSystem(unittest.TestCase):

    def __setup(self, src):
        pt = blobc.parse_string(src)
        return blobc.compile_types(pt)

    def test_uint(self):
        tsys = self.__setup(""" defprimitive a uint 4; """)
        ta = tsys.lookup('a')
        self.assertIsInstance(ta, blobc.Typesys.UnsignedIntType)
        self.assertEqual(ta.size, 4)

    def test_sint(self):
        tsys = self.__setup(""" defprimitive a sint 4; """)
        ta = tsys.lookup('a')
        self.assertIsInstance(ta, blobc.Typesys.SignedIntType)
        self.assertEqual(ta.size, 4)

    def test_float(self):
        tsys = self.__setup(""" defprimitive a float 4; """)
        ta = tsys.lookup('a')
        self.assertIsInstance(ta, blobc.Typesys.FloatingType)
        self.assertEqual(ta.size, 4)

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

    def test_enum1(self):
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

    def test_sptr(self):
        tsys = self.__setup("""
            struct foo {
                void *a;
                void **b;
            }
        """)
        ta = tsys.lookup('foo')
        a = ta.members[0]
        b = ta.members[1]
        self.assertEqual(a.mname, 'a')
        self.assertEqual(b.mname, 'b')
        self.assertIsInstance(a.mtype, blobc.Typesys.PointerType)
        self.assertIs(a.mtype.base_type, blobc.Typesys.VoidType.instance)
        self.assertIsInstance(b.mtype, blobc.Typesys.PointerType)
        self.assertIsInstance(b.mtype.base_type, blobc.Typesys.PointerType)
        self.assertIs(b.mtype.base_type.base_type, blobc.Typesys.VoidType.instance)

    def test_cstring(self):
        tsys = self.__setup('''
        defprimitive char character 1;
        struct foo {
                __cstring<char> a;
        }''')
        foo = tsys.lookup('foo')
        self.assertIsInstance(foo.members[0].mtype, blobc.Typesys.CStringType)
        self.assertIsInstance(foo.members[0].mtype.base_type, blobc.Typesys.CharacterType)

    def __check_eval_expr(self, a, b, op, expected):
        tsys = self.__setup("iconst val = %d %s %d;" % (a, op, b))
        for name, value, expr in tsys.iterconsts():
            self.assertEqual(name, 'val')
            self.assertEqual(value, expected)

    def test_add(self):
        self.__check_eval_expr(17, 3, '+', 20)
        self.__check_eval_expr(17, -17, '+', 0)
        self.__check_eval_expr(-17, 17, '+', 0)

    def test_sub(self):
        self.__check_eval_expr(17, 3, '-', 14)
        self.__check_eval_expr(17, -17, '-', 34)
        self.__check_eval_expr(-17, 17, '-', -34)
        self.__check_eval_expr(-17, -17, '-', 0)
        
