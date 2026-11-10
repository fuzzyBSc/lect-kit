Feature: Cross-tier scan of lower stores
  As the holder of a higher tier
  I want every lower store my tier can read checked for material its readers mustn't see
  So that the community learns of a leak of its restricted material before it spreads,
  without the report itself repeating what was leaked

  Carries out knowledge/spec_classification.md, "Cross-tier scan", with the parts of
  "Audience database" that say what a tier's material is (files a tier excludes, structure
  fields and term registers).

  The scan runs on the higher tier's audience database. A finding names a tier, a file and
  a line, never the text. Deciding what a finding means is a person's job, so nothing here
  is exempted unless a person of the tier that holds the material has said so; see
  scan_review.feature for those decisions.

  @AC-cross_tier_scan-1
  Scenario: Lower stores that copy nothing hidden give no findings
    Given a database built for fx-c, which holds the stores of fx-open, fx-a and fx-c
    And fx-open and fx-a copy nothing that only higher tiers hold
    When fx-c runs the scan
    Then the report says it scanned fx-open and fx-a
    And it lists no open findings

  @AC-cross_tier_scan-2
  Scenario: A line that equals hidden material is a value match
    Given fx-c's lexicon has a gloss that fx-open's readers can't see
    And a note in fx-open has a line that is exactly that gloss
    When fx-c runs the scan
    Then that line of the note is the only finding, and its kind of match is "value"

  @AC-cross_tier_scan-3
  Scenario: A hidden id inside a longer line is a token match
    Given fx-c's lexicon has a sense id stemB-s1
    And a note in fx-open says "see stemB-s1 here"
    When fx-c runs the scan
    Then that line is a finding of kind "token" that names fx-c as the tier whose material matched

  @AC-cross_tier_scan-4
  Scenario: A five-word passage that wraps across lines still matches
    Given fx-a's lexicon has a gloss of six words that fx-open can't see
    And a note in fx-open has five of those words in order, split over two lines
    When fx-c runs the scan
    Then the line where the passage starts is a finding of kind "passage" naming fx-a

  @AC-cross_tier_scan-5
  Scenario: Prose is matched whole or by passage, not looked for inside other lines
    Given a note in fx-c has the line "fxheadq rules"
    When a note in fx-open has a longer line containing those two words
    Then the scan reports nothing for that line
    But when the fx-open line is exactly "fxheadq rules" the scan reports it

  @AC-cross_tier_scan-6
  Scenario: Field names a higher tier shares with lower stores aren't exempted on their own
    Given fx-c's new record uses the field name "senses", which fx-open's lexicon also uses
    And no person of fx-c has decided about it
    When fx-c runs the scan
    Then fx-open's "senses" line is a finding
    And so is fx-open's "entries" line, since a higher tier never restates: what fx-c's copy writes is fx-c's material

  @AC-cross_tier_scan-7
  Scenario: A lower store can't exempt a restricted key by using it
    Given fx-c's lexicon has a key that fx-open can't see
    And fx-open uses that same key in a YAML file of its own and in a note
    When fx-c runs the scan
    Then both lines in fx-open are findings

  @AC-cross_tier_scan-8
  Scenario: Every hidden tier that holds the matched text is named, most restrictive first
    Given one line in fx-open matches material from both fx-a and fx-c
    When fx-c runs the scan
    Then that line's finding names fx-c then fx-a

  @AC-cross_tier_scan-9
  Scenario: A lower store's kit folder is scanned like any other folder
    Given fx-open has a file under its own .lectkit/ folder holding hidden fx-c material
    When fx-c runs the scan
    Then that file's line is a finding

  @AC-cross_tier_scan-10
  Scenario: A higher tier's other kit files are still its material
    Given fx-a has a note under its .lectkit/ folder that isn't one of its decision files
    And a note in fx-open copies a line of it
    When fx-c runs the scan
    Then the fx-open line is a finding

  @AC-cross_tier_scan-11
  Scenario: A tier's grant file is its material, and what it grants is released
    Given fx-a's .lectkit/accepted_matches.yaml grants fx-open a text that is a whole line
    And a note in fx-open has exactly that line
    When fx-c runs the scan
    Then the fx-open line matches fx-a material, from the grant file itself
    And it is accepted only for fx-open and the tiers that see it, because a text is granted only where the higher tier grants it (project custodian's ruling, 2026-11-09)

  @AC-cross_tier_scan-12
  Scenario: The scan refuses a database whose stores have changed since it was built
    Given a database built for fx-c
    When a file in fx-open changes, a file is added to fx-open's .lectkit/ folder, or fx-a's .lectkit/structure.yaml is written
    Then the scan stops with an error saying a store has changed since the build
    And from the command line scan_tiers.py exits with code 3

  @AC-cross_tier_scan-13
  Scenario: A higher tier decides which of its own files aren't its material
    Given fx-c lists its README in its .lectkit/not_material.txt and keeps a note in its lexicon
    And fx-open lists its own note in its .lectkit/not_material.txt
    And fx-open's note copies one line from fx-c's README and one from fx-c's lexicon note
    When fx-c runs the scan
    Then only the line copied from the lexicon note is a finding
    And fx-open's own list changes nothing about how its note is screened

  @AC-cross_tier_scan-14
  Scenario: Short values under a tier's structure fields aren't its material
    Given fx-c lists status, type and tags in its .lectkit/structure.yaml
    And fx-c has a record with a status value and an ordinary field value
    And a note in fx-c has a frontmatter block with a type line and a title line
    When fx-open has lines copying each of those four
    Then the status value and the frontmatter type line aren't findings
    And the ordinary field value and the title line are

  @AC-cross_tier_scan-15
  Scenario: Long values under structure fields, and unclosed frontmatter, are still material
    Given fx-c lists type and tags in its .lectkit/structure.yaml
    And fx-c has a short type value, a tag, and a sentence-long value under a type field
    And a note in fx-c opens a frontmatter block that is never closed
    When fx-open has lines copying each of them
    Then the short type value and the tag aren't findings
    And the long value and the line from the unclosed block are

  @AC-cross_tier_scan-16
  Scenario: A lower store's structure list doesn't change how it is screened
    Given fx-open lists a field in its own .lectkit/structure.yaml
    And fx-open has a line under that field holding hidden fx-c material
    When fx-c runs the scan
    Then that line is a finding

  @AC-cross_tier_scan-17
  Scenario: A tier's term register is applied as rules
    Given fx-c's register names a term register with a variant, a pattern and a label
    And a note in fx-open has a line with the variant, a line the pattern fits, and a line equal to the label
    When fx-c runs the scan
    Then the variant and pattern lines are findings of kind "term"
    And the label line is a finding of kind "value", because a label stays material

  @AC-cross_tier_scan-18
  Scenario: A term register's patterns, guards and keys aren't screened as text
    Given fx-c's term register has a pattern, a suffix guard and a key of its own format
    When fx-c's database is built
    Then none of the pattern, the guard or the key is fx-c material
    But a label in the register is

  @AC-cross_tier_scan-19
  Scenario: A missing term register stops the scan
    Given fx-c's register names a term register file that doesn't exist
    When fx-c runs the scan
    Then the scan stops with an error saying the register is missing

  @AC-cross_tier_scan-20
  Scenario: The printed report names where, never what
    Given a note in fx-open has a line with fx-c's sense id stemB-s1
    When fx-c runs scan_tiers.py
    Then it prints a MATCH line with a 12-character id, "fx-open: fx-notes.md:2: token matches fx-c material"
    And no hidden or matched text appears anywhere in the output
    And it exits with code 1

  @AC-cross_tier_scan-21
  Scenario: A report is never written into a lower store
    Given a scan that has findings
    When scan_tiers.py is given --out in fx-open's store, or in fx-c's store outside its .lectkit/ folder
    Then it exits with code 3, and no report appears in fx-open's store
    But --out under fx-c's .lectkit/ folder, or outside every store, is allowed and the scan exits with code 1

  @AC-cross_tier_scan-22
  Scenario: Accepted findings are counted, and listed only on request
    Given every match in the lower stores has been accepted by the tier whose material it is
    When fx-c runs scan_tiers.py
    Then it exits with code 0, lists no findings, and counts them as accepted
    And with --show-accepted it lists each of them marked ACCEPTED

  @AC-cross_tier_scan-23
  Scenario: A bad accept file stops the scan
    Given fx-c's .lectkit/accepted_matches.yaml has an entry missing its tier, reason, by or at, isn't a list, names an unknown tier, or is in the retired batch shape
    When fx-c runs the scan
    Then the scan stops with an error
    And from the command line scan_tiers.py exits with code 3

  @AC-cross_tier_scan-24
  Scenario: A field name or enumeration value the kit's schema declares needs no grant
    Given lect-kit's schema declares the field fxpos with the enumeration values fxnoun and fxverb
    And fx-c's lexicon uses the key fxpos with the value fxnoun
    And fx-open writes fxpos and fxnoun as a key and a value, and fxnoun again in a line of prose
    When fx-c's audience database is built and fx-c runs the scan
    Then fx-open's key and value lines are not held
    But fx-open's prose line that contains fxnoun is held, because a word in prose is material

  @AC-cross_tier_scan-25
  Scenario: lect-kit can't declassify a word that a tier treats as material
    Given lect-kit's schema declares a field name or an enumeration value
    And a higher tier's term register matches that word, or the tier writes it as an identifier
    When any audience database is built
    Then the build stops with an error that names the format word and the tier, and never the tier's term

  @AC-cross_tier_scan-26
  Scenario: A tier's name passes to a lower tier only by explicit grant
    Given fx-c writes its own tier name as a value in one of its files
    And a note in fx-open has that name on a line
    When the scan runs
    Then the fx-open line is held, because the name is fx-c's material like any other
    And once fx-c grants the name to fx-open, the line is accepted (project custodian's ruling, 2026-11-09)
    And lect-kit's schemas name no project's tiers: a classification is any tier of the project's register

  @AC-cross_tier_scan-27
  Scenario: A grant lives in the granting tier and goes only to a tier below it
    Given a tier's accepted-matches or reviewed-findings file names a tier it does not see, or itself
    When any scan reads that file
    Then the scan stops with an error naming the file's tier and the tier it wrongly names
    And a lower tier can never grant or review a higher tier's material, because each tier's grants are read only from its own store and only for its own material

  @AC-cross_tier_scan-28
  Scenario: A grant to a tier holds for every tier that sees it
    Given fx-c grants a text to fx-open
    And fx-a, which sees fx-open, has a line with that text
    When the scan runs
    Then the fx-a line is accepted, because what fx-open holds, fx-a can already read

  @AC-cross_tier_scan-29
  Scenario: A value in a field typed for it, such as a hash, is not material
    Given lect-kit's schema declares a field whose type it marks not material, with a pattern, such as digest
    When a tier writes a value that fits the pattern, such as a reviewed line's sha256
    Then the value is format and holds nothing below
    But any other text in that field, or the same value in any other field, is material as usual

  @AC-cross_tier_scan-30
  Scenario: Every tier may name itself
    Given fx-c writes fx-open's tier name in one of its files
    And a note in fx-open has its own tier name on a line
    When the scan runs
    Then the fx-open line is accepted without a grant, because a tier's own name is in the register (project custodian's ruling, 2026-11-09)
    But fx-open writing fx-c's name is still held until fx-c grants it

  @AC-cross_tier_scan-31
  Scenario: A shared list is granted by version in one line
    Given lect-kit holds a shared list fxwords-v1 with an entry that fx-c also holds
    And a note in fx-open has that entry on a line
    When fx-c grants fx-open the item list:fxwords-v1
    Then the fx-open line is accepted, as if fx-c had granted each entry (project custodian's ruling, 2026-11-09)
    But a grant naming a list lect-kit doesn't hold stops the scan

  @AC-cross_tier_scan-32
  Scenario: lect-kit can't release a restricted word through a shared list
    Given a tier's term register matches an entry of a shared list
    When any audience database is built
    Then the build stops with an error naming the list, the entry's line and the tier, and never the term

  @AC-cross_tier_scan-33
  Scenario: A screening-only tier holds no prose
    Given the register marks fx-c scope: screening
    When fx-c's staged files hold a comment, a prose field in a term entry, or a note file
    Then fx-c's commit is refused, naming each file and line but never its text (project custodian's rulings, 2026-11-09)
    But term entries with matching keys only, paradigm layer rows, kit files and files the tier excludes pass

  @AC-cross_tier_scan-34
  Scenario: A run of single letters is never a token match
    Given fx-c's material holds the phoneme pair "n i" as a value
    And an fx-open line of code reads index(b"\n", i)
    When fx-c runs the scan
    Then that line is not a finding, since its words "n" and "i" are single letters
    But an fx-open line whose whole value is "n i" is still a finding

  @AC-cross_tier_scan-35
  Scenario: Hashes and date-times are format, never material
    Given fx-c's material holds the value "0930" and a word "fxzone"
    And an fx-open line carries a git timestamp "1794302574 +0930", a hash and an ISO date-time
    When fx-c runs the scan
    Then the scan matches the line with those shapes masked, and it is no finding
    But a plain "0930" on its own is still a finding, and so is "fxzone" beside a hash

  @AC-cross_tier_scan-36
  Scenario: A passage never runs across a table's cell borders
    Given fx-c's material holds a table row "| fxvar | alpha beta gamma delta |"
    And an fx-open line reads "fxvar alpha beta gamma delta"
    When fx-c runs the scan
    Then that line is not a passage finding, since the run joins two cells
    But an fx-open line repeating five words from inside one fx-c cell is still a finding
