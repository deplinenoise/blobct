import re

re_compress = re.compile('\s+', re.DOTALL)

def compress_c(cstr):
    '''Compress a C language string to single space whitespace for more
    reliable testing.'''
    return re.sub(re_compress, ' ', cstr).strip()

