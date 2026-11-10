Feature: Commit and push hooks
  As someone committing to and pushing from a store's checkout
  I want git to refuse a commit or push that would carry a higher tier's material into this store or off the machine
  So that an honest mistake doesn't move material past the boundary the community drew for it

  Carries out knowledge/spec_classification.md, "Commit and push hooks".
  The hooks run locally, by someone who holds the higher stores they need. A commit rests
  on current evidence from the proposal scan. A push screens every commit it would
  publish afresh, with the commit object itself, because a commit can skip its hook. A
  hook is a local check: it keeps an honest mistake from leaving a machine, and
  --no-verify, another core.hooksPath or a clone without the hooks gets round it.

  @AC-commit_hooks-1
  Scenario: A clean commit passes and leaves current evidence
    Given fx-open's checkout has the hooks installed and fx-a, which sees fx-open, is on the machine
    And the staged tree holds nothing from fx-a
    When someone commits
    Then the commit is made and the evidence for its tree is current

  @AC-commit_hooks-2
  Scenario: A staged leak refuses the commit
    Given a staged fx-notes.md in fx-open holds a gloss from fx-a on line 1
    When someone commits
    Then the commit is refused with "fx-notes.md:1: not allowed in fx-open", without repeating the gloss
    And no commit is made

  @AC-commit_hooks-3
  Scenario: Evidence goes stale when a higher store or the register changes
    Given a commit to fx-open that left evidence
    When fx-a adds a file, or the register file changes
    Then the evidence is no longer current, saying "fx-a: store has changed since the scan" or "the register has changed since the scan"

  @AC-commit_hooks-4
  Scenario: Evidence must name exactly the higher tiers
    Given an evidence record for fx-open's tree that doesn't list fx-a
    When the hooks check it
    Then it isn't current, because it doesn't cover exactly the higher tiers

  @AC-commit_hooks-5
  Scenario: An absent higher store refuses the commit
    Given fx-a's store isn't on the machine
    When someone commits to fx-open
    Then the commit is refused and fx-a is reported as [GAP]

  @AC-commit_hooks-6
  Scenario: A tier no other tier sees commits at once
    Given fx-a, which no tier sees, has the hooks installed
    When someone commits to fx-a
    Then the commit is made without a proposal scan

  @AC-commit_hooks-7
  Scenario: A registered term in a file the tier excludes from its material refuses the commit
    Given fx-a names a term register, and its .lectkit/not_material.txt excludes README.md
    And README.md holds a term from that register on line 1
    When someone commits to fx-a
    Then the commit is refused with "README.md:1: a registered term", without repeating the term
    And the same term in a file under fx-a's material commits

  @AC-commit_hooks-8
  Scenario: The guard reads the exclusion list as staged
    Given fx-a's staged .lectkit/not_material.txt excludes docs/, but the working copy of that list excludes nothing
    And docs/fx-a-guide.md holds a registered term
    When someone commits to fx-a
    Then the commit is refused at docs/fx-a-guide.md line 1

  @AC-commit_hooks-9
  Scenario: A missing term register refuses the commit
    Given the register names a term register for fx-a that isn't there
    When someone commits to fx-a
    Then the commit is refused, naming the term register

  @AC-commit_hooks-10
  Scenario: A clean push passes
    Given fx-open has a clean commit and a remote
    When someone pushes
    Then the push goes ahead

  @AC-commit_hooks-11
  Scenario: Every commit being pushed is screened, not only the last
    Given an earlier commit made with --no-verify holds a gloss from fx-a, and a later commit removes it
    When someone pushes both
    Then the push is refused with "not allowed in fx-open"

  @AC-commit_hooks-12
  Scenario: Commits the remote already has aren't screened again
    Given the remote already has a commit holding a gloss from fx-a
    When someone pushes a clean commit on top of it
    Then the push goes ahead

  @AC-commit_hooks-13
  Scenario: What the remote has is asked of the remote, not of local tracking refs
    Given a commit holding a gloss from fx-a, and a local tracking ref that claims the remote has it
    When someone pushes
    Then the push is refused
    And when the remote can't be asked, every commit back to the root is screened, so a leak the remote already has refuses the push

  @AC-commit_hooks-14
  Scenario: Commit messages and author names are screened on push
    Given a clean tree committed with a message, or an author name, that holds a gloss from fx-a
    When someone pushes
    Then the push is refused at a line of .lectkit-commit-message, without repeating the gloss

  @AC-commit_hooks-15
  Scenario: An annotated tag's message is screened on push
    Given an annotated tag whose message holds a gloss from fx-a
    When someone pushes the tag
    Then the push is refused with "not allowed"

  @AC-commit_hooks-16
  Scenario: An update the hook can't read refuses the push
    Given git sends the push hook a line it can't read
    When the push hook runs
    Then it exits 1 and the push is refused

  @AC-commit_hooks-17
  Scenario: A store whose tier allows no remote never pushes
    Given fx-open's tier has remote: none in the register
    When someone pushes a clean commit
    Then the push is refused because its tier allows no remote

  @AC-commit_hooks-18
  Scenario: Installing writes both hooks for the registered store
    Given the register gives fx-open's store path
    When a person runs python scripts/install_hooks.py for fx-open in that checkout
    Then pre-commit and pre-push are written, each naming the register, the tier and the kit's hook script by absolute path
    And in a checkout that isn't the registered store, nothing is installed and the command exits 1

  @AC-commit_hooks-19
  Scenario: Installing leaves a hook it didn't write alone
    Given fx-open's checkout already has a pre-commit hook that lect-kit didn't write
    When a person runs python scripts/install_hooks.py
    Then it exits 1 and leaves the hook alone
    And with --force it replaces the hook and exits 0

  @AC-commit_hooks-20
  Scenario: A commit in a linked worktree is refused
    Given a linked worktree of fx-open's checkout
    When someone commits there
    Then the commit is refused, because that checkout isn't the store the register gives for fx-open

  @AC-commit_hooks-21
  Scenario: A commit's message and author lines are screened when the commit is made
    Given fx-open's staged tree screens clean
    When a commit is made whose message carries fx-a material
    Then the commit-msg hook refuses it and nothing is committed
    And the same change with a clean message commits
