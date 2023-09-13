from pathlib import Path
import json

import pytest
from typer.testing import CliRunner

from aurl.subst import app as subst

tpl = """
This is a test template

step1 = ${{ git://github.com/frobnitzem/aurl }}
root  = ${{ file:///usr/bin/last }}
github = ${{ git://github.com/frobnitzem/aiowire }}
"""

ans = """
This is a test template

step1 = {mirror}/git/github.com/frobnitzem/aurl
root  = /usr/bin/last
github = {mirror}/git/github.com/frobnitzem/aiowire
"""

runner = CliRunner()

def test_subst(tmp_path):
    result = runner.invoke(subst, ["--help"])
    assert result.exit_code == 0

    result = runner.invoke(subst, ["--mirror", str(tmp_path/"mirror"),
                                   str(tmp_path/"template.txt.tpl")])
    assert result.exit_code != 0

    (tmp_path/"mirror").mkdir()
    result = runner.invoke(subst, ["--mirror", str(tmp_path/"mirror"),
                                   str(tmp_path/"template.txt.tpl")])
    assert result.exit_code != 0

    (tmp_path/"template.txt.tpl").write_text(tpl)
    (tmp_path/"template.txt1.l").write_text(tpl)
    result = runner.invoke(subst, ["--mirror", str(tmp_path/"mirror"),
                                   str(tmp_path/"template.txt.tpl"),
                                   str(tmp_path/"template.txt1.l")])
    assert result.exit_code == 0

    out = (tmp_path / "template.txt").read_text()
    assert out == ans.format(mirror = str(tmp_path / "mirror"))
    out = (tmp_path / "template.txt1").read_text()
    assert out == ans.format(mirror = str(tmp_path / "mirror"))
