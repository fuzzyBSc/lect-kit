# Field schemas in LinkML (proposal, not yet wired)

These describe each format's fields so that engines (rendering, scoring, checking,
practice) and classification screening can work from them. They follow what the
project custodian decided on 8 November 2026, recorded in
`knowledge/spec_classification.md` under "Field schemas (decided, not yet built)".

- `lectkit.yaml` is the lect-kit vocabulary every format schema imports. It holds the
  `form` and `text` types and the `lectkit_material` and `lectkit_layering` annotations.
- `lexicon.yaml` and `slot-table.yaml` are the first two formats, the ones the nouns page
  reads.

Nothing reads them yet. `lectkit/formats.py` still reads the layering-only schemas
one directory up, and it doesn't look in this folder. They replace those schemas once
`formats.py` reads LinkML.

Validate a file against one by hand (LinkML 1.12.1; on Windows set `PYTHONUTF8=1`):

    linkml-validate -s lectkit/schemas/linkml/lexicon.yaml -C LexiconFile <path>/lexicon-nouns.yaml

Known gaps, which lect-kit has to fill itself:
- reference resolution within the tier's audience;
- the value type of open maps such as `works`, because LinkML doesn't enforce
  `extra_slots.range_expression`;
- screening by annotation.
