Feature: Decisions on cross-tier scan findings
  As a person of the tier whose material a scan finding matched
  I want to record once that a match is shared rather than leaked, or that an exact lower entry is fine
  So that each tier decides for its own material, and a decision lapses as soon as what it covered changes

  Carries out knowledge/spec_classification.md, "Cross-tier scan": accepted matches,
  reviewed findings, and keyed ids and review digests.

  Decisions live in the store of the tier whose material matched, so every scanner above
  that tier honours them and no tier decides for another. A review is tied to the exact
  lower text and the hidden items it matched, so any change brings the finding back.

  @AC-scan_review-1
  Scenario: An accepted match is kept with the material it is about
    Given a note in fx-open names fx-a's sense id stemA-s2
    And fx-a's .lectkit/accepted_matches.yaml accepts that text for fx-open
    When fx-c runs the scan
    Then the fx-open line is not an open finding
    But an acceptance of the same text in fx-c's own file doesn't clear fx-a's material

  @AC-scan_review-2
  Scenario: Each tier holding a matched text decides for itself
    Given fx-c and fx-a both accept the field name "gloss" for fx-open in their own stores
    And neither accepts "senses"
    When fx-c runs the scan
    Then fx-open's gloss line is cleared
    And its senses line is still a finding

  @AC-scan_review-3
  Scenario: An acceptance covers only its text, its tier, and the tiers that see it
    Given a line in fx-open matches two separate fx-c items
    When fx-c accepts only one of them for fx-open
    Then the line is still a finding, and it clears once both are accepted
    And an acceptance for fx-open also clears the same text in fx-a's store, since fx-a sees fx-open
    But an acceptance for fx-a doesn't clear the same text in fx-open's store

  @AC-scan_review-4
  Scenario: A reviewed entry stays cleared while it doesn't change
    Given a finding on a note in fx-open
    When a person runs review_finding.py with the finding's id, a reason and --by human:<name>
    Then review_finding.py exits with code 0
    And the next scan shows the finding as reviewed, exits with code 0, and counts "1 reviewed"

  @AC-scan_review-5
  Scenario: A review follows its entry to another line
    Given a reviewed finding on line 1 of a note in fx-open
    When a new first line is added above it
    Then the finding, now on line 2, is still reviewed

  @AC-scan_review-6
  Scenario: Changing the lower text brings the finding back
    Given a reviewed finding on a note in fx-open
    When the words of that line change
    Then the line is an open finding again

  @AC-scan_review-7
  Scenario: A passage review covers every line the passage spans
    Given a reviewed passage finding that starts on line 1 and runs onto line 2
    When only line 2 changes
    Then the finding is open again

  @AC-scan_review-8
  Scenario: A new hidden match on a reviewed entry brings it back
    Given a reviewed finding on a note in fx-open
    When fx-c adds material that the whole line now also matches
    Then the line is an open finding again

  @AC-scan_review-9
  Scenario: A matched item moving to another tier brings the finding back
    Given a reviewed finding on fx-open that matched an item of fx-a
    When that item leaves fx-a and appears in fx-c instead
    Then the line is an open finding again

  @AC-scan_review-10
  Scenario: Copying a reviewed line makes a new finding
    Given a reviewed finding on line 1 of a note in fx-open
    When the same line is written again as line 2
    Then line 1 stays reviewed and line 2 is an open finding

  @AC-scan_review-11
  Scenario: The same text in another file isn't covered
    Given a reviewed finding on a note in fx-open
    When another fx-open file has the same line
    Then only the line in the other file is an open finding

  @AC-scan_review-12
  Scenario: A review needs a person and a reason
    Given a finding on a note in fx-open
    When the review is given --by agent:<name>, or a blank reason
    Then the review is refused
    And who reviewed it is the tier's commit, not the file: a reviewed_findings.yaml row holds only the line's hashes

  @AC-scan_review-13
  Scenario: A review is saved in the store of the tier whose material matched
    Given a finding in fx-open that matched only fx-a material
    When a person of fx-c records a review of it
    Then the review is written in fx-a's .lectkit/reviewed_findings.yaml, and nowhere else
    And the row doesn't repeat the matched text, the file's path or the finding's id: each is a hash
    And because a review is fx-a's material, fx-a's store has changed: fx-c's scan asks for a rebuild, and after it honours the review

  @AC-scan_review-14
  Scenario: Recording a review keeps the review file valid
    Given fx-c's .lectkit/reviewed_findings.yaml already exists as an empty mapping in flow style
    When two findings are reviewed
    Then the file holds both reviews and still reads cleanly

  @AC-scan_review-15
  Scenario: Finding ids are keyed with a secret kept in the scanning tier's store
    Given fx-c has run a scan
    Then fx-c's .lectkit/scan_key holds a 32-byte key as hex
    And a finding's id can't be reproduced from the line and a guessed word without that key
    And no scan_key appears in fx-open's store

  @AC-scan_review-16
  Scenario: Reviewing an id no current finding has is refused
    Given a scan that has findings
    When review_finding.py is given an id that no current finding has
    Then it exits with code 3
