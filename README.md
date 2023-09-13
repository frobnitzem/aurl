[![CI](https://github.com/frobnitzem/aurl/actions/workflows/python-package.yml/badge.svg)](https://github.com/frobnitzem/aurl/actions)
[![Coverage](https://codecov.io/github/frobnitzem/aurl/branch/main/graph/badge.svg)](https://app.codecov.io/gh/frobnitzem/aurl)

aurl
====

A package for maintaining a download mirror / cache
and splicing URLs into file templates.

This package provides two commands, get:

    Usage: get [OPTIONS] URLS...

      Download a list of URLs.

    Arguments:
      URLS...  urls to download  [required]

and subst:

    Usage: subst [OPTIONS] TEMPLATES...

      Fetch and substitute URLs into a template.

    Arguments:
      TEMPLATES...  File(s) to substitute.  [required]

    Options:
      --results / --no-results        Don't substitute, but list required results.
                                      [default: no-results]


## Template Format

Templates can include URLs inside `${{ }}` splices.
The [[tests/template.rc.tpl]] file demonstrates:

    This is a test template

    step1 = ${{ git://code.ornl.gov/DataTrails/1000water }}
    root  = ${{ file:///usr/bin/last }}
    github = ${{ git://github.com/frobnitzem/aiowire }}


## Python API

Examining the source of `subst` reveals a `TemplateFile` and `Mirror` classes.
The `TemplateFile` class parses and prints templates.
Mirror provides the async functions `fetch` and `fetch_all`:

    tf = TemplateFile(fname)
    urls = set(tf.uris)

    M = Mirror( Path() )
    lookup = arun(M.fetch_all(urls))
    tf.write(out, lookup)

The `Mirror` class also has `encode`, and `decode`, which translate
URLs to/from fille paths inside the mirror's root path.
