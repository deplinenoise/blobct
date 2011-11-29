import blobc
import unittest
from blobc.ParseTree import *
from blobc.Parser import ParseError
from blobc.Typesys import TypeSystemException

class TestParser(unittest.TestCase):

    def _testprim(self, name, pclass, size):
        parse_tree = blobc.parse_string("defprimitive %s %s %d\n" % (name, pclass, size))
        self.assertEqual(len(parse_tree), 1)
        self.assertEqual(type(parse_tree[0]), RawDefPrimitive)
        self.assertEqual(parse_tree[0].name, name)
        self.assertEqual(parse_tree[0].pclass, pclass)
        self.assertEqual(parse_tree[0].size, size)

    def test_signed_int(self):
        for size in (1, 2, 4, 8):
            self._testprim("foo", "sint", size)

    def test_unsigned_int(self):
        for size in (1, 2, 4, 8):
            self._testprim("bar", "uint", size)

    def test_character(self):
        for size in (1, 2, 4):
            self._testprim("bar", "character", size)

    def test_float(self):
        for size in (4, 8):
            self._testprim("bar", "float", size)

    def test_illegal_sizes(self):
        self.assertRaises(ParseError, self._testprim, "foo", "sint", 3)
        self.assertRaises(ParseError, self._testprim, "foo", "uint", 9)
        self.assertRaises(ParseError, self._testprim, "foo", "float", 1)
        self.assertRaises(ParseError, self._testprim, "foo", "character", 8)
        self.assertRaises(ParseError, self._testprim, "foo", "sint", -1)

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
        self.assertIsInstance(p[0].members[0].type, RawPointerType)

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
        self.assertIsInstance(p[0], RawDefPrimitive)
        self.assertIsInstance(p[1], RawStructType)

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
        self.assertEqual(len(p[0].members), 1)
        self.assertEqual(p[0].members[0].name, 'bar')
        self.assertEqual(p[0].members[0].expr.value, 0)

    def test_enum_single_trailing_comma(self):
        p = blobc.parse_string("""
            enum foo {
                bar,
                }""")
        self.assertEqual(len(p), 1)
        self.assertEqual(len(p[0].members), 1)
        self.assertEqual(p[0].members[0].name, 'bar')
        self.assertEqual(p[0].members[0].expr.value, 0)

    def test_enum_double(self):
        p = blobc.parse_string("""
            enum foo {
                bar, baz
                }""")
        self.assertEqual(len(p), 1)
        self.assertEqual(len(p[0].members), 2)
        self.assertEqual(p[0].members[0].name, 'bar')
        self.assertEqual(p[0].members[1].name, 'baz')

    def test_enum_assigned(self):
        p = blobc.parse_string("""
            enum foo {
                bar = 7, baz = 7
                }""")
        self.assertEqual(len(p), 1)
        self.assertEqual(type(p[0]), RawEnumType)
        self.assertEqual(len(p[0].members), 2)
        self.assertEqual(p[0].members[0].name, 'bar')
        self.assertEqual(p[0].members[0].expr.value, 7)
        self.assertEqual(p[0].members[1].name, 'baz')

    def test_option_bare(self):
        p = blobc.parse_string("""struct foo : fiskrens { }""")
        foo = p[0]
        options = foo.get_options('fiskrens')
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].name, "fiskrens")
        self.assertEqual(len(options[0].pos_params), 0)

    def test_option_one_param_no_value(self):
        p = blobc.parse_string("""struct foo : fiskrens("bar") { }""")
        foo = p[0]
        options = foo.get_options('fiskrens')
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].name, "fiskrens")
        self.assertEqual(len(options[0].pos_params), 1)
        self.assertEqual(options[0].pos_params[0], "bar")
    
    def test_option_one_param_with_value(self):
        p = blobc.parse_string("""struct foo : fiskrens(bar=yep) { }""")
        foo = p[0]
        options = foo.get_options('fiskrens')
        self.assertEqual(len(options), 1)
        self.assertEqual(options[0].name, "fiskrens")
        self.assertEqual(len(options[0].pos_params), 0)
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
        self.assertEqual(len(options[0].pos_params), 1)
        self.assertEqual(options[0].pos_params[0], "foo")
        self.assertEqual(options[0].kw_param("bar"), 89)
        self.assertEqual(options[0].kw_param("baz"), "tjoho")

        options = foo.get_options("qux")
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0].name, "qux")
        self.assertEqual(len(options[0].pos_params), 0)

        self.assertEqual(options[1].name, "qux")
        self.assertEqual(len(options[1].pos_params), 0)
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
        self.assertEqual(len(options[0].pos_params), 0)

        options = m0.get_options('bar')
        self.assertEqual(len(options), 1)
        self.assertEqual(len(options[0].pos_params), 1)
        self.assertEqual(options[0].pos_params[0], "foo")
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

    def test_cstring_subtype(self):
        p = blobc.parse_string('''struct foo {
                __cstring<char>[4] a;
        }''')
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0].name, "foo")
        self.assertEqual(len(p[0].members), 1)
        m0 = p[0].members[0]
        self.assertIsInstance(m0.type, RawArrayType)
        bt = m0.type.basetype
        self.assertIsInstance(bt, RawPointerType)
        self.assertTrue(bt.is_cstring)

    def test_const(self):
        p = blobc.parse_string('''
        iconst a = 7;
        ''')
        self.assertEqual(len(p), 1)
        self.assertIsInstance(p[0], RawConstant)
        self.assertEqual(p[0].name, "a")
        self.assertIsInstance(p[0].expr, RawIntLiteralExpr)
        self.assertEqual(p[0].expr.value, 7)

    def test_unary_neg(self):
        p = blobc.parse_string('''iconst a = -7''')
        self.assertIsInstance(p[0], RawConstant)
        self.assertIsInstance(p[0].expr, RawNegateExpr)
        self.assertIsInstance(p[0].expr.expr, RawIntLiteralExpr)
        self.assertEqual(p[0].expr.expr.value, 7)

    def _do_binop(self, optype, opstr):
        p = blobc.parse_string("iconst a = b %s 1;" % (opstr))
        self.assertIsInstance(p[0].expr, optype)
        self.assertIsInstance(p[0].expr.lhs, RawNamedConstantExpr)
        self.assertIsInstance(p[0].expr.rhs, RawIntLiteralExpr)

    def test_expr_binop1(self): self._do_binop(RawAddExpr, '+')
    def test_expr_binop2(self): self._do_binop(RawSubExpr, '-')
    def test_expr_binop3(self): self._do_binop(RawMulExpr, '*')
    def test_expr_binop4(self): self._do_binop(RawDivExpr, '/')
    def test_expr_binop5(self): self._do_binop(RawShiftLeftExpr, '<<')
    def test_expr_binop6(self): self._do_binop(RawShiftRightExpr, '>>')

    def test_precedence1(self):
        p = blobc.parse_string('''
        iconst a = 7 * 2 + 5;
        ''')
        self.assertIsInstance(p[0], RawConstant)
        self.assertIsInstance(p[0].expr, RawAddExpr)
        self.assertIsInstance(p[0].expr.lhs, RawMulExpr)
        self.assertIsInstance(p[0].expr.rhs, RawIntLiteralExpr)

    def test_precedence2(self):
        p = blobc.parse_string('''
        iconst a = 7 + 2 * 5;
        ''')
        self.assertIsInstance(p[0], RawConstant)
        self.assertIsInstance(p[0].expr, RawAddExpr)
        self.assertIsInstance(p[0].expr.lhs, RawIntLiteralExpr)
        self.assertIsInstance(p[0].expr.rhs, RawMulExpr)

    def test_precedence3(self):
        p = blobc.parse_string('''
        iconst a = (7 + 2) * 5;
        ''')
        self.assertIsInstance(p[0], RawConstant)
        self.assertIsInstance(p[0].expr, RawMulExpr)
        self.assertIsInstance(p[0].expr.lhs, RawAddExpr)
        self.assertIsInstance(p[0].expr.rhs, RawIntLiteralExpr)

    def test_complex(self):
        p = blobc.parse_string('''
        iconst a = foo << -x + (y << a * b)
        ''')
        self.assertIsInstance(p[0], RawConstant)
        self.assertIsInstance(p[0].expr, RawShiftLeftExpr)

        self.assertIsInstance(p[0].expr.lhs, RawNamedConstantExpr)
        self.assertEqual(p[0].expr.lhs.name, "foo")

        self.assertIsInstance(p[0].expr.rhs, RawAddExpr)
        self.assertIsInstance(p[0].expr.rhs.lhs, RawNegateExpr)
        self.assertIsInstance(p[0].expr.rhs.lhs.expr, RawNamedConstantExpr)
        self.assertEqual(p[0].expr.rhs.lhs.expr.name, 'x')

        self.assertIsInstance(p[0].expr.rhs.rhs, RawShiftLeftExpr)
        self.assertIsInstance(p[0].expr.rhs.rhs.lhs, RawNamedConstantExpr)
        self.assertEqual(p[0].expr.rhs.rhs.lhs.name, 'y')

        self.assertIsInstance(p[0].expr.rhs.rhs.rhs, RawMulExpr)
        self.assertIsInstance(p[0].expr.rhs.rhs.rhs.lhs, RawNamedConstantExpr)
        self.assertEqual(p[0].expr.rhs.rhs.rhs.lhs.name, 'a')
        self.assertIsInstance(p[0].expr.rhs.rhs.rhs.rhs, RawNamedConstantExpr)
        self.assertEqual(p[0].expr.rhs.rhs.rhs.rhs.name, 'b')

