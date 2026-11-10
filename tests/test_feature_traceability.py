"""Tests for scripts/check_feature_traceability.py, on small trees under tmp_path.

The fixture features and tests written into tmp_path use the abstract keys fx_a and fx_b.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import check_feature_traceability as ft  # noqa: E402

SCRIPT = ROOT / "scripts" / "check_feature_traceability.py"

FX_A = """\
Feature: Fixture a
  As a tester
  I want a fixture
  So that the check has something to read

  @AC-fx_a-1
  Scenario: The first behaviour
    Given fixture data
    Then fixture output
"""

TEST_A = '''\
def test_one():
    """@AC-fx_a-1. Exercises the first behaviour."""
'''


def tree(tmp_path: Path, features: dict[str, str], tests: dict[str, str]) -> Path:
    (tmp_path / "features").mkdir()
    (tmp_path / "tests").mkdir()
    for name, text in features.items():
        (tmp_path / "features" / name).write_text(text, encoding="utf-8")
    for name, text in tests.items():
        (tmp_path / "tests" / name).write_text(text, encoding="utf-8")
    return tmp_path


def run(root: Path, capsys) -> tuple[int, str]:
    code = ft.main(["--root", str(root)])
    return code, capsys.readouterr().out


def test_clean_tree_passes(tmp_path, capsys):
    """@AC-feature_traceability-1. A fully linked tree passes."""
    root = tree(tmp_path, {"fx_a.feature": FX_A}, {"test_fx.py": TEST_A})
    code, out = run(root, capsys)
    assert code == 0
    assert out.strip() == "0 problem(s): 1 scenario(s), 1 test(s)"


def test_default_root_is_the_repository(monkeypatch, tmp_path, capsys):
    """@AC-feature_traceability-1. With no --root, the module's ROOT is read."""
    root = tree(tmp_path, {"fx_a.feature": FX_A}, {"test_fx.py": TEST_A})
    monkeypatch.setattr(ft, "ROOT", root)
    # argparse binds the default when the parser is built, so main() sees the patched ROOT.
    assert ft.main([]) == 0
    assert "0 problem(s)" in capsys.readouterr().out


def test_file_name_not_a_key(tmp_path, capsys):
    """@AC-feature_traceability-2. A feature file name that isn't a key is reported."""
    root = tree(tmp_path, {"Fx-a.feature": FX_A}, {"test_fx.py": TEST_A})
    code, out = run(root, capsys)
    assert code == 1
    assert "[ERROR] features/Fx-a.feature: file name isn't a key ([a-z0-9_]+)" in out
    assert "0 scenario(s)" in out


def test_no_feature_line(tmp_path, capsys):
    """@AC-feature_traceability-3. A feature file with no Feature: line is reported."""
    text = FX_A.replace("Feature: Fixture a", "Fixture a")
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": TEST_A})
    code, out = run(root, capsys)
    assert code == 1
    assert "[ERROR] features/fx_a.feature: has no Feature: line" in out
    assert "1 scenario(s)" in out


def test_scenario_with_no_tag(tmp_path, capsys):
    """@AC-feature_traceability-4. An untagged scenario is reported by file and line."""
    text = FX_A + "\n  Scenario: An untagged behaviour\n    Given fixture data\n"
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": TEST_A})
    code, out = run(root, capsys)
    assert code == 1
    assert "[ERROR] features/fx_a.feature:11: scenario has 0 @AC- tags, not one" in out


def test_scenario_with_two_tags(tmp_path, capsys):
    """@AC-feature_traceability-5. Two tags, on one line or two, are reported."""
    text = FX_A + (
        "\n  @AC-fx_a-2 @AC-fx_a-3\n  Scenario: Two on a line\n"
        "\n  @AC-fx_a-4\n  @wip @AC-fx_a-5\n  Scenario: Two on two lines\n"
    )
    tests = TEST_A + '\n\ndef test_two():\n    """@AC-fx_a-2 @AC-fx_a-3 @AC-fx_a-4 @AC-fx_a-5."""\n'
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": tests})
    code, out = run(root, capsys)
    assert code == 1
    assert "features/fx_a.feature:12: scenario has 2 @AC- tags, not one" in out
    assert "features/fx_a.feature:16: scenario has 2 @AC- tags, not one" in out
    assert out.count("[ERROR]") == 2


def test_tag_with_another_files_key(tmp_path, capsys):
    """@AC-feature_traceability-6. A tag must use its own file's key."""
    fx_b = "Feature: Fixture b\n\n  @AC-fx_a-1\n  Scenario: Borrowed key\n"
    root = tree(tmp_path, {"fx_a.feature": FX_A, "fx_b.feature": fx_b}, {"test_fx.py": TEST_A})
    code, out = run(root, capsys)
    assert code == 1
    assert "features/fx_b.feature:4: @AC-fx_a-1 doesn't use this file's key 'fx_b'" in out


def test_tag_used_twice(tmp_path, capsys):
    """@AC-feature_traceability-7. A tag on two scenarios is reported at the second."""
    text = FX_A + "\n  @AC-fx_a-1\n  Scenario: Same tag again\n"
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": TEST_A})
    code, out = run(root, capsys)
    assert code == 1
    assert ("features/fx_a.feature:12: @AC-fx_a-1 is already used at "
            "features/fx_a.feature:7") in out


def test_scenario_no_test_names(tmp_path, capsys):
    """@AC-feature_traceability-8. A scenario no test names is reported."""
    text = FX_A + "\n  @AC-fx_a-2\n  Scenario: Untested behaviour\n"
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": TEST_A})
    code, out = run(root, capsys)
    assert code == 1
    assert "[ERROR] features/fx_a.feature:12: no test names @AC-fx_a-2" in out
    assert "1 problem(s): 2 scenario(s), 1 test(s)" in out


def test_test_names_no_tag(tmp_path, capsys):
    """@AC-feature_traceability-9. Tests with no docstring or no tag in it are reported."""
    tests = TEST_A + '\n\ndef test_bare():\n    pass\n\n\ndef test_plain():\n    """No tag."""\n'
    root = tree(tmp_path, {"fx_a.feature": FX_A}, {"test_fx.py": tests})
    code, out = run(root, capsys)
    assert code == 1
    assert "[ERROR] tests/test_fx.py::test_bare: names no @AC- tag in its docstring" in out
    assert "[ERROR] tests/test_fx.py::test_plain: names no @AC- tag in its docstring" in out


def test_test_names_unknown_tag(tmp_path, capsys):
    """@AC-feature_traceability-10. A tag no scenario has is reported against the test."""
    tests = TEST_A + '\n\ndef test_ghost():\n    """@AC-fx_a-1 and @AC-fx_b-7."""\n'
    root = tree(tmp_path, {"fx_a.feature": FX_A}, {"test_fx.py": tests})
    code, out = run(root, capsys)
    assert code == 1
    assert "[ERROR] tests/test_fx.py::test_ghost: names @AC-fx_b-7, which no scenario has" in out
    assert out.count("[ERROR]") == 1


def test_comments_and_blank_lines_keep_the_tag(tmp_path, capsys):
    """@AC-feature_traceability-11. Comments and blanks keep a tag; other text drops it."""
    text = FX_A + (
        "\n  @AC-fx_a-2\n  # a comment\n\n  Scenario: Tag kept\n"
        "\n  @AC-fx_a-3\n  Some other text\n  Scenario: Tag dropped\n"
    )
    tests = TEST_A + '\n\ndef test_two():\n    """@AC-fx_a-2."""\n'
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": tests})
    code, out = run(root, capsys)
    assert code == 1
    assert "features/fx_a.feature:18: scenario has 0 @AC- tags, not one" in out
    assert "features/fx_a.feature:16: @AC-fx_a-3 isn't on a scenario" in out
    assert "@AC-fx_a-2" not in out
    assert out.count("[ERROR]") == 2


def test_outlines_templates_and_examples(tmp_path, capsys):
    """@AC-feature_traceability-12. Outline, Template and Example are scenarios."""
    text = FX_A + (
        "\n  @AC-fx_a-2\n  Scenario Outline: An outline\n    Given <x>\n\n    Examples:\n"
        "      | x |\n      | 1 |\n"
        "\n  @AC-fx_a-3\n  Scenario Template: A template\n"
        "\n  @AC-fx_a-4\n  Example: An example\n"
    )
    tests = TEST_A + '\n\ndef test_more():\n    """@AC-fx_a-2, @AC-fx_a-3, @AC-fx_a-4."""\n'
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": tests})
    code, out = run(root, capsys)
    assert code == 0, out
    assert "4 scenario(s), 2 test(s)" in out


def test_only_docstrings_name_tags(tmp_path, capsys):
    """@AC-feature_traceability-13. Tags in a test's body don't count."""
    text = FX_A + "\n  @AC-fx_a-2\n  Scenario: Named only in a body\n"
    tests = TEST_A + (
        '\n\ndef test_body():\n    """No tag here."""\n'
        '    # @AC-fx_a-2\n    x = "@AC-fx_a-2"\n'
    )
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": tests})
    code, out = run(root, capsys)
    assert code == 1
    assert "tests/test_fx.py::test_body: names no @AC- tag in its docstring" in out
    assert "features/fx_a.feature:12: no test names @AC-fx_a-2" in out


def test_methods_and_async_tests_are_read(tmp_path, capsys):
    """@AC-feature_traceability-14. Class methods and async tests are read, nested helpers aren't."""
    text = FX_A + "\n  @AC-fx_a-2\n  Scenario: Second\n\n  @AC-fx_a-3\n  Scenario: Third\n"
    tests = TEST_A + (
        '\n\nclass TestFx:\n    def test_method(self):\n        """@AC-fx_a-2."""\n'
        '\n\nasync def test_async():\n    """@AC-fx_a-3."""\n'
        '\n\ndef helper():\n    pass\n'
        '\n\ndef test_outer():\n    """@AC-fx_a-1."""\n    def test_inner():\n        pass\n'
    )
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": tests})
    code, out = run(root, capsys)
    assert code == 0, out
    assert "3 scenario(s), 4 test(s)" in out


def test_command_line_on_a_chosen_root(tmp_path, monkeypatch, capsys):
    """@AC-feature_traceability-15. Run as a script with --root, it exits 1 on a problem."""
    root = tree(tmp_path, {"fx_a.feature": FX_A}, {"test_fx.py": "def test_x():\n    pass\n"})
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--root", str(root)])
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 1
    else:
        raise AssertionError("the script did not exit")
    assert "names no @AC- tag" in capsys.readouterr().out


def test_a_test_file_that_isnt_python_is_reported(tmp_path, capsys):
    """@AC-feature_traceability-16. A syntax error is reported, and other files are still read."""
    root = tree(tmp_path, {"fx_a.feature": FX_A},
                {"test_fx.py": TEST_A, "test_broken.py": "def test_x(:\n    pass\n"})
    code, out = run(root, capsys)
    assert code == 1
    assert "tests/test_broken.py:1: can't be read as Python" in out
    assert out.count("[ERROR]") == 1
    assert "1 scenario(s), 1 test(s)" in out


def test_text_that_only_starts_like_a_tag_isnt_one(tmp_path, capsys):
    """@AC-feature_traceability-17. A tag must end where its number ends."""
    text = FX_A + "\n  @AC-fx_a-2-extra\n  Scenario: Second\n"
    tests = TEST_A + '\n\ndef test_two():\n    """Names AC-fx_a-2-extra with an at sign: @AC-fx_a-2-extra."""\n'
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": tests})
    code, out = run(root, capsys)
    assert code == 1
    assert "features/fx_a.feature:11: '@AC-fx_a-2-extra' isn't an @AC-<key>-<n> tag" in out
    assert "features/fx_a.feature:12: scenario has 0 @AC- tags, not one" in out
    assert "tests/test_fx.py::test_two: names no @AC- tag" in out


@pytest.mark.parametrize("keyword", ["Rule: A rule", "Background:", "Examples:", "Feature: Again"])
def test_a_tag_not_on_a_scenario_is_reported(tmp_path, capsys, keyword):
    """@AC-feature_traceability-18. A tag above a line that isn't a scenario is reported."""
    text = FX_A + f"\n  @AC-fx_a-2\n  {keyword}\n"
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": TEST_A})
    code, out = run(root, capsys)
    assert code == 1
    assert "features/fx_a.feature:11: @AC-fx_a-2 isn't on a scenario" in out
    assert out.count("[ERROR]") == 1


def test_a_tag_at_the_end_of_the_file_is_reported(tmp_path, capsys):
    """@AC-feature_traceability-18. A tag with nothing after it isn't on a scenario."""
    root = tree(tmp_path, {"fx_a.feature": FX_A + "\n  @AC-fx_a-2\n"}, {"test_fx.py": TEST_A})
    code, out = run(root, capsys)
    assert code == 1
    assert "features/fx_a.feature:11: @AC-fx_a-2 isn't on a scenario" in out


def test_a_repeated_tag_on_one_scenario_is_reported_once(tmp_path, capsys):
    """@AC-feature_traceability-19. A repeated tag counts as two tags, reported once."""
    text = FX_A.replace("  @AC-fx_a-1\n", "  @AC-fx_a-1 @AC-fx_a-1\n")
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": TEST_A})
    code, out = run(root, capsys)
    assert code == 1
    assert "features/fx_a.feature:7: scenario has 2 @AC- tags, not one" in out
    assert out.count("[ERROR]") == 1


@pytest.mark.parametrize("fence", ['"""', "```"])
def test_a_steps_doc_string_isnt_read(tmp_path, capsys, fence):
    """@AC-feature_traceability-20. Lines in a step's doc string are neither tags nor scenarios."""
    text = FX_A + f"    And a doc string\n      {fence}\n      @AC-fx_a-9\n      Scenario: Not one\n      {fence}\n"
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": TEST_A})
    code, out = run(root, capsys)
    assert code == 0, out
    assert "1 scenario(s), 1 test(s)" in out


def test_tests_are_found_the_way_pytest_finds_them(tmp_path, capsys):
    """@AC-feature_traceability-21. Tests in module-level blocks and Test classes count; helper classes don't."""
    text = FX_A + "\n  @AC-fx_a-2\n  Scenario: Second\n\n  @AC-fx_a-3\n  Scenario: Third\n"
    tests = TEST_A + (
        '\n\nimport sys\n\nif sys.platform:\n    def test_in_if():\n        """@AC-fx_a-2."""\n'
        'else:\n    pass\n'
        '\n\ntry:\n    import fx_absent\nexcept ImportError:\n'
        '    def test_in_except():\n        """No tag."""\n'
        '\n\nclass TestFx:\n    def test_method(self):\n        """@AC-fx_a-3."""\n'
        '\n\nclass Helper:\n    def test_not_collected(self):\n        pass\n'
    )
    root = tree(tmp_path, {"fx_a.feature": text}, {"test_fx.py": tests})
    code, out = run(root, capsys)
    assert code == 1
    assert "tests/test_fx.py::test_in_except: names no @AC- tag" in out
    assert "test_not_collected" not in out
    assert out.count("[ERROR]") == 1
    assert "3 scenario(s), 4 test(s)" in out
