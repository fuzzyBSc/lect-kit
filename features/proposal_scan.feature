Feature: Proposal scan
  As someone committing to a store that higher tiers can see
  I want every higher tier on this machine to screen what the store would hold after the commit
  So that nothing a higher tier keeps to itself reaches a lower store, and each tier's material stays where the community put it

  Carries out knowledge/spec_classification.md, "Proposal scan".
  The proposal is the whole staged tree, exported blob by blob from git's object store,
  so a leak already committed is caught with the new one and nothing about the working
  copy changes what is scanned. Each higher tier screens it in its own process and only a
  fixed-shape verdict crosses back, naming file and line in the proposed tree and nothing
  else. A pattern scan can't clear anything, so a verdict is either hold or no match.

  @AC-proposal_scan-1
  Scenario: A clean proposal is screened by every higher tier and leaves evidence
    Given a register where fx-a and fx-p both see fx-open, and all three stores are on the machine
    And the staged tree of fx-open holds nothing from fx-a or fx-p
    When a person runs python scripts/scan_proposal.py for fx-open in its checkout
    Then fx-a and fx-p each return no match
    And an evidence record for the staged tree is written inside fx-open's .git folder, never in the working tree
    And the command prints [EVIDENCE] and exits 0

  @AC-proposal_scan-2
  Scenario: A staged leak is held by the tier it belongs to, by file and line only
    Given the staged tree of fx-open has a file fx-notes.md whose line 2 holds a gloss from fx-a
    When the proposal scan runs for fx-open
    Then fx-a holds the proposal at fx-notes.md line 2 and fx-p returns no match
    And the output names the file and line, as "fx-notes.md:2: not allowed in fx-open", without repeating the gloss
    And no evidence is written and the command exits 1

  @AC-proposal_scan-3
  Scenario: The whole staged tree is screened, not only the change
    Given fx-open already has a staged file holding a gloss from fx-p
    And the change being made now is an unrelated file
    When the proposal scan runs for fx-open
    Then fx-p holds the proposal

  @AC-proposal_scan-4
  Scenario: What is staged is screened, not the working copy
    Given a file holding a gloss from fx-a is staged in fx-open and then cleaned in the working copy only, or marked skip-worktree and deleted from the working copy
    When the proposal scan runs for fx-open
    Then the proposal is held
    And once the clean version is staged, and the leak sits only in a file that isn't staged, the proposal is not held

  @AC-proposal_scan-5
  Scenario: Filters and line-ending settings don't change what is scanned
    Given fx-open has a .gitattributes filter that would rewrite .md files on checkout and core.autocrlf set to true
    And a staged fx-notes.md holds a gloss from fx-a on line 1
    When the proposal scan runs for fx-open
    Then fx-a holds the proposal at fx-notes.md line 1

  @AC-proposal_scan-6
  Scenario: File and folder names are screened too
    Given fx-open has a folder staged whose name is a gloss from fx-a
    When someone commits to fx-open
    Then the commit is refused at a line of .lectkit-paths, the list of every path in the proposed tree

  @AC-proposal_scan-7
  Scenario: A symbolic link or a submodule in the tree stops the scan
    Given the staged tree of fx-open holds a symbolic link, or a submodule
    When the proposal scan runs for fx-open
    Then the scan stops with an error saying it can't be screened

  @AC-proposal_scan-8
  Scenario: An absent higher store is a gap, never a pass
    Given fx-p's store isn't on the machine, or no higher store is there at all
    When a person runs python scripts/scan_proposal.py for fx-open
    Then fx-p is reported as [GAP] by name and only the tiers present are screened
    And no evidence is written and the command exits 2

  @AC-proposal_scan-9
  Scenario: An empty folder at a higher store's path is a gap
    Given an empty folder sits at the path the register gives for fx-p, not a checkout of its own
    When a person runs python scripts/scan_proposal.py for fx-open
    Then fx-p is a gap, the command exits 2 and fx-open's .git folder holds no evidence

  @AC-proposal_scan-10
  Scenario: Only a verdict in the fixed shape crosses back
    Given a screen answers with an extra field, free text, the wrong tier or tree, an outcome of clear, a hold with no locations, locations on a no match, or a location that carries text, isn't a path in the proposed tree or has a line below 1
    When the runner reads the answer
    Then the answer is refused
    And a verdict in the fixed shape is accepted unchanged

  @AC-proposal_scan-11
  Scenario: Evidence names the tree and the state of the higher stores
    Given a clean proposal for fx-open
    When its evidence is written
    Then the record names the tree git write-tree gives, a digest of the register, and a digest of each of fx-a and fx-p
    And after fx-a adds a file, screening again gives a different digest for fx-a

  @AC-proposal_scan-12
  Scenario: The scan runs only in the store the register names
    Given a git checkout that isn't the path the register gives for fx-open
    When a person runs python scripts/scan_proposal.py for fx-open there
    Then it reports that this checkout isn't the store the register gives for fx-open
    And the command exits 3

  @AC-proposal_scan-13
  Scenario: A screen that fails never passes
    Given fx-a's store holds a file that can't be read
    When the proposal scan runs for fx-open
    Then the scan stops, saying fx-a's screen couldn't run

  @AC-proposal_scan-14
  Scenario: Each higher tier's screen prints a verdict and nothing else
    Given fx-open's staged tree exported to a folder, with a gloss from fx-a in fx-notes.md line 1
    When python scripts/screen_for_tier.py screens it for fx-a
    Then it prints one verdict holding fx-notes.md line 1 and exits 0
    And asked to screen for a tier that doesn't see fx-open, or when fx-a's store can't be read, it prints nothing and exits 3

  @AC-proposal_scan-15
  Scenario: A hold says what kind of match held each line
    Given a staged line in fx-open matches fx-a material
    When fx-open's proposal is screened
    Then fx-a's verdict counts the held lines by kind of match: value, token, passage or term
    And the hook prints those counts beside the held lines, so the screen's own noise is visible
    But a verdict whose causes name anything else is refused, since it could carry text

  @AC-proposal_scan-16
  Scenario: Writing a higher tier's entry into the same file doesn't make it the lower tier's
    Given fx-a's layer of lexicon/fx-nouns.yaml adds an entry fx-open lacks
    When fx-open stages the same entry in its own copy of that file
    Then fx-a holds the copied lines, as it would in any other file
    And an identifier fx-a's layer writes to attach to an fx-open record is fx-a's material, held in fx-open until fx-a releases it

  @AC-proposal_scan-17
  Scenario: A screening tier keeps the material it screens with, and never uses a stale copy
    Given fx-a has screened fx-open once, so fx-a's git folder holds fx-a's material
    When fx-a's store changes, adding a gloss fx-open's staged tree already holds
    Then the next screen holds that line, because the kept material no longer matches fx-a's files
    And the kept material is only ever in fx-a's own git folder, never in a working tree or a lower store
    And a damaged copy is worked out again rather than trusted
