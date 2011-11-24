#! /usr/bin/env python

import re
from ParseTree import *

SCANNER = re.compile(r'(\s+)|(//)[^\n]*|(\d+)|([][,;:{}*])|([A-Za-z_][A-Za-z0-9_]*)|(.)', re.S);

TOK_EOF = -1
TOK_WORD = 1
TOK_INT = 2
TOK_PUNCT = 3

class ParseError(Exception):
    def __init__(self, lineno, msg):
        object.__init__(self)
        self.lineno = lineno
        self.msg = msg

class Tokenizer(object):
    def __init__(self, filename, data):
        object.__init__(self)
        self.filename = filename
        self.lineno = 1
        self.pos = 1
        self.data = data
        self.titer = re.finditer(SCANNER, self.data)
        self.cache = None

    def next(self):
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

            space, comment, integer, punct, word, badchar = m.groups()

            if space is not None:
                self.lineno += space.count('\n')
                continue

            if comment is not None:
                continue

            if integer is not None:
                return TOK_INT, int(integer)

            if punct is not None:
                return TOK_PUNCT, punct

            if word is not None:
                return TOK_WORD, word

            raise ParseError(self.lineno, 'bad token char: "%s"' % (badchar))

    def peek(self):
        if self.cache is None:
            self.cache = self.next()
        return self.cache

    def loc(self):
        return self.filename, self.lineno

class Parser(object):
    def __init__(self, tokenizer):
        object.__init__(self)
        self.tokenizer = tokenizer

    def error(self, msg):
        raise ParseError(self.tokenizer.lineno, msg)

    def accept(self, tt, tv=None):
        t, v = self.tokenizer.peek()
        if t == tt and (tv is None or tv == v):
            self.tokenizer.next()
            return True
        else:
            return False

    def expect(self, tt, tv=None):
        t, v = self.tokenizer.next()
        if t != tt:
            self.error('expected %d but got %d' % (tt, t))
        if tv is not None:
            if tv != v:
                self.error('expected %s but got %s' % (str(tv), str(v)))
        return v

    def repeat(self, rule, end_tok, end_val=None):
        result = []
        while True:
            t, v = self.tokenizer.peek()
            if t == end_tok and (end_val is None or end_val == v):
                return result
            result.append(rule())
        return result

    def require(self, rule):
        v = rule()
        if v is None:
            self.error("expected %s at this point" % (str(rule)))
        return v

    def sep_nonempy_list(self, rule, sep, end_tok, end_val = None):
        result = [ self.require(rule) ]
        while self.accept(TOK_PUNCT, sep):
            result.append(self.require(rule))
        return result

    def alt(self, *rules):
        for r in rules:
            v = r()
            if v: return v

        self.error("no matching alternative")

    def r_arraydim(self):
        return self.expect(TOK_INT)

    def r_type(self):
        loc = self.tokenizer.loc()
        t = RawSimpleType(self.expect(TOK_WORD), loc)

        while True:
            if self.accept(TOK_PUNCT, '*'):
                loc = self.tokenizer.loc()
                t = RawPointerType(t, loc)
            elif self.accept(TOK_PUNCT, '['):
                loc = self.tokenizer.loc()
                dims = self.sep_nonempy_list(self.r_arraydim, ',', TOK_PUNCT, ']')
                t = RawArrayType(t, dims, loc)
                self.expect(TOK_PUNCT, ']')
            else:
                break
            
        return t

    def r_member(self):
        loc = self.tokenizer.loc()
        t = self.r_type()
        n = self.expect(TOK_WORD)
        self.expect(TOK_PUNCT, ';')
        r = RawStructMember(t, n, loc)
        return r

    def r_struct(self):
        loc = self.tokenizer.loc()
        if not self.accept(TOK_WORD, 'struct'):
            return None
        name = self.expect(TOK_WORD)
        self.expect(TOK_PUNCT, '{')
        members = self.repeat(self.r_member, TOK_PUNCT, '}');
        self.expect(TOK_PUNCT, '}')
        self.accept(TOK_PUNCT, ';')
        return RawStructType(name, members, loc)

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

    def r_toplevel(self):
        return self.alt(self.r_struct, self.r_defprimitive)

    def r_unit(self):
        return self.repeat(self.r_toplevel, TOK_EOF)

def doparse(fn, data):
    tokenizer = Tokenizer(fn, data)
    parser = Parser(tokenizer)
    return parser.r_unit()

def parse_string(data):
    return doparse('<string>', data)

def parse_file(fn):
    with open(fn, 'r') as f:
        data = f.read()
    return doparse(fn, data)

if __name__ == '__main__':
    import sys
    parse_file(sys.argv[1])
