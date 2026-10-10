/*
 * AIDB public C API — draft ABI, not yet implemented.
 *
 * Keep this header valid in both C and C++. The stable boundary is C;
 * optional C++ wrappers should be layered on top of this API.
 */
#ifndef AIDB_AIDB_H
#define AIDB_AIDB_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define AIDB_ABI_VERSION 1u

typedef struct aidb_handle aidb_handle;

typedef enum aidb_status {
    AIDB_OK = 0,
    AIDB_INVALID_ARGUMENT = 1,
    AIDB_NOT_FOUND = 2,
    AIDB_ALREADY_EXISTS = 3,
    AIDB_REVISION_CONFLICT = 4,
    AIDB_UNAUTHENTICATED = 5,
    AIDB_PERMISSION_DENIED = 6,
    AIDB_UNSUPPORTED_VERSION = 7,
    AIDB_UNSUPPORTED_CAPABILITY = 8,
    AIDB_INTEGRITY_FAILURE = 9,
    AIDB_UNAVAILABLE = 10,
    AIDB_INTERNAL_ERROR = 11
} aidb_status;

/* Borrowed UTF-8 bytes. Not necessarily NUL-terminated. */
typedef struct aidb_string_view {
    const char *data;
    size_t size;
} aidb_string_view;

/* Owned byte buffer returned by AIDB; release with aidb_buffer_free. */
typedef struct aidb_buffer {
    uint8_t *data;
    size_t size;
} aidb_buffer;

/* Open/close a local or configured node. Options are UTF-8 JSON. */
aidb_status aidb_open(aidb_string_view options_json, aidb_handle **out_handle);
void aidb_close(aidb_handle *handle);

/* Return a stable machine-readable error object for the last failed call.
 * The returned buffer must be freed with aidb_buffer_free. */
aidb_status aidb_last_error(aidb_handle *handle, aidb_buffer *out_json);
void aidb_buffer_free(aidb_buffer *buffer);

/* All JSON arguments/results use UTF-8 and the versioned AIDB contract.
 * Resource identifiers are opaque strings, never assumed to be integers. */
aidb_status aidb_get_specification(aidb_handle *handle, aidb_buffer *out_json);
aidb_status aidb_get_resource(aidb_handle *handle, aidb_string_view resource_id,
                              aidb_buffer *out_json);
aidb_status aidb_create_resource(aidb_handle *handle, aidb_string_view resource_json,
                                 aidb_buffer *out_json);
aidb_status aidb_update_resource(aidb_handle *handle, aidb_string_view resource_id,
                                 uint64_t expected_revision,
                                 aidb_string_view patch_json,
                                 aidb_buffer *out_json);
aidb_status aidb_delete_resource(aidb_handle *handle, aidb_string_view resource_id,
                                 uint64_t expected_revision);
aidb_status aidb_relate_resources(aidb_handle *handle,
                                  aidb_string_view relationship_json);

/* Cursor is opaque JSON returned by the previous page; empty means start. */
aidb_status aidb_list_changes(aidb_handle *handle, aidb_string_view cursor_json,
                              uint32_t limit, aidb_buffer *out_json);

/* Portable interchange, not a native database-file copy. */
aidb_status aidb_export_snapshot(aidb_handle *handle,
                                 aidb_string_view options_json,
                                 aidb_buffer *out_snapshot);
aidb_status aidb_import_snapshot(aidb_handle *handle,
                                 aidb_string_view snapshot_json,
                                 aidb_string_view mode);

#ifdef __cplusplus
} /* extern "C" */
#endif

#endif /* AIDB_AIDB_H */
