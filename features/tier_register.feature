Feature: Tier register
  As a project custodian setting up tiers
  I want one register file that says each tier, who reads what, and where it is stored, checked for consistency
  So that the community decides who sees its material, and anyone can read that decision from the file

  Carries out knowledge/spec_classification.md, "Register file".
  The kit has no tier names of its own and doesn't decide what the tiers should be. It
  only checks that the register the community wrote holds together. A sees-list is
  written out in full rather than inferred, so nobody has to work out who reads what.

  @AC-tier_register-1
  Scenario: A consistent register passes
    Given the Japanese demo register examples/demo/japanese/jp-tiers.yaml
    When a person runs python scripts/check_tier_register.py on it
    Then every tier in the file is listed with no problems
    And the command exits 0

  @AC-tier_register-2
  Scenario: Tiers closed to each other are reported
    Given a register in which jp-p and jp-q each see jp-open but not each other
    When a person runs python scripts/check_tier_register.py on it
    Then the output has a line "[CLOSED] jp-p / jp-q"
    And a pair where one tier sees the other, such as jp-open and jp-a, is not reported as closed

  @AC-tier_register-3
  Scenario: A register with a missing or malformed entry fails
    Given a register whose register field isn't 1, whose tier list is empty, or with a tier that has an invalid id, a repeated id, no name or no store.path
    When the register is checked
    Then each such problem is reported against the tier it belongs to
    And the command exits 1

  @AC-tier_register-4
  Scenario: Every store must say whether it may have a remote
    Given a tier whose store.remote is missing, or is a value other than allowed or none
    When the register is checked
    Then the problem is reported
    And meanwhile the tier is treated as remote: none, the stricter rule

  @AC-tier_register-5
  Scenario: A sees-list may only name other tiers that exist
    Given a tier whose sees-list names a tier that isn't in the register, or names the tier itself
    When the register is checked
    Then the unknown tier, or the tier listing itself, is reported

  @AC-tier_register-6
  Scenario: A sees-list must be written in full
    Given tier b sees a, and tier a sees o, but b's sees-list leaves out o
    When the register is checked
    Then the check reports that b's sees-list must also list o
    And it doesn't add o for the reader

  @AC-tier_register-7
  Scenario: Tiers can't see each other in a circle
    Given tier a sees b and tier b sees a
    When the register is checked
    Then a cycle is reported

  @AC-tier_register-8
  Scenario: Each tier has its own store, not shared and not inside another
    Given two tiers whose store.path is the same folder, or one tier whose store lies inside another tier's store
    When the register is checked
    Then the shared store, or the store lying inside the other, is reported

  @AC-tier_register-9
  Scenario: Checking stores finds a remote a tier doesn't allow and reports absent stores
    Given a register whose store paths are read relative to the register file
    And a store whose tier has remote: none but whose git checkout has a remote
    And a tier whose store isn't on this machine
    When a person runs the check with --stores
    Then the store with the remote is reported as a problem
    And the missing store is reported as absent, not passed

  @AC-tier_register-10
  Scenario: A store must be the top of its own git checkout
    Given a tier whose store is a folder inside some other git repository
    When a person runs the check with --stores
    Then the store is reported as not the top of its own git checkout

  @AC-tier_register-11
  Scenario: Stores aren't checked while the register has problems
    Given a register with a problem, such as a tier that lists itself
    When a person runs the check with --stores
    Then the output says the stores were not checked
    And the command exits 1

  @AC-tier_register-12
  Scenario: A machine without git is reported, not passed
    Given a consistent register
    And a machine with no git installed
    When a person runs the check with --stores
    Then the check reports that no store could be checked because git is not installed

  @AC-tier_register-13
  Scenario: A tier's term registers are found relative to the register file
    Given a tier that lists a term register under terms
    When the register is read
    Then the term register's path is taken relative to the register file
    And the register has no problems

  @AC-tier_register-14
  Scenario: A tier may say who may classify into it
    Given a tier in the Japanese demo register with a classifiers list
    When the register is read
    Then the tier's classifiers are the ones the file lists
    And a tier without a classifiers list has none, and that is not a problem
