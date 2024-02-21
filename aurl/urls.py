from typing import Optional, Union
from pathlib import Path
import os, logging

from urllib.parse import urlparse, parse_qs, quote, unquote

class URL:
    """Parsed URL object.

    Fully parse a string into URL components
    and validate against valid URL formats.
   
    Attributes:

    * scheme   : str
    * netloc   : str
    * path     : str
    * query    : {key:val}
    * fragment : str

    """
    def __init__(self, s1 : Union[str, 'URL'], validate=True):
        if isinstance(s1, str):
            s = s1
        else:
            s = s.s # type: ignore[attr-defined]
        ans = urlparse(s, scheme='', allow_fragments=True)
        
        # store metadata
        if ans.query != "":
            self.meta = f"?{ans.query}"
        else:
            self.meta = ""
        if ans.fragment != "":
            self.meta = f"{self.meta}#{ans.fragment}"

        self.scheme = unquote(ans.scheme)
        self.netloc = unquote(ans.netloc)
        assert "%2F" not in ans.path, "Invalid path."
        self.path = unquote(ans.path)
        if self.scheme != "file": # remove leading '/' in paths
            if self.path.startswith("/"):
                self.path = self.path[1:]
        if len(ans.query) > 0:
            self.query = parse_qs(ans.query,
                              keep_blank_values=True,
                              strict_parsing=True,
                              errors="strict")
        else:
            self.query = {}
        self.fragment = unquote(ans.fragment)
        self.s = ans.geturl()
        if not validate:
            return
        try:
            self.validate()
        except AssertionError as e:
            raise AssertionError(f"Invalid URL format: {self.s} -- {e}")

    def with_scheme(self, scheme):
        return urlparse(self.s, scheme="", allow_fragments=True) \
                  . _replace(scheme=scheme) \
                  . geturl()

    def __repr__(self):
        return f"URL('{self.s}')"
    def __str__(self):
        return self.s
    def __hash__(self):
        return hash(repr(self))
    def __eq__(a, b):
        return repr(a) == repr(b)
    def fullpath(self):
        if self.scheme == "file":
            return self.path
        s = self.netloc
        if len(self.path) > 0:
            s += '/' + self.path
        return s
    def validate(url):
        absent = lambda x: len(getattr(url, x)) == 0
        # netloc, path, query, fragment
        if url.scheme in ["file", "git", "git+file", "git+http",
                          "git+https", "git+ssh"]:
            assert absent("query") and absent("fragment")
        elif url.scheme in ["result"]:
            assert absent("query")
        elif url.scheme == "https" or url.scheme == "http":
            assert absent("fragment")
        else:
            raise AssertionError(f"Unknown URL scheme: {url.scheme}")

