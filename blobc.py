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
parser.add_argument('-a', metavar='<file>', dest='aux_fn', help='Auxiliary output source file')
parser.add_argument('-l', metavar='<language>', dest='lang', required=True,
        choices=languages.keys().sort(),
        help='Specify language to generate code for (%s)' % (', '.join(languages)))

args = parser.parse_args()

try:
    parse_tree = blobc.parse_file(args.input_fn)

    type_system = blobc.compile_types(parse_tree)

    fh = sys.stdout
    aux_fh = None

    try:
        if args.output_fn is not None:
            fh = open(args.output_fn, 'w')
        if fh and args.aux_fn is not None:
            aux_fh = open(args.aux_fn, 'w')

        gencls = languages[args.lang]

        gen = gencls(fh, args.input_fn, aux_fh, args.output_fn)

        for t in type_system.itertypes():
            if isinstance(t, blobc.Typesys.PrimitiveType):
                gen.visit_primitive(t)

        for t in type_system.itertypes():
            if isinstance(t, blobc.Typesys.StructType):
                gen.visit_struct(t)

        gen.finish()
    finally:
        if aux_fh is not None:
            aux_fh.close()
        if fh is not sys.stdout:
            fh.close()

except blobc.ParseError as ex:
    print ex.msg
    sys.exit(1)
