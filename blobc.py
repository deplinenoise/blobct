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

parser.add_argument('input_fn', metavar='<source file>',
        help='Input source file')
parser.add_argument('-I', metavar='<path>', dest='import_paths', action='append',
        help='Specify import search directories')
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
    parse_tree = blobc.parse_file(args.input_fn, handle_imports=True)

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

        # find generator options from the parse tree
        gen_options = [x for x in parse_tree
                if isinstance(x, blobc.ParseTree.GeneratorConfig) and
                x.generator_name == args.lang]

        gen.apply_configuration(gen_options)

        gen.start()

        imports = []
        prims, enums, structs = [], [], []

        if not args.merge_imports:
            for t in type_system.itertypes():
                if t.loc.is_import:
                    if t.loc.filename not in imports:
                        gen.visit_import(t.loc.filename)
                        imports.append(t.loc.filename)
        else:
            # override import flag
            for t in type_system.itertypes():
                t.loc.is_import = False

        for t in type_system.itertypes():
            if isinstance(t, blobc.Typesys.StructType):
                gen.visit_struct(t)
            elif isinstance(t, blobc.Typesys.EnumType):
                gen.visit_enum(t)
            elif isinstance(t, blobc.Typesys.PrimitiveType):
                gen.visit_primitive(t)

        gen.finish()
    finally:
        if aux_fh is not None:
            aux_fh.close()
        if fh is not sys.stdout:
            fh.close()

except blobc.ParseError as ex:
    sys.stderr.write('%s(%d): %s\n' % (ex.filename, ex.lineno, ex.msg))
    sys.exit(1)
