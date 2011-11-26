#! /usr/bin/env python

import re
from ParseTree import *

SCANNER = re.compile(r'''
  (\s+)                             | # whitespace
  (//)[^\n]*                        | # comments
  ([+-]?\d+)                        | # integer literals
  ([][(){}=,;:*])                   | # punctuation
  ([A-Za-z_][A-Za-z0-9_]*)          | # identifiers
  "((?:[^"\n\\]|\\.)*)"             | # string literal
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
        self.__loc = None

    def next(self):
        self.__loc = None

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

            space, comment, integer, punct, word, stringlit, badchar = m.groups()

            if space is not None:
                self.lineno += space.count('\n')
                continue

            if comment is not None:
                continue

            if integer is not None:
                return TOK_INT, int(integer)

            if punct is not None:
                return TOK_PUNCT, punct

            if stringlit is not None:
                return TOK_STRING, stringlit

            if word is not None:
                return TOK_WORD, word

            raise ParseError(self.filename, self.lineno, 'bad token char: "%s"' % (badchar))

    def describe_here(self):
        t, v = self.peek()
        return describe(t, v)

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
            return "'%s'" % (v)

    def peek(self):
        if self.cache is None:
            self.cache = self.next()
        return self.cache

    def loc(self):
        if self.__loc is None:
            self.__loc = SourceLocation(self.filename, self.lineno, self.is_import)
        return self.__loc

class Parser(object):
    def __init__(self, tokenizer):
        object.__init__(self)
        self.tokenizer = tokenizer

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

    def r_arraydim(self):
        return self.expect(TOK_INT)

    def r_type(self):
        loc = self.tokenizer.loc()
        name = self.expect(TOK_WORD)
        if name == 'void':
            t = RawVoidType.instance
        else:
            t = RawSimpleType(name, loc)

        while True:
            if self.accept(TOK_PUNCT, '*'):
                loc = self.tokenizer.loc()
                t = RawPointerType(t, loc)
            elif self.accept(TOK_PUNCT, '['):
                loc = self.tokenizer.loc()
                dims = self.sep_nonempy_list(self.r_arraydim, ',')
                t = RawArrayType(t, dims, loc)
                self.expect(TOK_PUNCT, ']')
            else:
                break

        if t is RawVoidType.instance:
            self.error("void type is not instantiatable")
        return t

    def r_member(self):
        loc = self.tokenizer.loc()
        t = self.r_type()
        n = self.expect(TOK_WORD)
        self.expect(TOK_PUNCT, ';')
        r = RawStructMember(t, n, loc)
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
        members = self.repeat(self.r_member, TOK_PUNCT, '}')
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

        # sanity check the data
        if pclass in ('sint', 'uint'):
            if size not in (1, 2, 4, 8):
                self.error('unsupported integer size %d; 1, 2, 4 and 8 supported' % (size))
        elif pclass == "float":
            if size not in (4, 8):
                self.error('unsupported floating-point primitive size %d; 4 and 8 supported' % (size))
        else:
            self.error('unsupported primitive class %s; sint, uint and float supported' % (pclass))

        self.accept(TOK_PUNCT, ';')

        return RawDefPrimitive(name, pclass, size, loc)

    def r_enum_member(self):
        if self.tokenizer.peek()[0] != TOK_WORD:
            return None

        loc = self.tokenizer.loc()
        name = self.expect(TOK_WORD)
        if self.accept(TOK_PUNCT, '='):
            value = self.expect(TOK_INT)
        else:
            value = None
        return RawEnumMember(name, value, loc)

    def r_enum(self):
        loc = self.tokenizer.loc()
        if not self.accept(TOK_WORD, 'enum'):
            return None
        name = self.expect(TOK_WORD)

        self.expect(TOK_PUNCT, '{')

        members = self.sep_nonempy_list(self.r_enum_member, ',', allow_trailing=True);

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

    def r_toplevel(self):
        return self.alt(
                self.r_struct,
                self.r_defprimitive,
                self.r_enum,
                self.r_import,
                self.r_generator_config)

    def r_unit(self):
        return self.repeat(self.r_toplevel, TOK_EOF)

def doparse(fn, data, is_import=False):
    tokenizer = Tokenizer(fn, data, is_import)
    parser = Parser(tokenizer)
    return parser.r_unit()

def parse_string(data):
    return doparse('<string>', data)

def parse_file(fn, handle_imports=False, import_dirs=('.'), import_memo={}, depth=0):
    if depth > 0:
        print "importing", fn

    with open(fn, 'r') as f:
        data = f.read()

    result = doparse(fn, data, depth)

    if handle_imports:
        iresult = []
        for r in result:
            if isinstance(r, RawImportStmt):
                if not import_memo.has_key(r.filename):
                    # todo: should make an effort of using real absolute names here
                    import_memo[r.filename] = True
                    iresult.extend(parse_file(r.filename, True, import_dirs, import_memo, depth+1))
            else:
                iresult.append(r)
        return iresult
    else:
        return result

if __name__ == '__main__':
    import sys
    parse_file(sys.argv[1])
