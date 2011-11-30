
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

    class ImportHandler:
        def __init__(self, files):
            self._files = files
        def get_import_contents(self, fn):
            return self._files[fn]
        def find_imported_file(self, fn):
            return fn if self._files.has_key(fn) else None

    class Data:
        def __init__(self, src, **kws):
            imports = kws.get('imports', {})
            if kws.get('comments', False) == False:
                src = 'generator m68k : no_comments;\n' + src

            equ_label = kws.get('equ_label', 'equ')
            if equ_label != 'EQU':
                src = ('generator m68k : equ_label("%s");\n' % (equ_label)) + src
                
            imports['<string>'] = src
            self.parse_tree = blobc.parse_file(
                    '<string>', handle_imports=True,
                    import_handler=TestCodeGen_M68K.ImportHandler(imports))
            self.tsys = blobc.compile_types(self.parse_tree)
            out_fh = StringIO()
            aux_fh = StringIO()
            self.gen = M68kGenerator(out_fh, 'input.blob', aux_fh, 'output.h')
            self.gen.generate_code(self.parse_tree, self.tsys)
            self.output = compress_c(out_fh.getvalue())
            self.aux_output = compress_c(aux_fh.getvalue())

    def _check(self, src, expected, **kws):
        d = type(self).Data(src, **kws)
        self.assertEqual(compress_c(expected), d.output)

    def _get_output(self, src, **kws):
        d = type(self).Data(src, **kws)
        return d.output

    def test_constant1(self):
        d = self._check('''iconst foo = 7;''', '''foo equ 7''')

    def test_constant2(self):
        d = self._check('''iconst foo = 7 + 9;''', '''foo equ 16''')

    def test_constant3(self):
        d = self._check('''iconst foo = 7 / 9;''', '''foo equ 0''')

    def test_constant4(self):
        d = self._check('''iconst foo = 1 << 8;''', '''foo equ 256''')

    def test_constant4_1(self):
        d = self._check('''iconst foo = 256 >> 8;''', '''foo equ 1''')

    def test_constant5(self):
        d = self._check('''
            iconst foo = 17;
            iconst bar = 10 * foo;
        ''', '''
            foo equ 17
            bar equ 170
        ''')
 
    def test_imported_data(self):
        d = self._check('''
            import "imports.blob";
        ''', '''
            INCLUDE "imports.blob.i"
        ''', imports = {
            'imports.blob' : '''
                enum A { B = 0, C = 77 };
                struct B { A a; }
                '''
        })

    def test_comments(self):
        d = self._get_output('''
            generator m68k : emit("foo");
            enum A { B = 0, C = 77 };
            struct B { A a; }
            iconst C = A.B;
        ''', comments=True)
        self.assertNotEqual(d.find(';'), -1)

    def test_enum(self):
        d = self._check('''
            enum A { B = 0, C = 77 };
        ''', '''
            A_B equ 0
            A_C equ 77
        ''')

    def test_struct_empty(self):
        d = self._check('''
            struct Foo { };
        ''', '''
            Foo_SIZE equ 0
            Foo_ALIGN equ 1
        ''')

    def test_struct_single_member(self):
        d = self._check(stdprim + '''
            struct Foo {
                u32 Bar;
            };
        ''', '''
            Foo_Bar equ 0
            Foo_SIZE equ 4
            Foo_ALIGN equ 4
        ''')

    def test_sizeof_suffix(self):
        d = self._check(stdprim + '''
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
        d = self._check(stdprim + '''
            struct Foo {
                u32[4] Bar;
            };
        ''', '''
            Foo_Bar equ 0
            Foo_SIZE equ 16 
            Foo_ALIGN equ 4 
        ''')

    def test_array_multi(self):
        d = self._check(stdprim + '''
            struct Foo {
                u32[1,2,3] Bar;
            };
        ''', '''
            Foo_Bar equ 0
            Foo_SIZE equ 24 
            Foo_ALIGN equ 4 
        ''')

    def test_field_rename(self):
        d = self._check(stdprim + '''
            struct Foo {
                u32[1,2,3] Bar : m68k_name("Qux");
            };
        ''', '''
            Qux equ 0
            Foo_SIZE equ 24 
            Foo_ALIGN equ 4 
        ''')

    def test_import(self):
        d = self._check('''
            import "Foo.blob";
        ''', '''
            INCLUDE "Foo.blob.i"
        ''', imports={
            'Foo.blob': 'iconst a = 7;',
        })

    def test_import_suffix(self):
        d = self._check('''
            generator m68k : include_suffix(".fisk");
            import "Foo.blob";
        ''', '''
            INCLUDE "Foo.blob.fisk"
        ''', imports={
            'Foo.blob': 'iconst a = 7;\n',
        })

    def test_missing_import(self):
        with self.assertRaises(blobc.ParseError):
            d = self._check('''
                import "missing_file.blob";
            ''', '''''')

    def test_user_emit(self):
        d = self._check('''
            generator m68k : emit("blah");
        ''', '''
            blah
        ''')

    def test_user_emit_multiline(self):
        d = self._check('''
            generator m68k : emit("""
                blah
                blah
            """);
        ''', '''
            blah blah
        ''')

    def test_bad_token(self):
        with self.assertRaises(blobc.ParseError):
            d = self._get_output('''
            ^
            ''')

    def test_bad_option(self):
        with self.assertRaises(blobc.ParseError):
            d = self._get_output('''
                generator m68k : nonexisting_option("blah");
            ''')

    def test_bad_option_param(self):
        with self.assertRaises(blobc.ParseError):
            d = self._get_output('''
                generator m68k : emit(foo=bar);
            ''')

    def test_div_by_zero(self):
        with self.assertRaises(blobc.ParseError):
            d = self._get_output('''
                iconst b = 1;
                iconst a = 7 / (b - 1);
            ''')
