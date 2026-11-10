Feature: Layered files
  As an agent building a store for one audience
  I want each tier to keep its additions to a file in the same form, at the same path in its own store, composed in the order the register sets
  So that a general view is the same whether or not restricted tiers are loaded, and every added value keeps its own tier

  Carries out knowledge/spec_classification.md, "Layered files".
  There is no overlay format. Where a file sits decides its tier, the tier register
  decides the order, and a higher layer only adds. The merge rule is the same for every
  format, so nothing a lower tier holds can be changed by a tier above it.

  @AC-layered_files-1
  Scenario: An audience's view holds its own layer and the layers it sees, and no others
    Given the file lexicon/fx-nouns.yaml in the stores of fx-open, fx-a, fx-c and fx-p
    And fx-c sees fx-open and fx-a, and fx-p sees only fx-open
    When the file is composed for each audience
    Then fx-open's view holds only the sense stemA-s1
    And fx-c's view holds the senses added by fx-open, fx-a and fx-c
    And fx-p's view holds fx-open's sense and its own stemA-s3, and nothing from fx-a or fx-c

  @AC-layered_files-2
  Scenario: The register sets the order layers are applied in
    Given fx-c sees fx-open and fx-a
    When the file is composed for fx-c
    Then fx-open is applied first, then fx-a, then fx-c
    And the result is the same whatever order the layers were handed over in

  @AC-layered_files-3
  Scenario: A layer the audience can't read is refused
    Given a layer from fx-p, which fx-q doesn't see
    When the file is composed for fx-q
    Then composing stops with an error saying the fx-p layer isn't readable by fx-q

  @AC-layered_files-4
  Scenario: Each record and value takes the tier of the store that added it
    Given fx-open holds the lexeme stemA with sense stemA-s1
    And fx-a adds the sense stemA-s2, a variant of stemA and the lexeme stemB
    And fx-c adds the sense stemB-s2
    When the file is composed for fx-c
    Then the result says stemA and stemA-s1 are fx-open's, stemA-s2, stemB and the added variant are fx-a's, and stemB-s2 with its gloss is fx-c's

  @AC-layered_files-5
  Scenario: A field that names a tier isn't read as the tier
    Given an fx-a layer adding a sense that carries the field tier: fx-open
    When the file is composed for fx-a
    Then the sense is still fx-a's, because fx-a's store added it

  @AC-layered_files-6
  Scenario: A higher layer adds keys, records and list items
    Given a higher layer with a key the lower layer lacks, a record with a new id, a new plain value in a list, or a new mapping without an id in a list
    When the file is composed
    Then each is added after what the lower layer holds
    And a record whose id matches a lower record is merged into it

  @AC-layered_files-7
  Scenario: A higher layer can't change a value a lower layer holds
    Given a higher layer that gives a different value to a key a lower layer holds, gives it a value of a different type (such as true where the lower layer has 1, or a list where it has a mapping), or replaces an empty value with text
    And likewise a higher layer whose whole file isn't in the same form as the layer below it
    When the file is composed
    Then composing stops with an error

  @AC-layered_files-8
  Scenario: Restating an equal value adds nothing
    Given a higher layer that repeats a value, a list item or an empty value exactly as the lower layer holds it
    When the file is composed
    Then the value appears once, as the lower layer has it

  @AC-layered_files-9
  Scenario: Composing leaves the lower layer as it was
    Given the fx-open layer of a file
    When the file is composed for fx-a
    Then the fx-open layer is unchanged

  @AC-layered_files-10
  Scenario: Ids are text or whole numbers, unique within their list
    Given a list where two records share an id, or a record whose id is true or a list
    When the file is composed
    Then composing stops with an error

  @AC-layered_files-11
  Scenario: A higher layer finds a renamed record through replaces
    Given fx-open holds stemN, which lists stemOld under replaces
    And fx-a adds a sense to stemOld
    When the file is composed for fx-a
    Then the result holds only stemN, carrying fx-a's added sense
    And the added sense is fx-a's

  @AC-layered_files-12
  Scenario: A replaces list that conflicts is an error
    Given a replaces list naming an id a record in the same list still uses, an id two records both claim, or a value that isn't an id
    When the file is composed, from one layer or from several
    Then composing stops with an error

  @AC-layered_files-13
  Scenario: A higher layer can't add replaces to a record a lower layer holds
    Given fx-open holds the record x
    And fx-a gives x a replaces list
    When the file is composed for fx-a
    Then composing stops with an error saying fx-a can't add replaces

  @AC-layered_files-14
  Scenario: The command writes the composed view and, on request, each value's tier
    Given the stores of fx-open, fx-a and fx-c each hold lexicon/fx-nouns.yaml
    When a person runs python scripts/compose_layers.py for audience fx-c with --out and --origin
    Then the output file holds the senses from all three layers
    And the error stream lists each added value with its tier, such as stemB-s2 under fx-c
    And the command exits 0

  @AC-layered_files-15
  Scenario: An absent store is reported, never passed
    Given a store that fx-c reads is not on this machine
    When a person runs python scripts/compose_layers.py for fx-c
    Then the absent store is reported and the command exits 2
    And if no store that is present holds the file, the command says so and exits 1

  @AC-layered_files-16
  Scenario: The file path must stay inside the store
    Given a --rel path that climbs out of the store, or is absolute
    When a person runs python scripts/compose_layers.py
    Then the command refuses it and exits 1

  @AC-layered_files-17
  Scenario: Files are read strictly
    Given a file with a repeated key, words such as no and on, a date, true, or broken YAML
    When the file is read
    Then the repeated key and the broken YAML are errors
    And no and on stay text, the date stays text, and only true is a boolean

  @AC-layered_files-18
  Scenario: A file that can't be read stops the command, and the error stays out of the output
    Given a layer file with a repeated key, or bytes that aren't text
    When a person runs python scripts/compose_layers.py
    Then the error is written to the error stream, nothing is written as output, and the command exits 1
