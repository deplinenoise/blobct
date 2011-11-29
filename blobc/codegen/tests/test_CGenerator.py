import unittest
import blobc
from blobc.codegen.tests.util import compress_c
from blobc.Typesys import TypeSystemException
from blobc.codegen import CGenerator
from cStringIO import StringIO

stdprim = '''
    defprimitive u8 uint 1; defprimitive u16 uint 2; defprimitive u32 uint 4;
    defprimitive s8 sint 1; defprimitive s16 sint 2; defprimitive s32 sint 4;
    defprimitive f32 float 4; defprimitive f64 float 8;
    defprimitive char character 1;
'''

outprim = '''
    typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32;
    typedef int8_t s8; typedef int16_t s16; typedef int32_t s32;
    typedef float f32; typedef double f64;
'''

class TestCodeGen_C(unittest.TestCase):
    class Data:
        def __init__(self, src):
            src = "generator c : no_separators, no_include_guard, no_inttypes;\n" + src
            self.parse_tree = blobc.parse_string(src)
            self.tsys = blobc.compile_types(self.parse_tree)
            out_fh = StringIO()
            aux_fh = StringIO()
            self.gen = CGenerator(out_fh, 'input.blob', aux_fh, 'output.h')
            self.gen.generate_code(self.parse_tree, self.tsys)
            self.output = compress_c(out_fh.getvalue())
            self.aux_output = compress_c(aux_fh.getvalue())

    def _compile(self, src):
        TestCodeGen_C.Data(src)

    def _check(self, src, expected):
        d = TestCodeGen_C.Data(src)
        self.assertEqual(compress_c(expected), d.output)

    def test_constant1(self):
        d = self._check('''iconst foo = 7;''', ''' enum { foo = 7 }; ''')

    def test_constant2(self):
        d = self._check('''iconst foo = 7 + 9;''', ''' enum { foo = 16 }; ''')

    def test_constant3(self):
        d = self._check('''iconst foo = 7 / 9;''', ''' enum { foo = 0 }; ''')

    def test_constant4(self):
        d = self._check('''iconst foo = 1 << 8;''', ''' enum { foo = 256 }; ''')

    def test_constant5(self):
        d = self._check('''iconst foo = 1 << 8 + 1;''', ''' enum { foo = 512 }; ''')

    def test_constant6(self):
        d = self._check('''iconst foo = (1 << 8) + 1;''', ''' enum { foo = 257 }; ''')

    def test_constant7(self):
        d = self._check('''
            iconst foo = 17;
            iconst bar = 10 * foo;
        ''', '''
            enum { foo = 17, bar = 170 };
        ''')

    def test_constant8(self):
        d = self._check('''
            iconst foo = 17;
            iconst bar = 10 * foo;
            iconst baz = (10 * foo - bar + 1) * 2;
        ''', '''
            enum { foo = 17, bar = 170, baz = 2 };
        ''')

    def test_constant_enumref(self):
        d = self._check('''
            enum Foo { Bar = 10 };
            iconst Baz = Foo.Bar + 1;
        ''', '''
            enum { Baz = 11 }; typedef enum { Foo_Bar = 10 } Foo;
        ''')

    def test_constant_constref(self):
        d = self._check('''
            iconst Baz = -1;
            enum Foo { Bar = Baz * 2 };
        ''', '''
            enum { Baz = -1 }; typedef enum { Foo_Bar = -2 } Foo;
        ''')

    def test_defprimitive(self):
        d = self._check(stdprim, outprim) 

    def test_defprimitive_alias(self):
        '''Check "float" maps directly to "float" when matching'''
        d = self._check('''
            defprimitive float float 4;
        ''', ''' ''')

    def test_defprimitive_alias_conflict(self):
        '''Check "float" is wrapped when not when not matching'''
        d = self._check('''
            defprimitive float float 8;
        ''', '''
            typedef double blobc_c_wrap_float;
        ''')

    def test_struct_empty(self):
        d = self._check('''
            struct Foo { };
        ''', '''
            struct Foo_TAG;
            typedef struct Foo_TAG { } Foo;
        ''')

    def test_struct_single_member(self):
        d = self._check(stdprim + '''
            struct Foo {
                u32 Bar;
            };
        ''', outprim + '''
            struct Foo_TAG;
            typedef struct Foo_TAG { u32 Bar; } Foo;
        ''')

    def test_struct_tag_option_empty(self):
        d = self._check(stdprim + '''
            generator c : struct_suffix("")
            struct Foo {
                u32 Bar;
            };
        ''', outprim + '''
            struct Foo;
            typedef struct Foo { u32 Bar; } Foo;
        ''')

    def test_struct_tag_option(self):
        d = self._check(stdprim + '''
            generator c : struct_suffix("^^^")
            struct Foo {
                u32 Bar;
            };
        ''', outprim + '''
            struct Foo^^^;
            typedef struct Foo^^^ { u32 Bar; } Foo;
        ''')

    def test_error_duplicate_member(self):
        with self.assertRaises(TypeSystemException):
            self._compile(stdprim + '''
                struct Foo {
                    u8 Bar;
                    u8 Bar;
                };
            ''')

    def test_error_duplicate_struct(self):
        with self.assertRaises(TypeSystemException):
            self._compile(stdprim + '''
                struct Foo {}
                struct Foo { u8 Bar; }
            ''')

    def test_error_duplicate_type_enum(self):
        with self.assertRaises(TypeSystemException):
            self._compile(stdprim + '''
                enum Foo { A = 7 }
                enum Foo { B = 7 }
            ''')

    def test_error_duplicate_type(self):
        with self.assertRaises(TypeSystemException):
            self._compile(stdprim + '''
                enum Foo { A = 7 }
                struct Foo { u8 Bar; }
            ''')

    def test_array_simple(self):
        d = self._check(stdprim + '''
            struct Foo {
                u32[7] Bar;
            };
        ''', outprim + '''
            struct Foo_TAG;
            typedef struct Foo_TAG { u32 Bar[7]; } Foo;
        ''')

    def test_array_multi(self):
        d = self._check(stdprim + '''
            struct Foo {
                u32[1,2,3] Bar;
            };
        ''', outprim + '''
            struct Foo_TAG;
            typedef struct Foo_TAG { u32 Bar[1][2][3]; } Foo;
        ''')

    def test_array_ptr(self):
        d = self._check(stdprim + '''
            struct Foo {
                u32**[2] Bar;
            };
        ''', outprim + '''
            struct Foo_TAG;
            typedef struct Foo_TAG { u32** Bar[2]; } Foo;
        ''')

    def test_cstring(self):
        d = self._check(stdprim + '''
            struct Foo {
                __cstring<char> Bar;
            };
        ''', outprim + '''
            struct Foo_TAG;
            typedef struct Foo_TAG { char* Bar; } Foo;
        ''')

    def test_cstring_ptr(self):
        d = self._check(stdprim + '''
            struct Foo {
                __cstring<char>* Bar;
            };
        ''', outprim + '''
            struct Foo_TAG;
            typedef struct Foo_TAG { char** Bar; } Foo;
        ''')

    def test_cstring_array(self):
        d = self._check(stdprim + '''
            struct Foo {
                __cstring<char>[20] Bar;
            };
        ''', outprim + '''
            struct Foo_TAG;
            typedef struct Foo_TAG { char* Bar[20]; } Foo;
        ''')

    def test_cdecl_option(self):
        d = self._check(stdprim + '''
            struct Foo {
                void* Bar : c_decl("struct SomeOtherType* Frob");
            };
        ''', outprim + '''
            struct Foo_TAG;
            typedef struct Foo_TAG { struct SomeOtherType* Frob; } Foo;
        ''')

    def test_struct_containment(self):
        d = self._check(stdprim + '''
            struct Baz {
                u32 a;
                u32 b;
            };
            struct Foo {
                Bar[2] a;
            };
            struct Bar {
                Baz a;
            };
        ''', outprim + '''
            struct Baz_TAG;
            struct Bar_TAG;
            struct Foo_TAG;
            typedef struct Baz_TAG { u32 a; u32 b; } Baz;
            typedef struct Bar_TAG { struct Baz_TAG a; } Bar;
            typedef struct Foo_TAG { struct Bar_TAG a[2]; } Foo;
        ''')

