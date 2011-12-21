#! /usr/bin/env python

import blobc
import blobc.Typesys
import blobc.ParseTree
from blobc.codegen import *
import sys
import argparse

parser = argparse.ArgumentParser(description = 'Generate source code from blob definitions')

languages = {
    'm68k': M68kGenerator,
    'c' : CGenerator,
    'csharp' : CSharpGenerator,
}

parser.add_argument('input_fn', metavar='<source file>',
        help='Input source file')
parser.add_argument('-I', metavar='<path>', dest='import_paths', action='append',
        help='Specify import search directories', default=['.'])
parser.add_argument('-m', '--merge-imports', dest='merge_imports', action='store_true',
        help='Merge all imports together and produce stand-alone output suitable for distribution')
parser.add_argument('-o', metavar='<file>', dest='output_fn',
        help='Output source file')
parser.add_argument('-a', metavar='<file>', dest='aux_fn',
        help='Auxiliary output source file')
parser.add_argument('-l', metavar='<language>', dest='lang', required=True,
        choices=languages.keys().sort(),
        help='Specify language to generate code for (%s)' % (', '.join(languages)))

args = parser.parse_args()

try:
    parse_tree = blobc.parse_file(args.input_fn, import_dirs=args.import_paths, handle_imports=True)

    type_system = blobc.compile_types(parse_tree)

    fh = sys.stdout
    aux_fh = None

    try:
        if args.output_fn is not None:
            fh = open(args.output_fn, 'w')
        if fh and args.aux_fn is not None:
            aux_fh = open(args.aux_fn, 'w')

        # create generator
        gencls = languages[args.lang]
        gen = gencls(fh, args.input_fn, aux_fh, args.output_fn)

        gen.generate_code(parse_tree, type_system, merge_imports=args.merge_imports)

    finally:
        if aux_fh is not None:
            aux_fh.close()
        if fh is not sys.stdout:
            fh.close()

except blobc.Typesys.TypeSystemException as ex:
    sys.stderr.write(ex.message)
    sys.exit(1)
except blobc.ParseError as ex:
    sys.stderr.write('%s(%d): %s\n' % (ex.filename, ex.lineno, ex.msg))
    sys.exit(1)
