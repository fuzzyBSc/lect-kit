Feature: Knowledge checks
  As an agent about to commit a change to knowledge/ or schemes/
  I want checkers for the frontmatter profile, the citations and the identifiers
  So that a person checking agent knowledge can trust its labels and follow its sources

  Carries out knowledge/README.md, "Frontmatter (Open Knowledge Format)".
  Also carries out the citation rule under "Gardening rules" and the rule under
  "Identifiers" in the same file. Each checker prints one error per problem with the
  file it found it in, then a count, and exits 1 if it found any.

  @AC-knowledge_checks-1
  Scenario: A knowledge file that follows the frontmatter profile passes
    Given a knowledge file with a valid type, title, description, tags, status, generated, verified, sources and stale_after
    When the frontmatter checker runs
    Then it exits 0 and reports no problems in one file

  @AC-knowledge_checks-2
  Scenario: A knowledge file with no frontmatter fails
    Given a knowledge file that does not open with a frontmatter block
    When the frontmatter checker runs
    Then it exits 1 and reports that the file has no frontmatter

  @AC-knowledge_checks-3
  Scenario: Each missing required key is reported
    Given a knowledge file whose frontmatter has none of type, title and description
    When the frontmatter checker runs
    Then it reports each of the three keys as missing

  @AC-knowledge_checks-4
  Scenario: A key outside the profile is reported
    Given a knowledge file whose frontmatter has a key the profile doesn't list
    When the frontmatter checker runs
    Then it reports the unknown key

  @AC-knowledge_checks-5
  Scenario: A type outside the profile is reported
    Given a knowledge file whose type is not one of the profile's types
    When the frontmatter checker runs
    Then it reports that the type is not in the profile

  @AC-knowledge_checks-6
  Scenario: A title must be a short phrase with no trailing full stop
    Given a knowledge file whose title ends in a full stop, is blank, or is not text
    When the frontmatter checker runs
    Then it reports the title

  @AC-knowledge_checks-7
  Scenario: A description must be one sentence ending in a full stop
    Given a knowledge file whose description has no full stop, holds two sentences, or is longer than 220 characters
    When the frontmatter checker runs
    Then it reports the description

  @AC-knowledge_checks-8
  Scenario: Tags must be at most four from the profile's list
    Given a knowledge file with five tags, a tag outside the list, or tags that are not a list
    When the frontmatter checker runs
    Then it reports the tags

  @AC-knowledge_checks-9
  Scenario: A status outside draft, stable and deprecated is reported
    Given a knowledge file whose status is not draft, stable or deprecated
    When the frontmatter checker runs
    Then it reports the status

  @AC-knowledge_checks-10
  Scenario: Generated names an agent or human actor and a datetime with an offset
    Given a knowledge file whose generated entry has an extra key, an actor with no agent or human prefix, or a time with no offset
    When the frontmatter checker runs
    Then it reports what is wrong with the generated entry

  @AC-knowledge_checks-11
  Scenario: Only a person can verify a knowledge file
    Given a knowledge file whose verified list has an entry by an agent actor
    When the frontmatter checker runs
    Then it reports that verified must be by a human actor

  @AC-knowledge_checks-12
  Scenario: Each source names a resource and at most an id
    Given a knowledge file whose sources list has an entry with no resource, an extra key, or plain text
    When the frontmatter checker runs
    Then it reports the sources entries

  @AC-knowledge_checks-13
  Scenario: Stale-after must be a datetime with an offset
    Given a knowledge file whose stale_after is a date with no time or a time with no offset
    When the frontmatter checker runs
    Then it reports stale_after

  @AC-knowledge_checks-14
  Scenario: Files in folders under knowledge/ are checked too
    Given a knowledge file with no frontmatter in a folder under knowledge/
    When the frontmatter checker runs
    Then it reports that file by its path

  @AC-knowledge_checks-15
  Scenario: A spec that cites an existing principle and an existing docs page passes
    Given a principles file with sections 1 and 2, a docs page, and a spec citing section 1 and that page
    When the citation checker runs
    Then it exits 0 and reports no problems

  @AC-knowledge_checks-16
  Scenario: A citation of a principle that doesn't exist is reported
    Given a knowledge file citing a section number the principles file doesn't have
    When the citation checker runs
    Then it exits 1 and reports the section that doesn't exist

  @AC-knowledge_checks-17
  Scenario: A spec or procedure must cite at least one principle
    Given a spec and a procedure that cite no principle
    When the citation checker runs
    Then it reports each as citing no principles section

  @AC-knowledge_checks-18
  Scenario: Other knowledge files needn't cite a principle
    Given a knowledge file that is neither a spec nor a procedure and cites nothing
    When the citation checker runs
    Then it exits 0

  @AC-knowledge_checks-19
  Scenario: A citation can list several sections
    Given a principles file with sections 1, 2 and 3, and a procedure citing "§1, §2 and §4"
    When the citation checker runs
    Then it reports only section 4 as missing

  @AC-knowledge_checks-20
  Scenario: A spec must name a docs page
    Given a spec that cites a principle but names no docs page
    When the citation checker runs
    Then it reports that the spec names no docs page

  @AC-knowledge_checks-21
  Scenario: A docs page a spec names must exist
    Given a spec that names a docs page that isn't there
    When the citation checker runs
    Then it reports the page that doesn't exist

  @AC-knowledge_checks-22
  Scenario: Valid scheme and label identifiers pass
    Given a scheme file whose scheme and label ids use only letters, digits, underscores and hyphens and don't start with a digit
    When the identifier checker runs
    Then it exits 0 and reports no problems

  @AC-knowledge_checks-23
  Scenario: Display fields may hold any text
    Given a scheme file whose labels have valid ids and a code and name with spaces and punctuation
    When the identifier checker runs
    Then it exits 0

  @AC-knowledge_checks-24
  Scenario: An invalid scheme identifier is reported
    Given a scheme file whose scheme starts with a digit or holds a space, or a scheme file with no scheme
    When the identifier checker runs
    Then it exits 1 and reports the scheme as not a valid identifier

  @AC-knowledge_checks-25
  Scenario: An invalid label identifier is reported
    Given a scheme file with a label whose id holds a space or is missing
    When the identifier checker runs
    Then it reports that label's position and id as not a valid identifier

  @AC-knowledge_checks-26
  Scenario: A label identifier used twice is reported
    Given a scheme file with two labels sharing one id
    When the identifier checker runs
    Then it reports the duplicate id

  @AC-knowledge_checks-27
  Scenario: Frontmatter that isn't a mapping of keys is reported
    Given a knowledge file whose frontmatter is a list, and another whose frontmatter isn't valid YAML
    When the frontmatter checker runs
    Then it reports each file as having frontmatter that isn't a mapping or can't be read
    And it goes on to check the other files

  @AC-knowledge_checks-28
  Scenario: An empty identifier, or one that isn't text, is reported
    Given a scheme file whose scheme is empty and whose labels have an empty id and an id of true
    When the identifier checker runs
    Then it reports the scheme and both label ids as not valid identifiers
    And a word such as no is read as the text written, and passes

  @AC-knowledge_checks-29
  Scenario: A scheme file that isn't laid out as expected is reported
    Given a scheme file that is a list, one whose label is plain text, one with a repeated key, and one that isn't valid YAML
    When the identifier checker runs
    Then it reports each of them by file, and the label by position, and checks the rest

  @AC-knowledge_checks-30
  Scenario: Citation rules apply in subfolders of knowledge/ too
    Given a spec in a subfolder of knowledge/ that cites no PRINCIPLES.md section
    When the citation checker runs
    Then it reports that spec by its path

  @AC-knowledge_checks-31
  Scenario: Labels that aren't a list are reported
    Given a scheme file whose labels is a number, a word or a mapping
    When the identifier checker runs
    Then it reports that labels must be a list, once, and checks the other files

  @AC-knowledge_checks-32
  Scenario: Only valid identifiers are compared for duplicates
    Given a scheme file with two labels that have no id, and a label whose id is a list
    When the identifier checker runs
    Then each is reported as not a valid identifier, and none as a duplicate

  @AC-knowledge_checks-33
  Scenario: Frontmatter values of the wrong shape are reported, not a crash
    Given knowledge files whose type or status is a list, whose tags hold a list, or whose verified or sources is a number
    When the frontmatter checker runs
    Then it reports each wrong value and checks every file

  @AC-knowledge_checks-34
  Scenario: Frontmatter is read strictly
    Given a knowledge file whose frontmatter gives the same key twice
    When the frontmatter checker runs
    Then it reports that the frontmatter can't be read, rather than keeping one of the values

