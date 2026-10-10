# Multilingual and Programming-Language-Agnostic Design

Status: proposed architecture and product policy. This document does not claim that every language, script, tokenizer, or binding is implemented.

## Recommendation

AIDB should be agnostic in two separate senses:

1. **Programming-language agnostic:** the contract and data semantics are independent of the implementation language. C is the intended stable low-level ABI; optional C++, Python, Rust, Java, JavaScript/TypeScript, and other bindings should map to the same behavior.
2. **Human-language agnostic:** data can be stored, searched, related, and exchanged in any language or script, including English, Simplified and Traditional Chinese, Japanese, Arabic, and mixed-language content.

English can remain the default language for source code identifiers, repository documentation, API names, and normative technical specifications. It must not be a requirement that user content, resource names, notes, or agent memory be in English.

## Core principles

- Store text as Unicode, using UTF-8 at interoperable text boundaries unless a format explicitly requires another encoding.
- Preserve original bytes for file artifacts; do not decode unknown binary data as text.
- Preserve the original user text and script. Normalization or transliteration may create a derived search/index representation, never silently replace the source.
- Do not assume one language per resource. Mixed-language fields, documents, and conversations are valid.
- Keep locale, language, script, directionality, and transliteration as separate metadata concepts. Language identification can be unknown or uncertain.
- Language-specific processing is an optional adapter. Basic storage and retrieval must not require a language model, translation service, or network access.
- Never automatically translate content on ingest. Translation, transliteration, summarization, and language conversion are explicit transformations with provenance.
- Do not treat a translated or transliterated string as equivalent to the original for identity, authorization, hashing, or exact-match purposes.

## Text and metadata model

Where relevant, text-bearing resources SHOULD support:

- original text exactly as supplied;
- BCP 47 language tag when known, for example `en`, `zh-Hans`, `zh-Hant`, `ja`, or `ar`; tags may be absent or uncertain;
- script tag where useful, using ISO 15924 conventions, such as `Hans`, `Hant`, `Jpan`, or `Arab`;
- text direction (`ltr`, `rtl`, or `auto`) for display metadata, without treating it as a security boundary;
- optional normalized search form, with the normalization algorithm/version recorded;
- optional transliteration, translation, or extracted text as separately identified derived content;
- provenance for automated language detection, translation, OCR, or transliteration.

BCP 47 tags and script metadata are hints about language and presentation, not proof of content, user identity, or correctness. Do not force a language tag when the content is multilingual or detection is inconclusive.

## Unicode and multilingual correctness

- Use Unicode-capable types and UTF-8 at public text boundaries.
- Test non-ASCII identifiers and content where the contract allows them; do not accidentally restrict user-visible text to ASCII.
- Use Unicode-aware normalization and case folding only for explicitly defined search/comparison operations. Keep original text intact.
- Do not use byte length as the displayed character count. Specify whether limits are in bytes, Unicode code points, grapheme clusters, or tokens.
- Avoid language assumptions in sorting, tokenization, stemming, and word-boundary detection; make search analyzers configurable by language.
- Support right-to-left display for Arabic and mixed-direction text. Use appropriate bidirectional isolation in user interfaces and avoid concatenating untrusted RTL text into security-sensitive logs or command strings.
- Ensure JSON serialization and import/export preserve Unicode text. Reject malformed encodings clearly rather than silently replacing characters.
- Do not normalize filenames or resource identifiers in a way that can cause collisions. Define comparison and uniqueness rules separately from display.

## Search and retrieval

Search should be modular and language-aware, not built around English-only tokenization.

- Begin with exact metadata filtering and Unicode-safe substring or full-text search.
- Allow language-specific analyzers to be installed independently.
- Chinese search must not require whitespace-delimited words; Japanese search must not assume spaces separate words; Arabic processing must not assume one spelling form or diacritic pattern.
- Treat stemming, segmentation, diacritic folding, transliteration, and semantic embeddings as optional retrieval strategies, each versioned and configurable.
- Search results should retain references to original artifacts and text spans when the adapter can provide them.
- Avoid promising equal search quality across languages until evaluated with representative test collections.

## API and binding policy

- Keep public operation names and canonical schema field names stable and language-neutral; English technical identifiers are acceptable.
- Keep user content as Unicode strings or byte-safe artifact streams according to the declared media type.
- Define C ABI text parameters with explicit pointer/length pairs or string-view structures; do not assume NUL termination for arbitrary data.
- Bindings may use native idioms but must preserve the same error codes, revision behavior, identity semantics, and data meaning.
- Separate API localization (translated error/help messages) from stable machine-readable error codes.
- Document encoding, ownership, lifetime, and allocation rules for every C buffer and string.

## Conformance and test plan

Include fixtures for:

- English, Simplified Chinese, Traditional Chinese, Japanese, and Arabic;
- mixed-language paragraphs and code-switching;
- combining marks, supplementary-plane characters, emoji, and normalization edge cases;
- right-to-left text adjacent to Latin identifiers, punctuation, and numbers;
- multilingual filenames and metadata;
- exact Unicode round-trip through create/read/update/export/import;
- malformed UTF-8 rejection or explicitly documented alternative-encoding behavior;
- binding parity across C and at least one higher-level implementation;
- search relevance tests separately for each supported analyzer and language.

Tests must distinguish successful Unicode storage from language-aware search quality. Passing the first does not prove the second.

## Implementation sequence

1. State explicitly in the core contract that text is Unicode and interoperable JSON is UTF-8.
2. Audit C ABI string handling, lengths, ownership, and error behavior.
3. Add multilingual round-trip fixtures for Chinese, Japanese, and Arabic, including mixed RTL/LTR text.
4. Add language/script/direction metadata without requiring it on every resource.
5. Define a pluggable search-analyzer interface and measure language-specific quality before adding more advanced retrieval.
6. Add localized documentation and agent-facing messages later, keeping machine protocols stable and language-neutral.

## Acceptance criteria

AIDB is human-language agnostic at the storage layer when it can preserve and exchange supported Unicode text without loss, does not assume English for resource content, and can represent language metadata without forcing a single language. It is language-aware at the retrieval layer only to the extent that installed analyzers have been implemented and tested.
