import pytest

import joy


def test_help_presents_joy_as_a_harness_overlay(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["joy", "--help"])
    with pytest.raises(SystemExit) as exit_:
        joy.main()
    assert exit_.value.code == 0
    assert capsys.readouterr().out.splitlines()[0] == "joy - a harness overlay for AI-assisted coding tools"
