import json

from aidb import AIDB


MULTILINGUAL_CASES = {
    "zh_hans": "你好，世界 — 漢字示例",
    "zh_hant": "你好，世界 — 繁體中文示例",
    "ja": "こんにちは世界 — 日本語の例",
    "ar": "مرحبا بالعالم — مثال عربي",
    "mixed_rtl_ltr": "ABC مرحبا بالعالم 123",
    "emoji_and_latin": "A1-B2: 你好 — こんにちは — مرحبا",
}


def test_multilingual_note_content_and_metadata_round_trip():
    source = AIDB(":memory:")
    source.initialize_home(owner="agent:one", visibility="private")

    for key, value in MULTILINGUAL_CASES.items():
        source.create_note(
            f"{key}-title",
            value,
            owner="agent:one",
            visibility="public",
            metadata={"language": key, "text": value},
        )

    exported = source.export_home(include_private=True)

    restored = AIDB(":memory:")
    restored.import_home(exported)

    restored_by_title = {note.title: note for note in restored.list_notes(include_private=True)}

    for key, value in MULTILINGUAL_CASES.items():
        note = restored_by_title[f"{key}-title"]
        assert note.content == value
        assert note.metadata["language"] == key
        assert note.metadata["text"] == value


def test_multilingual_resource_payload_and_relation_round_trip():
    source = AIDB(":memory:")
    source.initialize_home(owner="agent:one", visibility="private")

    left = source.create_resource(
        "document",
        {
            "title": "ABC مرحبا بالعالم 123",
            "body": "你好，世界 — こんにちは — مرحبا",
            "nested": {
                "zh_hans": "你好",
                "zh_hant": "你好",
                "ja": "こんにちは",
                "ar": "مرحبا",
                "mixed": "A مرحبا B",
            },
        },
        owner="agent:one",
        visibility="public",
        metadata={"script_mix": ["latin", "arabic", "han", "hiragana"], "sample": "ABC مرحبا بالعالم 123"},
    )

    right = source.create_resource(
        "document",
        {
            "title": "日本語の例",
            "body": "中文例子 — 例子中文 — مثال عربي",
            "nested": {"samples": ["你好", "こんにちは", "مرحبا"]},
        },
        owner="agent:one",
        visibility="public",
        metadata={"sample": "繁體中文 / 日本語 / العربية"},
    )

    source.relate_resources(left.id, right.id, "references", metadata={"note": "ABC مرحبا بالعالم 123"})

    exported = source.export_home(include_private=True)

    restored = AIDB(":memory:")
    restored.import_home(exported)

    restored_resources = {resource.resource_type + ":" + str(resource.id): resource for resource in restored.list_resources(include_private=True)}
    restored_left = next(resource for resource in restored.list_resources(include_private=True) if resource.resource_type == "document" and resource.metadata.get("script_mix") == ["latin", "arabic", "han", "hiragana"])
    restored_right = next(resource for resource in restored.list_resources(include_private=True) if resource.metadata.get("sample") == "繁體中文 / 日本語 / العربية")

    assert restored_left.content["title"] == "ABC مرحبا بالعالم 123"
    assert restored_left.content["body"] == "你好，世界 — こんにちは — مرحبا"
    assert restored_left.content["nested"]["ar"] == "مرحبا"
    assert restored_right.content["nested"]["samples"] == ["你好", "こんにちは", "مرحبا"]

    relations = restored.resource_relations(restored_left.id)
    assert len(relations) == 1
    assert relations[0]["relation"] == "references"
    assert json.loads(relations[0]["metadata"]) == {"note": "ABC مرحبا بالعالم 123"}
