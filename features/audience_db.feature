Feature: An audience's database of everything it can see
  As a project custodian whose community holds material at several tiers
  I want each audience to build one database of everything it can see, with the tier of every value
  So that a leak scanner can find restricted material that was described or copied into a lower store, not only material that names a restricted term

  Carries out knowledge/spec_classification.md, "Audience database", and the part of
  "Builds are per audience" that says each audience gets its own copy.

  The database holds readable restricted text, so it is as restricted as its audience
  and is built only on request, outside every store and every git working tree, and is
  never kept. A term register catches material that names a restricted thing; this
  database is what lets a scanner catch material that describes one, or copies it.

  @AC-audience_db-1
  Scenario: The database reads the audience's own store and the stores it sees, and no other
    Given a register where tier C sees the open tier and tier A, and tier P sees only the open tier
    When the database is built for audience C
    Then it reads the open, A and C stores, lowest first
    And nothing from tier P's store is in it

  @AC-audience_db-2
  Scenario: A store the audience sees that isn't on this machine stops the build
    Given the audience sees tier A and tier A's store is absent
    When the database is built
    Then the build stops with an error naming tier A as not on this machine

  @AC-audience_db-3
  Scenario: Every line and value is kept as source with its store, file and line
    Given the same value written in the open store and in tier A's store
    When the database is built
    Then the source view holds it once for each store, with that store's tier, the file's relative path and the line number

  @AC-audience_db-4
  Scenario: Model material is credited to every tier whose copy writes it
    Given a sense written in the open store and written again unchanged by tier A, and a new sense tier A adds
    When the database is built
    Then the repeated sense is model material of the open tier and of tier A, since a higher tier never restates
    And the new sense is model material of tier A, pointing at the line in tier A's file that writes it
    And numbers, ids, comments and short notes that tier C adds are model material of tier C

  @AC-audience_db-5
  Scenario: A mapping key is recorded at the tier that added it
    Given tier C adds a key to an entry that a lower tier holds, and keys of its own in a file only it has
    When the database is built
    Then each of those keys is model material of tier C, at the line that writes it

  @AC-audience_db-6
  Scenario: Lookups don't depend on case
    Given tier C holds a value in lower case
    When the value is looked up in upper case
    Then it is found as model material of tier C

  @AC-audience_db-7
  Scenario: A text file held at several tiers is layered line by line
    Given the open store and tier C both hold a note at the same path, and tier C's copy adds one line
    When the database is built
    Then the shared line is model material of the open tier and of tier C
    And the added line is model material of tier C only

  @AC-audience_db-8
  Scenario: Passages of five words are kept, even when they wrap across lines
    Given a sentence tier A adds, and a note whose sentence wraps across two lines
    When the database is built
    Then each run of five consecutive words is held as a passage with the tier of the value it came from
    And a run that crosses the line break is held too

  @AC-audience_db-9
  Scenario: A "#" inside a quoted or block value isn't a comment
    Given a YAML file with a real comment, a quoted value containing "#", and a block value with a line starting "#"
    When the database is built
    Then only the real comment is recorded as a comment

  @AC-audience_db-10
  Scenario: Lines with no letter or digit aren't material
    Given a note with a frontmatter fence, a table rule and an ordinary line
    When the database is built
    Then the fence and the rule are kept as source but aren't model material
    And the ordinary line is model material

  @AC-audience_db-11
  Scenario: The audience's own kit folder isn't read
    Given the audience's store and a lower store each hold a file in their .lectkit/ folder
    When the database is built
    Then nothing from the audience's own .lectkit/ is in it
    And the lower store's .lectkit/ file is read like any other file

  @AC-audience_db-12
  Scenario: The database records a digest of each store it read
    Given a database built for audience C
    When a file in tier A's store changes, or tier A changes its not_material.txt list, and the database is rebuilt
    Then there is one digest for each store read
    And only tier A's digest changes

  @AC-audience_db-13
  Scenario: A tier's own list of what isn't its material
    Given tier C lists a note in .lectkit/not_material.txt, and the open tier lists its README in its own list
    When the database is built
    Then tier C's note is kept as source but isn't model material, and the rest of tier C's files are
    And the open tier's README is still kept as source
    And the list itself isn't model material

  @AC-audience_db-14
  Scenario: Exclusion patterns are read like .gitignore, and unclear syntax is an error
    Given patterns in a not_material.txt list
    When they are read
    Then a bare name matches at any depth, a leading "/" anchors to the top, "**" spans folders, and a trailing "/" means a folder
    And comment lines and blank lines are ignored
    And a pattern with "!", "[ ]", a backslash or a "#" after the start of the line is an error

  @AC-audience_db-15
  Scenario: Short values of the tier's structure fields aren't material
    Given tier C lists "status" in .lectkit/structure.yaml
    And tier C's files hold short and long status values, and a status line in closed and in unclosed frontmatter
    When the database is built
    Then a status value of three words or fewer isn't model material, but is still kept as source
    And a longer status value, and other fields, are model material
    And the status line in closed frontmatter isn't model material, and in an unclosed fence it is

  @AC-audience_db-16
  Scenario: A term register's terms and keys aren't material, but its labels are
    Given tier C names a term register in the register file, holding a term, a variant and a label
    When the database is built
    Then the term, the variant and the register's keys aren't model material, but are kept as source
    And the label is model material of tier C

  @AC-audience_db-17
  Scenario: Every table and every row carries a tier the audience reads
    Given a database built for audience C
    Then every table has a tier column that can't be empty, and every row's tier is one of the tiers read
    And every passage has the tier of the value it was cut from
    And the database as a whole is classified as audience C
    When a row of an unread tier is added, or a passage's tier is changed, and the database is opened
    Then opening it fails

  @AC-audience_db-18
  Scenario: A lower store that copies material added above is a candidate leak
    Given the open store has a file holding one value tier C added and one key both tiers write
    When the database is queried for open-store values that equal tier C's material, leaving out keys the open tier also uses
    Then only the line with tier C's added value is found, by file and line

  @AC-audience_db-19
  Scenario: A store that is a git checkout holds what git holds
    Given tier C's store is its own git checkout, with an ignored folder holding a binary file and a new file that isn't ignored
    When the database is built
    Then the build succeeds, the ignored folder isn't read, and the new file is model material of tier C

  @AC-audience_db-20
  Scenario: A symbolic link in a store stops the build
    Given tier C's store holds a symbolic link
    When the database is built
    Then the build stops with an error saying symbolic links aren't allowed in a store

  @AC-audience_db-21
  Scenario: A YAML file holding more than one document stops the build
    Given tier C's store holds a YAML file holding two documents
    When the database is built
    Then the build stops with an error saying the file holds more than one YAML document

  @AC-audience_db-22
  Scenario: An unreadable file stops the build, naming the file and never its content
    Given one of these: tier C holds a file that isn't UTF-8 text, a YAML file that doesn't parse, or one with a duplicated key, or tier A's copy of a layered file doesn't compose with the open tier's
    When the database is built
    Then the build stops with an error naming the file and none of its content
    And no database, finished or partial, is left at the output path

  @AC-audience_db-23
  Scenario: Media files are counted and left out
    Given tier C's store holds an image file
    When the database is built
    Then the build succeeds, reports one media file skipped, and records the image's store and path as skipped

  @AC-audience_db-24
  Scenario: The database can't be written inside a store or a git working tree
    Given an output path inside any store in the register, or inside a git working tree
    When the database is built
    Then the build stops with an error saying where the path lies

  @AC-audience_db-25
  Scenario: The build command prints counts only
    Given a register and its stores
    When "python scripts/build_audience_db.py --register REG --audience fx-c --out FILE" is run
    Then it exits 0 and prints a "[BUILT] fx-c" line of counts, with no stored material
    And rebuilding while the database is open either succeeds or exits 1, leaving no temporary file behind

  @AC-audience_db-26
  Scenario: An aliased value is recorded once, at its anchor's line
    Given tier C's store holds a YAML file where a value is given an anchor and used again through an alias
    When the database is built
    Then the build succeeds and reads each alias as its anchor's content
    And that content is recorded once, at the anchor's line, not again where the alias is used
    # A tier's files go into its store as they were written, and some of them use aliases.
