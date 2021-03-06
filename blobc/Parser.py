#! /usr/bin/env python

import re
import os.path
from ParseTree import *

SCANNER = re.compile(r'''
  (\s+)                             | # whitespace
  (//)[^\n]*                        | # comments
  0[xX]([0-9A-Fa-f]+)               | # hexadecimal integer literals
  (\d+)                             | # integer literals
  (<<|>>)                           | # multi-char punctuation
  ([][(){}<>=,;:*+-/])              | # punctuation
  ([A-Za-z_][A-Za-z0-9_]*)          | # identifiers
  """(.*?)"""                       | # multi-line string literal
  "((?:[^"\n\\]|\\.)*)"             | # regular string literal
  (.)                                 # an error!
  ''', re.DOTALL | re.VERBOSE);

TOK_EOF = -1
TOK_WORD = 1
TOK_INT = 2
TOK_PUNCT = 3
TOK_STRING = 4

class ParseError(Exception):
    def __init__(self, filename, lineno, msg):
        self.filename = filename
        self.lineno = lineno
        self.msg = msg

    def __str__(self):
        return '%s(%d): %s' % (self.filename, self.lineno, self.msg)

class Tokenizer(object):
    def __init__(self, filename, data, is_import):
        object.__init__(self)
        self.filename = filename
        self.lineno = 1
        self.is_import = is_import 
        self.pos = 1
        self.data = data
        self.titer = re.finditer(SCANNER, self.data)
        self.cache = None
        self._loc = None

    def next(self):
        self._loc = None

        if self.cache is not None:
            r = self.cache
            self.cache = None
            return r

        while True:
            m = None
            try:
                m = self.titer.next()
            except StopIteration:
                return TOK_EOF, None

            space, comment, hexint, integer, mpunct, \
            punct, word, mstringlit, stringlit, badchar \
                = m.groups()

            if space is not None:
                self.lineno += space.count('\n')
                continue

            if word is not None:
                return TOK_WORD, word

            if integer is not None:
                return TOK_INT, int(integer)

            if hexint is not None:
                return TOK_INT, int(hexint, 16)

            if comment is not None:
                continue

            if mpunct is not None:
                return TOK_PUNCT, mpunct

            if punct is not None:
                return TOK_PUNCT, punct

            if stringlit is not None:
                return TOK_STRING, stringlit

            if mstringlit is not None:
                self.lineno += mstringlit.count('\n')
                return TOK_STRING, mstringlit

            raise ParseError(self.filename, self.lineno, 'bad token char: "%s"' % (badchar))

    def describe_here(self):
        t, v = self.peek()
        return self.describe(t, v)

    def describe(self, t, v):
        if t == TOK_EOF:
            return '<end of file>'
        elif t == TOK_WORD:
            if v is not None:
                return 'identifier "%s"' % (v)
            else:
                return 'identifier'
        elif t == TOK_INT:
            if v is not None:
                return "integer %d" % (v)
            else:
                return 'integer'
        elif t == TOK_STRING:
            if v is not None:
                return 'string literal "%s"' % (v)
            else:
                return 'string literal'
        else:
            assert t == TOK_PUNCT
            assert v is not None
            return "'%s'" % (v)

    def peek(self):
        if self.cache is None:
            self.cache = self.next()
        return self.cache

    def loc(self):
        if self._loc is None:
            self._loc = SourceLocation(self.filename, self.lineno, self.is_import)
        return self._loc

class Parser(object):
    def __init__(self, tokenizer):
        object.__init__(self)
        self.tokenizer = tokenizer
        self._current_enum_name = None
        self._prev_enum_member = None

    def error(self, msg):
        raise ParseError(self.tokenizer.filename, self.tokenizer.lineno, msg)

    def accept(self, tt, tv=None):
        return self.accept_v(tt, tv)[0]

    def accept_v(self, tt, tv=None):
        t, v = self.tokenizer.peek()
        if t == tt and (tv is None or tv == v):
            self.tokenizer.next()
            return True, v
        else:
            return False, None

    def expect(self, tt, tv=None):
        t, v = self.tokenizer.next()
        if t != tt:
            self.error('expected %s but got %s' %
                    (self.tokenizer.describe(tt, tv), self.tokenizer.describe(t, v)))
        return v

    def expect_any(self, *tts):
        t, v = self.tokenizer.next()
        if t not in tts:
            self.error('expected %s but got %s' %
                    (', '.join([self.tokenizer.describe(x, None) for x in tts]),
                     self.tokenizer.describe(t, v)))
        return t, v

    def repeat(self, rule, end_tok, end_val=None):
        result = []
        while True:
            t, v = self.tokenizer.peek()
            if t == end_tok and (end_val is None or end_val == v):
                return result
            result.append(self.require(rule))
        return result

    def require(self, rule):
        v = rule()
        if v is None:
            self.error("expected %s at this point" % (rule.__name__[2:]))
        return v

    def sep_nonempy_list(self, rule, sep, allow_trailing=False):
        result = [ self.require(rule) ]
        if allow_trailing:
            # e.g. "a,b,c," is accepted
            while self.accept(TOK_PUNCT, sep):
                v = rule()
                if v is None:
                    break # we just ate the trailing separator
                else:
                    result.append(v)
        else:
            while self.accept(TOK_PUNCT, sep):
                result.append(self.require(rule))
        return result

    def alt(self, *rules):
        for r in rules:
            v = r()
            if v: return v

        tokdesc = self.tokenizer.describe_here()
        rules = ', '.join(["'%s'" % (r.__name__[2:]) for r in rules])

        self.error("no matching alternative; have %s but only one of %s is acceptable" %
                (tokdesc, rules))

    def r_type(self):
        loc = self.tokenizer.loc()
        name = self.expect(TOK_WORD)
        if name == 'void':
            t = RawVoidType.instance
        elif name == '__cstring':
            self.expect(TOK_PUNCT, '<')
            char_type = self.r_type()
            self.expect(TOK_PUNCT, '>')
            t = RawPointerType(char_type, loc, is_cstring=True)
        else:
            t = RawSimpleType(name, loc)

        while True:
            loc = self.tokenizer.loc()
            if self.accept(TOK_PUNCT, '*'):
                t = RawPointerType(t, loc)
            elif self.accept(TOK_PUNCT, '['):
                dims = self.sep_nonempy_list(self.r_expr, ',')
                t = RawArrayType(t, dims, loc)
                self.expect(TOK_PUNCT, ']')
            else:
                break

        if t is RawVoidType.instance:
            self.error("void type is not instantiatable")
        return t

    def r_struct_member(self):
        loc = self.tokenizer.loc()
        t = self.r_type()
        n = self.expect(TOK_WORD)
        if self.accept(TOK_PUNCT, ':'):
            options = self.sep_nonempy_list(self.r_named_option, ',')
        else:
            options = []
        self.expect(TOK_PUNCT, ';')
        r = RawStructMember(t, n, options, loc)
        return r

    def r_option_param(self):
        loc = self.tokenizer.loc()

        has_key, key = self.accept_v(TOK_WORD)

        if has_key:
            if self.accept(TOK_PUNCT, '='):
                # this is a key=value type parameter
                _, value = self.expect_any(TOK_INT, TOK_WORD, TOK_STRING)
                return RawOptionParam(key, value, loc)
            else:
                return RawOptionParam(None, key, loc)
        else:
            has_string, string = self.accept_v(TOK_STRING)
            if has_string:
                return RawOptionParam(None, string, loc)

            has_int, intv = self.accept_v(TOK_INT)
            if has_int:
                return RawOptionParam(None, intv, loc)

            return None
        
    def r_named_option(self):
        if self.tokenizer.peek()[0] != TOK_WORD:
            return None

        loc = self.tokenizer.loc()
        optname = self.expect(TOK_WORD)

        if self.accept(TOK_PUNCT, '('):
            params = self.sep_nonempy_list(self.r_option_param, ',')
            self.expect(TOK_PUNCT, ')')
        else:
            params = []

        return RawNamedOption(optname, params, loc)

    def r_struct(self):

        if not self.accept(TOK_WORD, 'struct'):
            return None

        loc = self.tokenizer.loc()

        name = self.expect(TOK_WORD)

        if self.accept(TOK_PUNCT, ':'):
            options = self.sep_nonempy_list(self.r_named_option, ',')
        else:
            options = []

        self.expect(TOK_PUNCT, '{')
        members = self.repeat(self.r_struct_member, TOK_PUNCT, '}')
        self.expect(TOK_PUNCT, '}')
        self.accept(TOK_PUNCT, ';')
        return RawStructType(name, members, options, loc)

    def r_defprimitive(self):
        loc = self.tokenizer.loc()
        if not self.accept(TOK_WORD, 'defprimitive'):
            return None
        name = self.expect(TOK_WORD)
        pclass = self.expect(TOK_WORD)
        size = self.expect(TOK_INT)

        if self.accept(TOK_PUNCT, ':'):
            options = self.sep_nonempy_list(self.r_named_option, ',')
        else:
            options = []

        # sanity check the data
        if pclass in ('sint', 'uint'):
            if size not in (1, 2, 4, 8):
                self.error('unsupported integer size %d; 1, 2, 4 and 8 supported' % (size))
        elif pclass == 'character':
            if size not in (1, 2, 4):
                self.error('unsupported character size %d; 1, 2 and 4 supported' % (size))
        elif pclass == "float":
            if size not in (4, 8):
                self.error('unsupported floating-point primitive size %d; 4 and 8 supported' % (size))
        else:
            self.error('unsupported primitive class %s; sint, uint, character and float supported' % (pclass))

        self.accept(TOK_PUNCT, ';')

        return RawDefPrimitive(name, pclass, size, options, loc)

    def r_enum_member(self):
        if self.tokenizer.peek()[0] != TOK_WORD:
            return None

        loc = self.tokenizer.loc()
        name = self.expect(TOK_WORD)
        if self.accept(TOK_PUNCT, '='):
            # the value is initialized, parse an arbitrary expression
            expr = self.require(self.r_expr)
        elif self._prev_enum_member is not None:
            # express the initializer as the previous field + 1
            prev_name = self._prev_enum_member.name
            expr = RawAddExpr(loc, RawNamedConstantExpr(loc, prev_name), RawIntLiteralExpr(loc, 1))
        else:
            # this is the first field, which starts at zero.
            expr = RawIntLiteralExpr(loc, 0)

        result = RawEnumMember(name, expr, loc)
        self._prev_enum_member = result
        return result

    def r_enum(self):
        loc = self.tokenizer.loc()
        if not self.accept(TOK_WORD, 'enum'):
            return None

        name = self.expect(TOK_WORD)
        self._current_enum_name = name

        self.expect(TOK_PUNCT, '{')

        members = self.sep_nonempy_list(self.r_enum_member, ',', allow_trailing=True);
        self._prev_enum_member = None

        self.expect(TOK_PUNCT, '}')
        self.accept(TOK_PUNCT, ';')

        return RawEnumType(name, members, loc)

    def r_import(self):
        loc = self.tokenizer.loc()
        if not self.accept(TOK_WORD, 'import'):
            return None
        filename = self.expect(TOK_STRING);
        self.accept(TOK_PUNCT, ';')
        return RawImportStmt(filename, loc)

    def r_generator_config(self):
        loc = self.tokenizer.loc()
        if not self.accept(TOK_WORD, 'generator'):
            return None
        generator_name = self.expect(TOK_WORD)
        self.expect(TOK_PUNCT, ':')
        options = self.sep_nonempy_list(self.r_named_option, ',')
        self.accept(TOK_PUNCT, ';')
        return GeneratorConfig(generator_name, options, loc)

    def _binop_expr(self, types, subrule):
        v = self.require(subrule)
        while True:
            loc = self.tokenizer.loc()
            found = False
            for t in types:
                if self.accept(TOK_PUNCT, t.TOKEN):
                    rhs = self.require(subrule)
                    v = t(loc, v, rhs)
                    found = True
                    break
            if not found:
                return v

    def r_primary_expr(self):
        loc = self.tokenizer.loc()
        ok, val = self.accept_v(TOK_INT)
        if ok:
            return RawIntLiteralExpr(loc, val)

        if self.accept(TOK_PUNCT, '('):
            val = self.require(self.r_expr)
            self.expect(TOK_PUNCT, ')')
            return val

        ok, val = self.accept_v(TOK_WORD)
        if ok:
            while self.accept(TOK_PUNCT, '.'):
                val = val + '.' + self.expect(TOK_WORD)
            return RawNamedConstantExpr(loc, val)

        if self.accept(TOK_PUNCT, '-'):
            expr = self.require(self.r_primary_expr)
            return RawNegateExpr(loc, expr)

        tokdesc = self.tokenizer.describe_here()
        raise ParseError(
                loc.filename, loc.lineno,
                "expected int, (expr), name or -expr at this point, have: " + tokdesc)

    SHIFT_TYPES = (RawShiftLeftExpr, RawShiftRightExpr)
    ADD_TYPES = (RawAddExpr, RawSubExpr)
    MUL_TYPES = (RawMulExpr, RawDivExpr)

    def r_shift_expr(self):
        return self._binop_expr(Parser.SHIFT_TYPES, self.r_add_expr)

    def r_add_expr(self):
        return self._binop_expr(Parser.ADD_TYPES, self.r_mul_expr)

    def r_mul_expr(self):
        return self._binop_expr(Parser.MUL_TYPES, self.r_primary_expr)

    def r_expr(self):
        return self.r_shift_expr()

    def r_iconst(self):
        loc = self.tokenizer.loc()
        if not self.accept(TOK_WORD, 'iconst'):
            return None
        name = self.expect(TOK_WORD)
        self.expect(TOK_PUNCT, '=')
        value = self.r_expr()
        self.accept(TOK_PUNCT, ';')
        return RawConstant(name, value, loc)

    def r_toplevel(self):
        return self.alt(
                self.r_struct,
                self.r_defprimitive,
                self.r_enum,
                self.r_iconst,
                self.r_import,
                self.r_generator_config)

    def r_unit(self):
        return self.repeat(self.r_toplevel, TOK_EOF)

class DefaultImportHandler:
    def __init__(self, dirs):
        self._dirs = dirs

    def get_import_contents(self, fn):
        with open(fn, 'r') as f:
            return f.read()

    def find_imported_file(self, fn):
        for d in self._dirs:
            fpath = os.path.normpath(os.path.join(d, fn))
            if os.path.exists(fpath):
                return fpath
        return None


class ParseContext(object):
    def __init__(self, handle_imports, import_handler):
        assert import_handler
        self._import_dirs=('.')
        self._import_memo={}
        self._import_handler = import_handler
        self._handle_imports = handle_imports

    def _load_file(self, fn):
        self._import_memo[fn] = True
        return self._import_handler.get_import_contents(fn)

    def parse(self, fn, is_import=False):
        data = self._load_file(fn)
        tokenizer = Tokenizer(fn, data, is_import)
        parser = Parser(tokenizer)
        result = parser.r_unit()

        if not self._handle_imports:
            return result

        iresult = []
        for r in result:
            if isinstance(r, RawImportStmt):
                imported_fn = self._import_handler.find_imported_file(r.filename)
                if not imported_fn:
                    raise ParseError(
                            r.location.filename,
                            r.location.lineno,
                            "couldn't find '%s' in any of [%s]" %
                                (r.filename, ', '.join(self._import_dirs)))
                if not self._import_memo.has_key(imported_fn):
                    # todo: should make an effort of using real absolute names here
                    iresult.extend(self.parse(imported_fn, is_import=True))
            else:
                iresult.append(r)
        return iresult

class StringImportHandler:
    def __init__(self, s):
        self._s = s

    def get_import_contents(self, fn):
        s = self._s
        self._s = None
        return s

    def find_imported_file(self, fn):
        return '<string>' if self._s is not None else None

def parse_string(string):
    import_handler = StringImportHandler(string)
    ctx = ParseContext(False, import_handler)
    return ctx.parse('<string>')

def parse_file(fn, handle_imports=True, import_handler=None, import_dirs=None):
    if import_handler is None:
        import_handler = DefaultImportHandler(import_dirs or ('.',))
    ctx = ParseContext(handle_imports, import_handler)
    return ctx.parse(fn)

if __name__ == '__main__':
    import sys
    parse_file(sys.argv[1])
