from aurl import __version__

def test_version():
    semver = __version__.split('.')
    assert len(semver) == 3
    for i in semver:
        for j in i:
            assert ord('0') <= ord(j) and ord(j) <= ord('9')
