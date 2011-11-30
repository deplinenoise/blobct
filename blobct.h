
#include <inttypes.h>
#include <stdlib.h>
#include <stddef.h>

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

typedef struct bct_typenode {
	uint8_t metatype;
	uint8_t primitive_class;
	uint8_t primitive_size;
	uint8_t primitive_alignment;
	uint32_t native_size;
	uint32_t native_align;
	union {
		uint32_t member_count;
		uint32_t array_dimension;
	};
	union {
		const void *extension_;
		const struct bct_typenode *subtype;
		const struct bct_member *members;
	};
	const char *name;
} bct_typenode;

extern bct_typenode bct_typenode_void_;

typedef struct bct_member {
	const char *name; /* NULL for array dimensions */
	uint32_t native_offset;
	const struct bct_typenode *type;
} bct_member;


#if 0
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
#endif
