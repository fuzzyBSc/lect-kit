Feature: File formats and their schemas
  As an agent building a store for one audience
  I want every data format the kit handles to have a schema that says how its records are identified and how a higher tier adds to them
  So that a tier's additions join the right record, identifiers keep names that say what they identify, and nothing falls back on a generic overlay

  Carries out knowledge/spec_classification.md, "Formats and schemas".
  Project custodian's ruling, 2026-11-08 (R19 as reworded): how each format layers comes
  from that format's schema in the kit. The schema names the field that identifies each
  kind of record. A project says which of its files is in which format.

  @AC-formats-1
  Scenario: A schema names the field that identifies each kind of record
    Given the fx-lexicon schema, which identifies an entry by lexeme_id
    And fx-open holds the entry stemA and fx-a adds a sense to stemA, both naming it by lexeme_id
    When the file is composed for fx-a with that schema
    Then the result holds one stemA carrying both senses
    And the added sense is fx-a's

  @AC-formats-2
  Scenario: A list the schema gives no identifier stacks by value
    Given a schema whose senses list has no identifier, and senses held as plain text
    And fx-a adds a sense fx-open lacks and restates one fx-open holds
    When the file is composed for fx-a
    Then the new sense follows fx-open's senses and the restated one appears once

  @AC-formats-3
  Scenario: Under a schema a record must carry its identifier, once in its list
    Given a list the schema identifies by lexeme_id, with a record that lacks lexeme_id or two records that share one
    When the file is composed with that schema
    Then composing stops with an error naming the list and the field

  @AC-formats-4
  Scenario: Under a schema a field called id is an ordinary field
    Given a list the schema identifies by lexeme_id, whose records also carry id
    When the file is composed with that schema
    Then records join on lexeme_id, and two records sharing an id are not an error

  @AC-formats-5
  Scenario: A schema that is malformed is refused
    Given a schema with no format name, a list path that isn't text, or an identifier that isn't a field name
    When the schema is loaded
    Then loading stops with an error naming the schema file

  @AC-formats-6
  Scenario: A project's own map adds formats, and the map is itself layered
    Given fx-open's .lectkit/formats.yaml maps lexicon/fx-nouns.yaml to fx-lexicon
    And fx-a's map adds lexicon/fx-extra.yaml
    When the map is composed for fx-a
    Then both files have a format, and fx-a can't give lexicon/fx-nouns.yaml a different one

  @AC-formats-7
  Scenario: A mapped file names a format the kit has
    Given a project map naming a format the kit has no schema for
    When the map is loaded
    Then loading stops with an error naming the file and the format

  @AC-formats-8
  Scenario: The command composes a file under its format, and refuses a file with none
    Given the kit's fx-lexicon schema claims lexicon/*.yaml
    When a person runs python scripts/compose_layers.py for lexicon/fx-nouns.yaml
    Then records join on the schema's identifier and the command exits 0
    And for a file no pattern claims and no map names, the command says so and exits 1

  @AC-formats-9
  Scenario: The kit's file patterns give a file its format without a project map
    Given the fx-lexicon schema names the pattern lexicon/*.yaml
    When the format of lexicon/fx-nouns.yaml is looked up in a store with no map
    Then it is fx-lexicon

  @AC-formats-10
  Scenario: A project can't move a file out of the format the kit's layout gives it
    Given the kit's pattern puts lexicon/fx-nouns.yaml in fx-lexicon
    And the project's map puts it in another format
    When its format is looked up
    Then the lookup stops with an error naming both formats
    And a map that restates the kit's format is accepted

  @AC-formats-11
  Scenario: Two kit patterns can't claim one file
    Given two schemas whose patterns both match lexicon/fx-nouns.yaml
    When its format is looked up
    Then the lookup stops with an error naming both formats

  @AC-formats-12
  Scenario: The kit defines a store's standard directories
    Given the kit's layout file
    When it is loaded
    Then it names the standard directories, and marks the model directory as one whose every file must have a format
    And a layout file without a path for each directory is refused

  @AC-formats-13
  Scenario: The format check lists every model file without a format
    Given a store whose model directory holds a file the kit claims, a file the store's map names, and a file neither claims
    When a person runs python scripts/check_formats.py for the store
    Then only the unclaimed file is reported, and the command exits 1
    And a store with none unclaimed exits 0
