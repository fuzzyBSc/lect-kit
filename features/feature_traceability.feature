Feature: Feature traceability
  As a project custodian reviewing an agent's work
  I want a check that every scenario is tested and every test names a scenario
  So that each test and piece of code answers a stated need I can read

  Carries out knowledge/feature_procedure.md, "Checks".
  Scenarios are tagged in features/ and tests name those tags in their docstrings. The
  check reads both and reports each broken link by file and line or by test name, then
  a count, and exits 1 if it found any.

  @AC-feature_traceability-1
  Scenario: A tree where every scenario is tested and every test names one passes
    Given a feature file with one tagged scenario and a test whose docstring names that tag
    When the traceability check runs on that tree
    Then it exits 0 and reports no problems, one scenario and one test

  @AC-feature_traceability-2
  Scenario: A feature file whose name isn't a key is reported
    Given a feature file whose name holds a capital letter or a hyphen
    When the traceability check runs
    Then it reports that the file name isn't a key and reads no scenarios from it

  @AC-feature_traceability-3
  Scenario: A feature file with no Feature line is reported
    Given a feature file with tagged scenarios but no Feature line
    When the traceability check runs
    Then it reports that the file has no Feature line

  @AC-feature_traceability-4
  Scenario: A scenario with no tag is reported
    Given a scenario with no tag above it
    When the traceability check runs
    Then it reports the scenario's file and line as having no tags

  @AC-feature_traceability-5
  Scenario: A scenario with more than one tag is reported
    Given a scenario with two tags above it, on one line or on two
    When the traceability check runs
    Then it reports the scenario's file and line as having two tags, not one

  @AC-feature_traceability-6
  Scenario: A tag with another file's key is reported
    Given a scenario in one feature file tagged with another file's key
    When the traceability check runs
    Then it reports that the tag doesn't use this file's key

  @AC-feature_traceability-7
  Scenario: A tag used on two scenarios is reported
    Given two scenarios in one file carrying the same tag
    When the traceability check runs
    Then it reports the second as already used at the first one's line

  @AC-feature_traceability-8
  Scenario: A scenario no test names is reported
    Given a tagged scenario that no test's docstring names
    When the traceability check runs
    Then it reports the scenario's file and line and says no test names its tag

  @AC-feature_traceability-9
  Scenario: A test that names no tag is reported
    Given a test function with no docstring, and one whose docstring names no tag
    When the traceability check runs
    Then it reports each test by file and name as naming no tag

  @AC-feature_traceability-10
  Scenario: A test that names a tag no scenario has is reported
    Given a test whose docstring names a tag that no feature file has
    When the traceability check runs
    Then it reports the test and the tag no scenario has

  @AC-feature_traceability-11
  Scenario: Comments and blank lines between a tag and its scenario keep the tag
    Given a tag followed by a comment and a blank line and then a scenario
    And a tag followed by a line of other text and then a scenario
    When the traceability check runs
    Then the first scenario has its tag
    And for the second, the tag is reported as not on a scenario and the scenario as having none

  @AC-feature_traceability-12
  Scenario: Outlines, templates and examples count as scenarios
    Given tagged scenarios written as a Scenario Outline, a Scenario Template and an Example
    When the traceability check runs
    Then each is read as a scenario with its tag

  @AC-feature_traceability-13
  Scenario: Only a test's docstring names its tags
    Given a test whose docstring names no tag but whose body holds a tag in a comment and a string
    When the traceability check runs
    Then it reports the test as naming no tag, and the tag in its body as tested by no one

  @AC-feature_traceability-14
  Scenario: Test methods in classes and async tests are read, and helpers inside a test aren't
    Given a test method in a test class and an async test function, each naming a tag
    And a function named like a test defined inside another test
    When the traceability check runs
    Then the method and the async test are counted and their tags are tested
    And the function inside the test isn't counted as a test

  @AC-feature_traceability-15
  Scenario: The check runs from the command line on a chosen root
    Given a repository tree with a broken link
    When the script is run from the command line with that tree as its root
    Then its exit status is 1

  @AC-feature_traceability-16
  Scenario: A test file that can't be read as Python is reported
    Given a test file with a syntax error
    When the traceability check runs
    Then it reports the file and the line of the error, and still checks every other file

  @AC-feature_traceability-17
  Scenario: Text that only starts like a tag isn't one
    Given a tag line holding AC-fx_a-1-extra after the at sign
    And a test docstring holding the same text
    When the traceability check runs
    Then the tag line is reported as holding text that isn't a tag
    And the docstring names no tag

  @AC-feature_traceability-18
  Scenario: A tag that isn't on a scenario is reported
    Given a tag above a Feature, Rule, Background or Examples line
    When the traceability check runs
    Then it reports the tag's file and line as not on a scenario

  @AC-feature_traceability-19
  Scenario: The same tag twice on one scenario is reported once
    Given a scenario whose tag line repeats its one tag
    When the traceability check runs
    Then it reports the scenario as having 2 tags, and nothing else about that tag

  @AC-feature_traceability-20
  Scenario: A step's doc string isn't read for tags or scenarios
    Given a step with a doc string holding a line that starts with an at sign and a line starting "Scenario:"
    When the traceability check runs
    Then neither line is read as a tag or a scenario

  @AC-feature_traceability-21
  Scenario: Tests are found the way pytest finds them
    Given a test inside a module-level if block, a test method in a class named Test-something
    And a test-named method in a helper class whose name doesn't start with Test
    When the traceability check runs
    Then the first two are read as tests and the helper's method isn't

