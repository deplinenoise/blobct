
import re
import unittest
import blobc
from blobc.Typesys import TypeSystemException
from blobc.codegen import M68kGenerator
from blobc.codegen.tests.util import compress_c
from cStringIO import StringIO

stdprim = '''
    defprimitive u8 uint 1; defprimitive u16 uint 2; defprimitive u32 uint 4;
    defprimitive s8 sint 1; defprimitive s16 sint 2; defprimitive s32 sint 4;
    defprimitive f32 float 4; defprimitive f64 float 8;
    defprimitive char character 1;
'''

class TestCodeGen_M68K(unittest.TestCase):
    class Data:
        def __init__(self, src):
            src = 'generator m68k : no_comments, equ_label("equ");\n' + src
            self.parse_tree = blobc.parse_string(src)
            self.tsys = blobc.compile_types(self.parse_tree)
            out_fh = StringIO()
            aux_fh = StringIO()
            self.gen = M68kGenerator(out_fh, 'input.blob', aux_fh, 'output.h')
            self.gen.generate_code(self.parse_tree, self.tsys)
            self.output = compress_c(out_fh.getvalue())
            self.aux_output = compress_c(aux_fh.getvalue())

    def __compile(self, src):
        type(self).Data(sr)

    def __check(self, src, expected):
        d = type(self).Data(src)
        self.assertEqual(compress_c(expected), d.output)

    def test_constant1(self):
        d = self.__check('''iconst foo = 7;''', '''foo equ 7''')

    def test_constant2(self):
        d = self.__check('''iconst foo = 7 + 9;''', '''foo equ 16''')

    def test_constant3(self):
        d = self.__check('''iconst foo = 7 / 9;''', '''foo equ 0''')

    def test_constant4(self):
        d = self.__check('''iconst foo = 1 << 8;''', '''foo equ 256''')

    def test_constant5(self):
        d = self.__check('''
            iconst foo = 17;
            iconst bar = 10 * foo;
        ''', '''
            foo equ 17
            bar equ 170
        ''')

    def test_struct_empty(self):
        d = self.__check('''
            struct Foo { };
        ''', '''
            Foo_SIZE equ 0
            Foo_ALIGN equ 1
        ''')

    def test_struct_single_member(self):
        d = self.__check(stdprim + '''
            struct Foo {
                u32 Bar;
            };
        ''', '''
            Foo_Bar equ 0
            Foo_SIZE equ 4
            Foo_ALIGN equ 4
        ''')

    def test_sizeof_suffix(self):
        d = self.__check(stdprim + '''
            generator m68k : sizeof_suffix("_FOO"), alignof_suffix("_BAR")
            struct Foo {
                u32 Bar;
            };
        ''', '''
            Foo_Bar equ 0
            Foo_FOO equ 4
            Foo_BAR equ 4
        ''')

    def test_array_simple(self):
        d = self.__check(stdprim + '''
            struct Foo {
                u32[4] Bar;
            };
        ''', '''
            Foo_Bar equ 0
            Foo_SIZE equ 16 
            Foo_ALIGN equ 4 
        ''')

    def test_array_multi(self):
        d = self.__check(stdprim + '''
            struct Foo {
                u32[1,2,3] Bar;
            };
        ''', '''
            Foo_Bar equ 0
            Foo_SIZE equ 24 
            Foo_ALIGN equ 4 
        ''')
