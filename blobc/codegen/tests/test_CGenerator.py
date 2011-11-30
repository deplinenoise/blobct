import unittest
import blobc
from blobc.codegen.tests.util import *
from blobc.Typesys import TypeSystemException
from blobc.codegen import CGenerator
from cStringIO import StringIO

stock_primitives = '''
    defprimitive u8 uint 1; defprimitive u16 uint 2; defprimitive u32 uint 4;
    defprimitive s8 sint 1; defprimitive s16 sint 2; defprimitive s32 sint 4;
    defprimitive f32 float 4; defprimitive f64 float 8;
    defprimitive char character 1;
'''

stock_primitives_gen = '''
    typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32;
    typedef int8_t s8; typedef int16_t s16; typedef int32_t s32;
    typedef float f32; typedef double f64;
'''

one_of_each = '''
    iconst Baz = 8;
    enum Bar { A, B, C }
    struct Frob {
        u32 Member;
    }
    struct Foo {
        Bar Barbie;
        Bar[1] BarbieArray;
        void*[1] VoidArray;
        Bar* BarPtr;
        Frob* FromPtr;
        Frob*[Baz] FrobPtrArray;
        Frob[Baz] FrobArray;
        Frob FromMember;
    }
'''

class TestCodeGen_C(unittest.TestCase):
    class Driver(CodegenTestDriver):
        def _apply_options(self, stream, kwargs):
            if not kwargs.get('no_primitives', False):
                stream.write(stock_primitives)
            if not kwargs.get('print_includes', True):
                stream.write('generator c : no_includes\n;')
            if not kwargs.get('separators', False):
                stream.write('generator c : no_separators;\n')
            if not kwargs.get('include_guard', False):
                stream.write('generator c : no_include_guard;\n')
            if not kwargs.get('inttypes', False):
                stream.write('generator c : no_inttypes;\n')

    _driver = Driver(CGenerator)

    def _compile(self, src, **kwargs):
        d = type(self)._driver.run(src, kwargs)
        return d.output

    def _check(self, src, expected, **kwargs):
        d = type(self)._driver.run(src, kwargs)
        hdrs = ''
        for inc in kwargs.get('expect_includes', ()):
            hdrs = hdrs + '#include ' + inc + '\n'
        if not kwargs.get('no_primitives', False):
            expected = stock_primitives_gen + ' ' +  expected
        expected = hdrs + expected
        if not kwargs.get('keep_ws', False):
            expected = compress_c(expected)
        self.assertEqual(d.output, expected)

    def test_constant1(self):
        self._check('''iconst foo = 7;''', ''' enum { foo = 7 }; ''')

    def test_constant2(self):
        self._check('''iconst foo = 7 + 9;''', ''' enum { foo = 16 }; ''')

    def test_constant3(self):
        self._check('''iconst foo = 7 / 9;''', ''' enum { foo = 0 }; ''')

    def test_constant4(self):
        self._check('''iconst foo = 1 << 8;''', ''' enum { foo = 256 }; ''')

    def test_constant5(self):
        self._check('''iconst foo = 1 << 8 + 1;''', ''' enum { foo = 512 }; ''')

    def test_constant6(self):
        self._check('''iconst foo = (1 << 8) + 1;''', ''' enum { foo = 257 }; ''')

    def test_constant7(self):
        self._check('''
            iconst foo = 17;
            iconst bar = 10 * foo;
        ''', '''
            enum { foo = 17, bar = 170 };
        ''')

    def test_constant8(self):
        self._check('''
            iconst foo = 17;
            iconst bar = 10 * foo;
            iconst baz = (10 * foo - bar + 1) * 2;
        ''', '''
            enum { foo = 17, bar = 170, baz = 2 };
        ''')

    def test_constant_enumref(self):
        self._check('''
            enum Foo { Bar = 10 };
            iconst Baz = Foo.Bar + 1;
        ''', '''
            enum { Baz = 11 }; typedef enum { Foo_Bar = 10 } Foo;
        ''')

    def test_constant_constref(self):
        self._check('''
            iconst Baz = -1;
            enum Foo { Bar = Baz * 2 };
        ''', '''
            enum { Baz = -1 }; typedef enum { Foo_Bar = -2 } Foo;
        ''')

    def test_array_constant(self):
        self._check('''
            iconst DIM = 0x1 << 0x8;
            struct Foo { void*[DIM] Bar; }
        ''', '''
            enum { DIM = 256 };
            struct Foo_TAG;
            typedef struct Foo_TAG { void* Bar[256]; } Foo;
        ''')

    def test_defprimitive(self):
        self._check('', '') 

    def test_defprimitive_alias(self):
        '''Check "float" maps directly to "float" when matching'''
        self._check('''
            defprimitive float float 4;
        ''', ''' ''')

    def test_defprimitive_alias_conflict(self):
        '''Check "float" is wrapped when not when not matching'''
        self._check('''
            defprimitive float float 8;
        ''', '''
            typedef double blobc_c_wrap_float;
        ''')

    def test_struct_empty(self):
        self._check('''
            struct Foo { };
        ''', '''
            struct Foo_TAG;
            typedef struct Foo_TAG { } Foo;
        ''')

    def test_struct_single_member(self):
        self._check('''
            struct Foo {
                u32 Bar;
            };
        ''', '''
            struct Foo_TAG;
            typedef struct Foo_TAG { u32 Bar; } Foo;
        ''')

    def test_struct_tag_option_empty(self):
        self._check('''
            generator c : struct_suffix("")
            struct Foo {
                u32 Bar;
            };
        ''', '''
            struct Foo;
            typedef struct Foo { u32 Bar; } Foo;
        ''')

    def test_struct_tag_option(self):
        self._check('''
            generator c : struct_suffix("^^^")
            struct Foo {
                u32 Bar;
            };
        ''', '''
            struct Foo^^^;
            typedef struct Foo^^^ { u32 Bar; } Foo;
        ''')

    def test_error_duplicate_member(self):
        with self.assertRaises(TypeSystemException):
            self._compile('''
                struct Foo {
                    u8 Bar;
                    u8 Bar;
                };
            ''')

    def test_error_duplicate_struct(self):
        with self.assertRaises(TypeSystemException):
            self._compile('''
                struct Foo {}
                struct Foo { u8 Bar; }
            ''')

    def test_error_duplicate_type_enum(self):
        with self.assertRaises(TypeSystemException):
            self._compile('''
                enum Foo { A = 7 }
                enum Foo { B = 7 }
            ''')

    def test_error_duplicate_type(self):
        with self.assertRaises(TypeSystemException):
            self._compile('''
                enum Foo { A = 7 }
                struct Foo { u8 Bar; }
            ''')

    def test_array_simple(self):
        self._check('''
            struct Foo {
                u32[7] Bar;
            };
        ''', '''
            struct Foo_TAG;
            typedef struct Foo_TAG { u32 Bar[7]; } Foo;
        ''')

    def test_array_multi(self):
        self._check('''
            struct Foo {
                u32[1,2,3] Bar;
            };
        ''', '''
            struct Foo_TAG;
            typedef struct Foo_TAG { u32 Bar[1][2][3]; } Foo;
        ''')

    def test_array_ptr(self):
        self._check('''
            struct Foo {
                u32**[2] Bar;
            };
        ''', '''
            struct Foo_TAG;
            typedef struct Foo_TAG { u32** Bar[2]; } Foo;
        ''')

    def test_cstring(self):
        self._check('''
            struct Foo {
                __cstring<char> Bar;
            };
        ''', '''
            struct Foo_TAG;
            typedef struct Foo_TAG { char* Bar; } Foo;
        ''')

    def test_cstring_ptr(self):
        self._check('''
            struct Foo {
                __cstring<char>* Bar;
            };
        ''', '''
            struct Foo_TAG;
            typedef struct Foo_TAG { char** Bar; } Foo;
        ''')

    def test_cstring_array(self):
        self._check('''
            struct Foo {
                __cstring<char>[20] Bar;
            };
        ''', '''
            struct Foo_TAG;
            typedef struct Foo_TAG { char* Bar[20]; } Foo;
        ''')

    def test_cdecl_option(self):
        self._check('''
            struct Foo {
                void* Bar : c_decl("struct SomeOtherType* Frob");
            };
        ''', '''
            struct Foo_TAG;
            typedef struct Foo_TAG { struct SomeOtherType* Frob; } Foo;
        ''')

    def test_struct_containment(self):
        self._check('''
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
        ''', '''
            struct Baz_TAG;
            struct Bar_TAG;
            struct Foo_TAG;
            typedef struct Baz_TAG { u32 a; u32 b; } Baz;
            typedef struct Bar_TAG { struct Baz_TAG a; } Bar;
            typedef struct Foo_TAG { struct Bar_TAG a[2]; } Foo;
        ''')

    def test_indent_spaces(self):
        out = self._compile(one_of_each + ' generator c : indent_style("spaces");', keep_ws=True)
        self.assertTrue(out.find('\t') == -1)

    def test_indent_tabs(self):
        out = self._compile(one_of_each + ' generator c : indent_style("tabs");', keep_ws=True)
        self.assertTrue(out.find('    ') == -1)

    def test_bad_indent(self):
        with self.assertRaises(blobc.ParseError):
            self._compile(one_of_each + ' generator c : indent_style("both");')

    def test_brace_k_r(self):
        self._compile(one_of_each + ' generator c : brace_style("k&r");', keep_ws=True)

    def test_brace_newline(self):
        self._compile(one_of_each + ' generator c : brace_style("newline");', keep_ws=True)

    def test_bad_brace(self):
        with self.assertRaises(blobc.ParseError):
            self._compile(one_of_each + ' generator c : brace_style("something else");', keep_ws=True)

    def test_emit_user_literals(self):
        self._check('generator c : emit("should print");', 'should print', no_primitives=True)

    def test_dont_emit_imported_user_literals(self):
        self._check('import "foo";', '', imports={
            'foo': 'generator c : emit("should not print");'
        })

    def test_include_imports(self):
        self._check('import "foo";', '', imports={
            'foo': 'iconst a = 7;'
        }, expect_includes=['"foo.h"'])

    def test_dont_emit_imported_struct(self):
        self._check('import "foo";', '', imports={
            'foo': 'struct Foo { u32 Field; };'
        }, print_includes=False)

    def test_dont_emit_imported_primitive(self):
        self._check('import "foo";', '', imports={
            'foo': 'defprimitive torsk uint 1;'
        }, print_includes=False)

    def test_dont_emit_imported_enum(self):
        self._check('import "foo";', '', imports={
            'foo': 'enum torsk { A, B };'
        }, print_includes=False)

    def test_include_guard(self):
        out = self._compile('',include_guard=True, no_primitives=True)
        self.assertTrue(out.find('#ifndef') != -1)
        self.assertTrue(out.find('#define') != -1)
        self.assertTrue(out.find('#endif') != -1)

    def test_separators(self):
        d = self._compile('struct Foo { void* Bar; }', include_guard=True, no_primitives=True, separators=True)
        self.assertTrue(d.count('/*') > 0)

    def test_inttypes_hdr(self):
        self._check('', '#include <inttypes.h>', no_primitives=True, inttypes=True)

    def test_no_wide_char_yet(self):
        with self.assertRaises(blobc.codegen.GeneratorException):
            self._compile('defprimitive fisk character 2;', no_primitives=True, inttypes=True)
