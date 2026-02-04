from pathlib import Path

import pytest

from pcb_renderer.cli import open_file


def test_open_file_linux_no_opener(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("shutil.which", lambda *_args, **_kwargs: None)
    with pytest.raises(RuntimeError):
        open_file(Path("/tmp/out.svg"))


def test_open_file_linux_with_xdg(monkeypatch):
    monkeypatch.setattr("sys.platform", "linux")
    calls = []
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/xdg-open" if name == "xdg-open" else None)
    monkeypatch.setattr("subprocess.run", lambda args, check=False: calls.append(args))
    open_file(Path("/tmp/out.svg"))
    assert calls and calls[0][0] == "/usr/bin/xdg-open"
