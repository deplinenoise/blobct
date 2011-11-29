import struct

from Typesys import Array
from ClassGen import StructBase
from cStringIO import StringIO

class Serializer(object):
    def __init__(self, typesys, targmach):
        self.targmach = targmach
        self._fixups = []
        self._locations = {}
        self._offset = 0
        self._block_index = 0
        self._blocks = [StringIO()]
        self._relocs = []
        self._nullstr = '\0' * targmach.pointer_size
        self._unresolved_relocs = False

    def _block(self):
        return self._blocks[self._block_index]

    def here(self):
        return (self._block_index, self._block().tell())

    def divert(self):
        self._block_index += 1
        if len(self._blocks) <= self._block_index:
            self._blocks.append(StringIO())
        return self.here()

    def update_location(self, datum):
        assert not self._locations.has_key(datum)
        self._locations[datum] = self.here()

    def location_of(self, datum):
        loc = self._locations.get(datum)
        if loc is not None:
            return loc
        self._unresolved_relocs = True
        return (None, datum)

    def write_ptr(self, location, offset = 0):
        self._relocs.append((self.here(), location, offset))
        self.write_null_ptr()

    def write_null_ptr(self):
        self._block().write(self._nullstr)

    def resume(self):
        assert self._block_index > 0
        self._block_index -= 1

    def _find_type(self, v):
        if isinstance(v, Array):
            return v.item_type.array_type(len(v.items), None)
        elif isinstance(v, StructBase):
            return type(v).srctype
        else:
            assert false 

    def align(self, alignment):
        blk = self._block()
        pos = blk.tell()
        pad = ((pos + alignment - 1) & ~(alignment - 1)) - pos
        if pad > 0:
            blk.write('\xfd' * pad)

    def write(self, data):
        self._block().write(data)

    def _commit_pending(self):
        while self._unresolved_relocs:
            self._unresolved_relocs = False
            # use indexed iteration as we might add stuff to the array
            for x in xrange(0, len(self._relocs)):
                (sblock, sidx), (dblock, didx), off = self._relocs[x]
                if dblock is None:
                    obj = didx
                    ntype = self._find_type(obj)
                    dblock, didx = self.here()
                    ntype.serialize(self, obj)
                    self._relocs[x] = ((sblock, sidx), (dblock, didx), off)

    def freeze(self):
        self._commit_pending()
        head = self._blocks[0]
        block_locations = [0]
        for b in self._blocks[1:]:
            block_locations.append(head.tell())
            head.write(b.getvalue())

        pfx = '>' if self.targmach.big_endian else '<'
        rel_fmt = pfx + 'I'
        fix_fmt = '%s%s' % (pfx, 'I' if 4 == self.targmach.pointer_size else 'Q') 

        reloc_block = StringIO()

        # patch in relocation offsets
        for r in self._relocs:
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
