Feature: Content checker
  As an agent about to commit to this public repository
  I want a checker that screens files against a project's own deny-lists and generic patterns
  So that no community's words, names or personal data reach lect-kit

  Carries out knowledge/content_procedure.md, "Checker behaviour (`scripts/check_content.py`)".
  The deny-lists belong to each project and are read only from paths given at run time.
  A hit reports file and line only, so the output never repeats a restricted term. A pass
  means the checker found nothing it was told to look for, not that the files are clear.

  @AC-content_checker-1
  Scenario: Only term, variant and pattern values in a structured deny-list count
    Given a YAML deny-list whose entries also carry captions, remarks, keys, flags and a group name
    When the deny-list is loaded
    Then text matching only a caption, remark, flag or key is not a hit

  @AC-content_checker-2
  Scenario: YAML values are read as the text written
    Given a YAML deny-list with variants "no" and "1234"
    When a line holding the word "no" or the number 1234 is screened
    Then each line is a hit, because the values stayed text rather than a boolean or a number

  @AC-content_checker-3
  Scenario: Variants match as whole words in any case
    Given a YAML deny-list with the variant "stemqa"
    When the lines "a line with StemQA in it" and "xstemqa" are screened
    Then the first line is a hit and the second is not

  @AC-content_checker-4
  Scenario: Pattern values are regular expressions
    Given a YAML deny-list with the pattern "sfxzz" followed by any word characters
    When the line "sfxzzing" is screened
    Then it is a hit

  @AC-content_checker-5
  Scenario: A variant or pattern that isn't a valid regular expression is matched literally
    Given a YAML deny-list with the variant or the pattern "brk(" which is not a valid regular expression
    When the line "has brk( here" is screened
    Then it is a hit, and the variant or pattern was not dropped

  @AC-content_checker-6
  Scenario: A plain text deny-list holds one term per line
    Given a text deny-list with a comment line, a blank line, "stemqa", "ab" and "ab:cd:ef"
    When the deny-list is loaded
    Then the terms are "stemqa" and "ab:cd:ef", and the two-letter entry is too short to count

  @AC-content_checker-7
  Scenario: A JSON deny-list is read like a YAML one
    Given a JSON deny-list with a term "stemqa", a note, and a pattern "sfxzz"
    When the deny-list is loaded
    Then the term is "stemqa", the note is ignored, and the pattern matches "sfxzz"

  @AC-content_checker-8
  Scenario: A term next to or holding punctuation is a hit reported by file and line only
    Given a deny-list with "stemqa" and "ab:cd:ef"
    And a file whose line holds one of them beside a full stop, hyphen, bracket or apostrophe
    When the checker runs on that file
    Then it exits 1 and reports the file and line as matching a supplied deny-list term
    And the output does not contain the term

  @AC-content_checker-9
  Scenario: A term inside a longer word is not a hit
    Given a deny-list with "stemqa"
    And a file whose only line is "xstemqa stemqax"
    When the checker runs on that file
    Then it exits 0

  @AC-content_checker-10
  Scenario: Deny-lists and files are compared after Unicode normalisation
    Given a deny-list with a term written in composed form
    And a file holding the same term written in decomposed form
    When the checker runs on that file
    Then it exits 1

  @AC-content_checker-11
  Scenario: A UTF-16 file is decoded and screened
    Given a deny-list with "stemqa"
    And a UTF-16 file holding "stemqa"
    When the checker runs on that file
    Then it exits 1

  @AC-content_checker-12
  Scenario: A file that can't be decoded is an error, not a skip
    Given a file of bytes that are not valid text
    When the checker runs on that file
    Then it exits 1 and says the file cannot be decoded

  @AC-content_checker-13
  Scenario: A directory is expanded into the files under it
    Given a deny-list with "stemqa"
    And a directory with a subdirectory holding a file with "stemqa"
    When the checker runs on the directory
    Then it exits 1

  @AC-content_checker-14
  Scenario: A path that doesn't exist is an error
    Given a path that names no file or directory
    When the checker runs on that path
    Then it exits 1 and says the path does not exist

  @AC-content_checker-15
  Scenario: A YAML deny-list that can't be parsed stops the run
    Given a YAML deny-list that is not valid YAML
    When the checker loads it
    Then the run stops with an error naming the deny file, without printing its contents

  @AC-content_checker-16
  Scenario: Deny-lists can be given in the LECT_KIT_DENY environment variable
    Given the environment variable LECT_KIT_DENY names a deny-list with "stemqa"
    And a file holding "stemqa"
    When the checker runs on that file with no deny option
    Then it exits 1 and reports the line

  @AC-content_checker-17
  Scenario: With no deny-list the checker says only generic checks ran
    Given no deny-list on the command line or in the environment
    And a clean file
    When the checker runs on that file
    Then it exits 0 and prints a note that only generic checks ran

  @AC-content_checker-18
  Scenario: An honorific followed by a capitalised name is a hit
    Given a file with a line holding an honorific such as Elder followed by a capitalised name
    When the checker runs on that file with no deny-list
    Then it exits 1 and reports the line as an honorific and name

  @AC-content_checker-19
  Scenario: An archive-style tape identifier is a hit
    Given a file with a line holding the word tape followed by a three to five digit number
    When the checker runs on that file
    Then it exits 1 and reports the line as an archive-style identifier

  @AC-content_checker-20
  Scenario: A personal home-directory path is a hit
    Given a file with a line holding a Windows, Linux or macOS user's home-directory path
    When the checker runs on that file
    Then it exits 1 and reports the line as a personal path

  @AC-content_checker-21
  Scenario: An email address is a hit
    Given a file with a line holding an email address
    When the checker runs on that file
    Then it exits 1 and reports the line as an email address

  @AC-content_checker-22
  Scenario: The commit attribution address is allowed
    Given a file with a line holding the no-reply address used in commit attribution
    When the checker runs on that file
    Then it exits 0

  @AC-content_checker-23
  Scenario: Images and compiled files are not screened
    Given a deny-list with "stemqa"
    And an image file and a compiled Python file that both hold "stemqa"
    When the checker runs on them
    Then it exits 0 and reports no file checked

  @AC-content_checker-24
  Scenario: The checker doesn't screen its own source
    Given the checker's own script
    When the checker runs on it
    Then it exits 0 and reports no file checked

  @AC-content_checker-25
  Scenario: With no path the checker screens every file git tracks or would add
    Given a git working tree with a file holding "stemqa" and an ignored file holding "stemqa"
    When the checker runs there with a deny-list and no path
    Then it reports the file git would add and not the ignored one

  @AC-content_checker-26
  Scenario: The shared deny-list helpers give the line numbers that match
    Given deny-lists with a term and a pattern
    When lines are searched with the matchers built from them
    Then the numbers, counted from 1, of the lines that match are returned, after Unicode normalisation

  @AC-content_checker-27
  Scenario: A deny-list given as a folder reads the structured lists in it
    Given a folder holding YAML and JSON lists, one of them in a subfolder
    And a README.txt, a README.md and a list inside a hidden folder
    When the checker runs with that folder as a deny-list
    Then the terms in every .yaml, .yml and .json file under it are screened for
    And the text files and anything in the hidden folder aren't read as lists
    # A plain text list is named on its own, so notes kept beside the lists can't become terms.

  @AC-content_checker-28
  Scenario: A deny-list that can't be read stops the run
    Given a deny-list path that doesn't exist, a deny-list that isn't UTF-8 text, or a folder with no lists in it
    When the checker runs with it
    Then it stops with an error naming the deny-list by file name only, never its content or full path
    And it screens nothing, so no pass is reported

  @AC-content_checker-29
  Scenario: The hooks and the scan read deny-lists the same way as the checker
    Given a term register given as a folder of lists, and one that isn't UTF-8 text
    When the shared deny-list reader builds its matchers
    Then the folder's lists are read, and the undecodable one stops the run with an error naming it

  @AC-content_checker-30
  Scenario: An entry marked case_sensitive matches only in the case written
    Given a YAML deny-list entry with the variant "StemQc", the term "TermQd", the pattern "SfxQe" and case_sensitive true
    And another entry with the variant "stemqf" and no case_sensitive option
    When the lines "StemQc", "stemqc", "TermQd", "termqd", "SfxQe", "sfxqe" and "STEMQF" are screened
    Then "StemQc", "TermQd", "SfxQe" and "STEMQF" are hits and the others are not
    # The term registers these lists come from match case-insensitively unless an entry says otherwise.

  @AC-content_checker-31
  Scenario: An entry's suffix_guard is appended after each of its variants
    Given a YAML deny-list entry with the variant "stemqg" and the suffix_guard "(?!-[a-z])"
    When the lines "a stemqg here" and "a stemqg-ly look-alike" are screened
    Then the first line is a hit and the second is not
    And a suffix_guard that isn't a valid regular expression stops the run with an error naming the file only
    # The guard rules out a look-alike word. It isn't applied to a pattern, which is used as written.
