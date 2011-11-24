import struct

from Typesys import Array
from ClassGen import StructBase
from cStringIO import StringIO

class Serializer(object):
    def __init__(self, typesys, targmach):
        self.__targmach = targmach
        self.__fixups = []
        self.__locations = {}
        self.__offset = 0
        self.__block_index = 0
        self.__blocks = [StringIO()]
        self.__relocs = []
        self.__nullstr = '\0' * targmach.pointer_size()
        self.__unresolved_relocs = False

    def __block(self):
        return self.__blocks[self.__block_index]

    def targmach(self):
        return self.__targmach

    def here(self):
        return (self.__block_index, self.__block().tell())

    def divert(self):
        self.__block_index += 1
        if len(self.__blocks) <= self.__block_index:
            self.__blocks.append(StringIO())
        return self.here()

    def update_location(self, datum):
        assert not self.__locations.has_key(datum)
        self.__locations[datum] = self.here()

    def location_of(self, datum):
        loc = self.__locations.get(datum)
        if loc is not None:
            return loc
        self.__unresolved_relocs = True
        return (None, datum)

    def write_ptr(self, location, offset = 0):
        self.__relocs.append((self.here(), location, offset))
        self.write_null_ptr()

    def write_null_ptr(self):
        self.__block().write(self.__nullstr)

    def resume(self):
        assert self.__block_index > 0
        self.__block_index -= 1

    def __find_type(self, v):
        if isinstance(v, Array):
            return v.item_type.array_type(len(v.items), None)
        elif isinstance(v, StructBase):
            return type(v).srctype
        else:
            assert false 

    def align(self, alignment):
        blk = self.__block()
        pos = blk.tell()
        pad = ((pos + alignment - 1) & ~(alignment - 1)) - pos
        if pad > 0:
            blk.write('\xfd' * pad)

    def write(self, data):
        self.__block().write(data)

    def __commit_pending(self):
        while self.__unresolved_relocs:
            self.__unresolved_relocs = False
            # use indexed iteration as we might add stuff to the array
            for x in xrange(0, len(self.__relocs)):
                (sblock, sidx), (dblock, didx), off = self.__relocs[x]
                if dblock is None:
                    obj = didx
                    ntype = self.__find_type(obj)
                    dblock, didx = self.here()
                    ntype.serialize(self, obj)
                    self.__relocs[x] = ((sblock, sidx), (dblock, didx), off)

    def freeze(self):
        self.__commit_pending()
        head = self.__blocks[0]
        block_locations = [0]
        for b in self.__blocks[1:]:
            block_locations.append(head.tell())
            head.write(b.getvalue())

        pfx = '>' if self.__targmach.big_endian() else '<'
        rel_fmt = pfx + 'I'
        fix_fmt = '%s%s' % (pfx, 'I' if 4 == self.__targmach.pointer_size() else 'Q') 

        reloc_block = StringIO()

        # patch in relocation offsets
        for r in self.__relocs:
            (sblock, sidx), (dblock, didx), off = r

            head.seek(sidx)
            targoff = block_locations[dblock] + didx + off
            head.write(struct.pack(fix_fmt, targoff))

            srcoff = block_locations[sblock] + sidx
            reloc_block.write(struct.pack(rel_fmt, srcoff))

        return head.getvalue(), reloc_block.getvalue()

def layout(root, targmach):
    cls = type(root) # root must be struct type currently
    typesys = cls.typesys
    ntype = cls.srctype

    sr = Serializer(typesys, targmach)

    ntype.serialize(sr, root)
    
    return sr.freeze()
