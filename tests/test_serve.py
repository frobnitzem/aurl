from pathlib import Path

from aurl.serve import safe_path, HTTPException

def test_safe_path(tmp_path: Path):
    base = tmp_path / "test_base"

    # Create a base directory and some files/directories for testing
    base.mkdir(exist_ok=True)
    (base / "file1.txt").touch()
    (base / "subdir").mkdir(exist_ok=True)
    (base / "subdir" / "file2.txt").touch()
    (tmp_path / "outside_dir").mkdir(exist_ok=True)
    (tmp_path / "outside_dir" / "outside_file.txt").touch()

    tests = [("file1.txt",True),
             ("subdir/file2.txt",True),
             ("../outside_file.txt",False),
             ( "../outside_dir/outside_file.txt",False),
             ("subdir/file1.txt",True),
             ("subdir/../file1.txt", False),
             ("subdir/../subdir/file2.txt", False),
             ("subdir/../subdir/../file1.txt", False),
             ("../my_base_dir/file1.txt", False)
            ]
    for fname, ok in tests:
        try:
            sp = safe_path(base, fname)
            print(f"Safe path {fname}: {sp}")
            assert ok
        except HTTPException as e:
            print(f"Unsafe path {fname}: {e}")
            assert not ok
