# Optional AIID descriptor adapter

AIDB can store AIID draft 0.1 descriptors as ordinary private-by-default resources using the optional helper in aidb.aiid.

## Example

~~~python
from aidb import AIDB, register_aiid_descriptor

db = AIDB("aidb.sqlite3")
db.initialize_home(owner="agent:local")

resource = register_aiid_descriptor(
    db,
    {
        "aiid_version": "0.1",
        "identity": {"id": "urn:example:photo:1", "type": "image"},
        "resource": {"name": "photo.jpeg", "media_type": "image/jpeg"},
    },
    owner="agent:local",
)
print(resource.id)
~~~

## Contract

- The adapter accepts UTF-8 JSON bytes, JSON text, or a JSON-compatible object.
- It validates the minimum AIID 0.1 structure and preserves unknown extension fields.
- It stores the descriptor as an AIDB resource with resource type aiid-descriptor.
- The descriptor content is retained as data; a small copy of identity/version is indexed in metadata.
- The resource visibility defaults to private.
- AIID is optional. AIDB works without descriptors.
- The adapter does not resolve paths, open files, fetch URIs, verify hashes, authenticate publishers, interpret permissions, or execute resources.
- Descriptor claims remain untrusted metadata. A stored descriptor does not prove that the described resource exists or is safe.

The helper is intentionally narrower than the full AIID reference implementation. It provides a safe ingestion boundary, not full JSON Schema validation or an AIID trust system.
