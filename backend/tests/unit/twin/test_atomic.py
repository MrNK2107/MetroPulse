import pytest

from twin.store.atomic import publish_dir


def test_fresh_install(tmp_path):
    final = tmp_path / "a" / "v1"
    publish_dir(final, lambda t: (t / "f.txt").write_text("new"))
    assert (final / "f.txt").read_text() == "new"
    assert [p.name for p in final.parent.iterdir()] == ["v1"]


def test_replace_existing_keeps_only_new(tmp_path):
    final = tmp_path / "v1"
    final.mkdir()
    (final / "old.txt").write_text("old")
    publish_dir(final, lambda t: (t / "new.txt").write_text("new"))
    assert [p.name for p in final.iterdir()] == ["new.txt"]
    assert [p.name for p in tmp_path.iterdir()] == ["v1"]


def test_writer_failure_leaves_previous_intact(tmp_path):
    final = tmp_path / "v1"
    final.mkdir()
    (final / "old.txt").write_text("old")

    def bad(t):
        (t / "partial.txt").write_text("x")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        publish_dir(final, bad)
    assert (final / "old.txt").read_text() == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["v1"]


def test_install_failure_restores_previous(tmp_path, monkeypatch):
    import twin.store.atomic as atomic

    final = tmp_path / "v1"
    final.mkdir()
    (final / "old.txt").write_text("old")
    real = atomic.os.replace
    calls = []

    def flaky(src, dst):
        calls.append(1)
        if len(calls) == 2:  # the tmp -> final install
            raise OSError("nope")
        return real(src, dst)

    monkeypatch.setattr(atomic.os, "replace", flaky)
    with pytest.raises(OSError):
        publish_dir(final, lambda t: (t / "n.txt").write_text("n"))
    assert (final / "old.txt").read_text() == "old"
    assert [p.name for p in tmp_path.iterdir()] == ["v1"]
