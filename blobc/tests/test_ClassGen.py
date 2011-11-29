import blobc
import unittest
from blobc.Typesys import TypeSystemException

class TestClassGen(unittest.TestCase):
    def _setup(self, src):
        pt = blobc.parse_string(src)
        tsys = blobc.compile_types(pt)
        classes = {}
        blobc.generate_classes(tsys, classes)
        return classes

    def test_struct(self):
        c = self._setup("""
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
        c = self._setup("""
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
        self.assertEqual(cls.BAR.value, 7)
        self.assertEqual(cls.BAZ.value, 8)
        self.assertEqual(cls.FROB.value, 9)

    def test_struct_base_ptr(self):
        c = self._setup("""
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
        c = self._setup("""
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
        c = self._setup("""
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


