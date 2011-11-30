
#include "foo.h"

typedef enum {
	BCT_VOID,
	BCT_STRUCT,
	BCT_PRIMITIVE,
	BCT_POINTER,
	BCT_CSTRING,
	BCT_ARRAY
} bct_metatype_t;

typedef enum {
	BCT_NONE,
	BCT_UNSIGNED,
	BCT_SIGNED,
	BCT_FLOAT,
	BCT_CHAR,
} bct_primitive_class_t;

typedef struct bct_typenode_tag {
	u8 metatype;
	u8 primitive_class;
	u8 primitive_size;
	u8 primitive_alignment;
	u32 native_size;
	u32 native_align;
	union {
		u32 member_count;
		u32 array_dimension;
	};
	const struct bct_member_tag *members;
	const struct bct_typenode_tag *subtype;
	const char *name;
} bct_typenode_t;

typedef struct bct_member_tag {
	const struct bct_typenode_tag *type;
	unsigned native_offset;
	const char *name; /* NULL for array dimensions */
} bct_member_t;

const struct bct_typenode_t bct_descriptor_u32_ = {
	BCT_PRIMITIVE,
	BCT_UNSIGNED,
	4,
	4,
	0,
	sizeof(u32),
	alignof(u32),
	NULL,
	"u32"
};

const struct bct_member_t bct_array_u32_16 = {
	&bct_descriptor_u32_, 
	NULL,
	16
};

const struct bct_typenode_t bct_descriptor_u32_array16 = {
	BCT_ARRAY,
	BCT_NONE,
	4,
	4,
	1,
	sizeof(u32),
	alignof(u32),
	&bct_array_u32_16,
	"u32"
};

const struct bct_struct_member_t bct_struct_foo_members_[] = {
	{ &bct_descriptor_u32_, "foo" },
	{ &bct_descriptor_u32_array16, "bar" }
};

const struct bct_typenode_t bct_descriptor_foo_ = {
	BCT_STRUCT,
	BCT_NONE,
	0,
	0,
	sizeof(struct foo),
	alignof(struct u32),
	sizeof(bct_struct_foo_members_)/sizeof(bct_struct_foo_members_[0]),
	&bct_struct_foo_members_[0],
	"foo"
};

#define BCT_MAKE(pkg, seg, type) \
	bct_make(pkg, seg, bct_descriptor_ ## type ## _)

#define BCT_MAKE_ARRAY(pkg, seg, type, count) \
	bct_make_array(pkg, seg, bct_descriptor_ ## type ## _, count)

void save_foo(FILE* f, const foo *data) {

	bct_package *pkg = bct_init();

	root_t *root = BCT_MAKE(pkg, /* seg */0, root_t);

	root->foo = "bar";
	root->count = 3;
	root->ptr = BCT_MAKE_ARRAY(pkg, /* seg 1 */, root->count, u32);

	root->ptr[0] = 1;
	root->ptr[1] = 2;
	root->ptr[2] = 3;
	roor->eptr = ptr + 2;
	
	bct_freeze(pkg);
}
