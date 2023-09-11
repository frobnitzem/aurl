"""
Defines template strings and files for URL substitution.

See subst.py for code that performs the actual
substitution.
"""
from typing import Mapping, Sequence, Union, Tuple
from pathlib import Path

from .urls import URL

def parse_template(t : str) -> Tuple[Sequence[str], Sequence[URL]]:
    # Return a parsed form of the template string
    # as a sequence of strings, in-between which 
    # the URL-s should be inserted.
    #
    # The intended output starts and ends with a str
    # so that len(texts) == len(uris)+1
    start = '${{'
    end = '}}'
    ls = len(start)
    le = len(end)

    texts = []
    uris = []
    # Consume all instances of '${{ ... }}' template in string,
    # parsing all URL-s in-between.
    while True:
        i = t.find(start)
        if i == -1:
            break
        j = t[i+ls:].find(end)+i+ls
        if j == -1:
            raise SyntaxError(f"Missing '{end}' in '{t}'")

        texts.append( t[:i] )
        uris.append( URL(t[i+ls:j].strip()) )
        t = t[j+le:]

    texts.append(t)

    return texts, uris

class Template:
    """ Class encapsulating a string to be templated.

        Segments the input string (t) into
        self.texts and self.urls
        with len(self.texts) == len(self.urls)+1
    """
    def __init__(self, t : str):
        texts, uris = parse_template(t)
        self.texts = texts
        self.uris = uris

    def subst(self, cache : Mapping[URL, Path]) -> str:
        # substitute the template
        ans = self.texts[0]
        for u,t in zip(self.uris, self.texts[1:]):
            ans = ans + str(cache[u]) + t
        return ans

class TemplateFile(Template):
    # Class encapsulating a file to be templated.
    def __init__(self, f : Union[str, Path]):
        self.f = Path(f)
        super().__init__(self.f.read_text(encoding='utf-8'))

    def write(self, out : Union[str, Path], cache : Mapping[URL, Path]) -> None:
        # Over-write the input file with the mapped result.
        with open(out, 'w', encoding='utf-8') as f:
            f.write(self.subst(cache))
