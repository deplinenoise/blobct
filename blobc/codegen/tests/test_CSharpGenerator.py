import re
import unittest
import blobc
from cStringIO import StringIO

from blobc.Typesys import TypeSystemException
from blobc.codegen import CSharpGenerator, GeneratorException

from .util import *

class TestCodeGen_CSharp(unittest.TestCase):
    class Driver(CodegenTestDriver):
        def _apply_options(self, stream, kwargs):
            if not kwargs.get('comments', False):
                stream.write('generator csharp : no_comments;\n')
            if kwargs.get('namespace'):
                stream.write('generator csharp : namespace(%s);\n' % (kwargs['namespace']))

    def _get_output(self, src, **kwargs):
        d = type(self)._driver.run(src, kwargs)
        return d.output

    def _check(self, src, expected, **kwargs):
        d = type(self)._driver.run(src, kwargs)
        self.assertEqual(compress_c(expected), d.output)

    def _check_raises(self, src, **kwargs):
        with self.assertRaises(GeneratorException):
            type(self)._driver.run(src, kwargs)

    _driver = Driver(CSharpGenerator)

    def test_empty(self):
        self._check('', 'using System;')

    def test_csharp_names1(self):
        self._check('''iconst foo_bar = 1;''', '''
            using System;
            public partial class Constants { const int FooBar = 1; }
        ''')

    def test_csharp_names2(self):
        self._check('''iconst foobar = 1;''', '''
            using System;
            public partial class Constants { const int Foobar = 1; }
        ''')

    def test_csharp_names3(self):
        self._check('''iconst fooBar = 1;''', '''
            using System;
            public partial class Constants { const int fooBar = 1; }
        ''')

    def test_constant2(self):
        self._check('''iconst foo = 7 + 9;''', '''
            using System;
            public partial class Constants { const int Foo = 16; }
        ''')

    def _find_test(self, source, *expected):
        o = self._get_output(source)
        for x in expected:
            self.assertTrue(o.find(x) != -1, "could not find %s in %s" % (x, o))

    def _dotest_type(self, pclass, size, expected_name):
        self._find_test(
            'defprimitive X %s %d; struct foo { X a; }' % (pclass, size),
            ' public %s A ' % (expected_name))

    def test_byte(self):
        self._dotest_type('uint', 1, 'byte')

    def test_ushort(self):
        self._dotest_type('uint', 2, 'ushort')

    def test_uint(self):
        self._dotest_type('uint', 4, 'uint')

    def test_sbyte(self):
        self._dotest_type('sint', 1, 'sbyte')

    def test_short(self):
        self._dotest_type('sint', 2, 'short')

    def test_sbyte(self):
        self._dotest_type('sint', 4, 'int')

    def test_float(self):
        self._dotest_type('float', 4, 'float')

    def test_char(self):
        self._dotest_type('character', 1, 'char')

    def test_enum(self):
        self._check('''
            enum foo { a = 0, b = 1, c, d = a + b }
        ''', '''
            using System;
            enum Foo { A = 0, B = 1, C = 2, D = 1, }
        ''')

    def test_single_enum(self):
        self._check('''
            enum foo { a }
        ''', '''
            using System;
            enum Foo { A = 0, }
        ''')

    def test_member_csharp_name(self):
        self._find_test('''
            defprimitive X sint 1;
            struct foo { X a : csharp_name("Fiskrens"); }
        ''', ' public sbyte Fiskrens ');

    def test_member_csharp_name(self):
        self._find_test('''
            defprimitive X sint 1;
            struct foo { X a : csharp_name("Fiskrens"); }
        ''', ' public sbyte Fiskrens ');

    def test_array(self):
        self._find_test('''
            defprimitive X float 4;
            struct foo { X[3] blodpudding; }
        ''', ' public BlobCt.BlobArray<float> Blodpudding ',
        ' new BlobCt.BlobArray<float>(3);')

    def test_struct_member(self):
        self._find_test('''
            defprimitive X float 4;
            struct bar { X x; }
            struct foo { bar a; }
        ''', ' private Bar A_;',
        ' A_ = new Bar();')

    def test_ptr_member(self):
        self._find_test('''
            defprimitive X float 4;
            struct bar { X x; }
            struct foo { bar* a; }
        ''', ' public BlobCt.Pointer<Bar> A ')

    def test_string_member(self):
        self._find_test('''
            defprimitive X character 1;
            struct bar { __cstring<X> x; }
        ''', ' public string X ',
        '.WriteStringPointer(')

    def test_array_of_struct(self):
        self._find_test('''
            defprimitive X float 4;
            struct bar { X x; }
            struct foo { bar[3] a; }
        ''', ' private BlobCt.BlobArray<Bar> A_;',
        ' A_[x] = new Bar();')

    def test_emit(self):
        self._check('''
            generator csharp : emit("a");
            generator csharp : emit("b");
            generator csharp : emit("c");
        ''', 'using System; a b c')

    def test_namespace(self):
        self._check('''
            generator csharp : namespace("Fisk");
            enum foo { a }
        ''', 'using System; namespace Fisk { enum Foo { A = 0, } }')

    def test_void_raises(self):
        self._check_raises('''
            struct foo { void* a; }
        ''')

