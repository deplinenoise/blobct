#! /usr/bin/env python

import blobc
import blobc.Typesys
from blobc.codegen import *
import sys
import argparse

parser = argparse.ArgumentParser(description = 'Generate source code from blob definitions')

languages = {
    'm68k': M68kGenerator,
    'c' : CGenerator,
}

parser.add_argument('input_fn', metavar='<source file>', help='Input source file')
parser.add_argument('-o', metavar='<file>', dest='output_fn', help='Output source file')
parser.add_argument('-l', metavar='<language>', dest='lang', required=True,
        choices=languages.keys().sort(),
        help='Specify language to generate code for (%s)' % (', '.join(languages)))

args = parser.parse_args()

def run_generator(gen, fh, filename):
    gen.set_output(fh)

    for t in type_system.itertypes():
        if isinstance(t, blobc.Typesys.PrimitiveType):
            gen.visit_primitive(t)

    for t in type_system.itertypes():
        if isinstance(t, blobc.Typesys.StructType):
            gen.visit_struct(t)

    gen.finish()

try:
    parse_tree = blobc.parse_file(args.input_fn)

    type_system = blobc.compile_types(parse_tree)

    gen = languages[args.lang](args.input_fn)

    if args.output_fn is not None:
        with open(args.output_fn, 'w') as fh:
            run_generator(gen, fh, args.input_fn)
    else:
        run_generator(gen, sys.stdout, args.input_fn)

except blobc.ParseError as ex:
    print ex.msg
    sys.exit(1)
