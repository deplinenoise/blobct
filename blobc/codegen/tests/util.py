import re
from cStringIO import StringIO

import blobc

re_compress = re.compile('\s+', re.DOTALL)

def compress_c(cstr):
    '''Compress a C language string to single space whitespace for more
    reliable testing.'''
    return re.sub(re_compress, ' ', cstr).strip()

class InMemoryImportHandler:
    """Handle file import requests from a dictionary of filename->data"""
    def __init__(self, files):
        self._files = files
    def get_import_contents(self, fn):
        return self._files[fn]
    def find_imported_file(self, fn):
        return fn if self._files.has_key(fn) else None

class CodegenTestResult(object):
    """Dummy class to hold test driver results"""
    pass

class CodegenTestDriver(object):
    """Base class for test cases that test code generators"""
    def __init__(self, gen_cls):
        self._gen_cls = gen_cls

    def _apply_options(self, stream, kwargs):
        """Override to apply options and print to stream"""
        pass

    def run(self, src, kwargs):
        src_text = StringIO()
        self._apply_options(src_text, kwargs)
        src_text.write(src)

        imports = kwargs.get('imports', {})
        imports['<string>'] = src_text.getvalue()

        result = CodegenTestResult()
        result.parse_tree = blobc.parse_file(
                '<string>', handle_imports=True,
                import_handler=InMemoryImportHandler(imports))
        result.tsys = blobc.compile_types(result.parse_tree)
        out_fh = StringIO()
        aux_fh = StringIO()
        gen = self._gen_cls(out_fh, 'input.blob', aux_fh, 'output.h')
        gen.generate_code(result.parse_tree, result.tsys)
        result.output = out_fh.getvalue()
        result.aux_output = aux_fh.getvalue()
        if not kwargs.get('keep_ws', False):
            result.output = compress_c(result.output)
            result.aux_output = compress_c(result.aux_output)
        return result

