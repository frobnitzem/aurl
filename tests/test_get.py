from pathlib import Path
import json

import pytest
from typer.testing import CliRunner

from aurl.get import app as get

runner = CliRunner()

def test_get_file(tmp_path):
    def to_url(name : Path) -> str:
         return "file://%s/%s"%(str(tmp_path).replace("\\", "/"),
                         str(name).replace("\\", "/"))

    result = runner.invoke(get, ["--mirror", str(tmp_path/"mirror"),
                                    to_url("dir1"), to_url("x")]
                          )
    assert result.exit_code != 0

    (tmp_path/"mirror").mkdir()
    (tmp_path/"dir1").mkdir()
    (tmp_path/"x").write_text("some text")
    assert(to_url("x").startswith("file:///"))
    result = runner.invoke(get, ["--mirror", str(tmp_path/"mirror"),
                                    to_url("dir1"), to_url("x")])
    assert result.exit_code == 0
    ret = json.loads(result.stdout)
    assert len(ret) == 2
