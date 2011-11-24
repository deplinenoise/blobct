
from Typesys import *

class StructBase(object):

    def __init__(self, **kwargs):
        cls = type(self)
        self.__dict__['_StructBase__data'] = {}

        for m in cls.srctype.members:
            if not kwargs.has_key(m.mname):
                self.__data[m.mname] = m.mtype.default_value()

        for k, v in kwargs.iteritems():
            self.__setattr__(k, v)

    def __str_value(self, name):
        v = self.__data.get(name)
        if v is None:
            v = "<undef>"
        return str(v)

    def __setattr__(self, n, v):
        ntype = type(self).srctype
        fieldtype = ntype.get_field_type(n)
        self.__data[n] = fieldtype.create_value(v)

    def __getattr__(self, n):
        cls = type(self)
        cls.srctype.get_field_type(n)
        return self.__data[n]

    def __setitem__(self, n, v):
        self.__data[n] = v

    def __getitem__(self, n):
        return self.__data[n]

    def __str__(self):
        cls = type(self)
        mems = ["%s = %s" % (m.mname, self.__str_value(m.mname)) for m in cls.srctype.members]
        return '%s { %s }' % (cls.srctype.name, '; '.join(mems))

def make_class(t, typesys):
    fields = {}
    for mem in t.members:
        fields[mem.mname] = mem

    pyfields = dict(srctype = t, fields = fields, typesys = typesys)

    return type(t.name, (StructBase,), pyfields)

def generate_classes(typesys, global_dict):
    for t in typesys.itertypes():
        if not isinstance(t, StructType):
            continue
        cls = make_class(t, typesys)
        t.set_class_object(cls)
        global_dict[t.name] = cls

