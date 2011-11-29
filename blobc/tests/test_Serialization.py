import blobc
import unittest

from struct import pack

class TestSerializer(unittest.TestCase):

    def _setup(self, src):
        pt = blobc.parse_string(src)
        tsys = blobc.compile_types(pt)
        classes = {}
        blobc.generate_classes(tsys, classes)
        return classes

    def test_simple(self):
        c = self._setup("""
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
        c = self._setup("""
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
        c = self._setup("""
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
        c = self._setup("""
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
        c = self._setup("""
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
        c = self._setup("""
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
        c = self._setup("""
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
        c = self._setup("""
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
        c = self._setup("""
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
        c = self._setup("""
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
        c = self._setup("""
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
        c = self._setup("""
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
        c = self._setup("""
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

