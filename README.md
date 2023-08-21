aurl
====

A package for splicing URLs into file templates.

This package provides two commands, get:

    Usage: get [OPTIONS] URLS...

      Download a list of URLs.

    Arguments:
      URLS...  urls to download  [required]

and subst:

    Usage: subst [OPTIONS] FNAME

      Fetch and substitute URLs into a template.

    Arguments:
      FNAME  File name to substitute.  [required]

    Options:
      --results                       list required results


## Template Format

Templates can include URLs inside `${{ }}` splices.
The [[tests/template.rc.tpl]] file demonstrates:

    This is a test template

    step1 = ${{ git://code.ornl.gov/DataTrails/1000water }}
    root  = ${{ file:///usr/bin/last }}
    github = ${{ git://github.com/frobnitzem/aiowire }}


## Python API

Examining the source of `subst` reveals a `TemplateFile`
and `Mirror` classes, along with the async
function, `fetch_all`:

    tf = TemplateFile(fname)
    urls = set(tf.uris)

    M = Mirror( Path() )
    lookup = arun(fetch_all(M, urls))
    if lookup is None:
        print("Unable to substitute.")
        return 1
    tf.write(out, lookup)

The `Mirror` class has an `async get(url : URL)` function,
as well as `encode`, and `decode`, which translate
URLs to/from fille paths inside its root.

The `TemplateFile` class parses and prints templates.
