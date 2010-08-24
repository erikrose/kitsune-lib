#!/usr/bin/env python
"""usage: %prog [options] filename

Parse a document to a simpletree tree, with optional profiling
"""

import sys
import os
from optparse import OptionParser

from html5lib import html5parser, sanitizer
from html5lib.tokenizer import HTMLTokenizer
from html5lib import treebuilders, serializer, treewalkers
from html5lib import constants

def parse():
    optParser = getOptParser()
    opts,args = optParser.parse_args()
    encoding = None

    try:
        f = args[-1]
        # Try opening from the internet
        if f.startswith('http://'):
            try:
                import urllib, cgi
                f = urllib.urlopen(f)
                contentType = f.headers.get('content-type')
                if contentType:
                    (mediaType, params) = cgi.parse_header(contentType)
                    encoding = params.get('charset')
            except: pass
        elif f == '-':
            f = sys.stdin
        else:
            try:
                # Try opening from file system
                f = open(f)
            except IOError: pass
    except IndexError:
        sys.stderr.write("No filename provided. Use -h for help\n")
        sys.exit(1)

    treebuilder = treebuilders.getTreeBuilder(opts.treebuilder)

    if opts.sanitize:
        tokenizer = sanitizer.HTMLSanitizer
    else:
        tokenizer = HTMLTokenizer


    p = html5parser.HTMLParser(tree=treebuilder, tokenizer=tokenizer)

    if opts.fragment:
        parseMethod = p.parseFragment
    else:
        parseMethod = p.parse

    if opts.profile:
        #XXX should import cProfile instead and use that
        import hotshot
        import hotshot.stats
        prof = hotshot.Profile('stats.prof')
        prof.runcall(parseMethod, f, encoding=encoding)
        prof.close()
        # XXX - We should use a temp file here
        stats = hotshot.stats.load('stats.prof')
        stats.strip_dirs()
        stats.sort_stats('time')
        stats.print_stats()
    elif opts.time:
        import time
        t0 = time.time()
        document = parseMethod(f, encoding=encoding)
        t1 = time.time()
        printOutput(p, document, opts)
        t2 = time.time()
        sys.stderr.write("\n\nRun took: %fs (plus %fs to print the output)"%(t1-t0, t2-t1))
    else:
        document = parseMethod(f, encoding=encoding)
        printOutput(p, document, opts)

def printOutput(parser, document, opts):
    if opts.encoding:
        print "Encoding:", parser.tokenizer.stream.charEncoding
    if opts.xml:
        sys.stdout.write(document.toxml("utf-8"))
    elif opts.tree:
        if not hasattr(document,'__getitem__'): document = [document]
        for fragment in document:
            print parser.tree.testSerializer(fragment).encode("utf-8")
    elif opts.hilite:
        sys.stdout.write(document.hilite("utf-8"))
    elif opts.html:
        kwargs = {}
        for opt in serializer.HTMLSerializer.options:
            kwargs[opt] = getattr(opts,opt)
        if not kwargs['quote_char']: del kwargs['quote_char']
        tokens = treewalkers.getTreeWalker(opts.treebuilder)(document)
        for text in serializer.HTMLSerializer(**kwargs).serialize(tokens, encoding='utf-8'):
            sys.stdout.write(text)
        if not text.endswith('\n'): sys.stdout.write('\n')
    if opts.error:
        errList=[]
        for pos, errorcode, datavars in parser.errors:
            errList.append("Line %i Col %i"%pos + " " + constants.E.get(errorcode, 'Unknown error "%s"' % errorcode) % datavars)
        sys.stdout.write("\nParse errors:\n" + "\n".join(errList)+"\n")

def getOptParser():
    parser = OptionParser(usage=__doc__)

    parser.add_option("-p", "--profile", action="store_true", default=False,
                      dest="profile", help="Use the hotshot profiler to "
                      "produce a detailed log of the run")
    
    parser.add_option("-t", "--time",
                      action="store_true", default=False, dest="time",
                      help="Time the run using time.time (may not be accurate on all platforms, especially for short runs)")
    
    parser.add_option("-b", "--treebuilder", action="store", type="string",
                      dest="treebuilder", default="simpleTree")

    parser.add_option("-e", "--error", action="store_true", default=False,
                      dest="error", help="Print a list of parse errors")

    parser.add_option("-f", "--fragment", action="store_true", default=False,
                      dest="fragment", help="Parse as a fragment")

    parser.add_option("", "--tree", action="store_true", default=False,
                      dest="tree", help="Output as debug tree")
    
    parser.add_option("-x", "--xml", action="store_true", default=False,
                      dest="xml", help="Output as xml")
    
    parser.add_option("", "--no-html", action="store_false", default=True,
                      dest="html", help="Don't output html")
    
    parser.add_option("", "--hilite", action="store_true", default=False,
                      dest="hilite", help="Output as formatted highlighted code.")
    
    parser.add_option("-c", "--encoding", action="store_true", default=False,
                      dest="encoding", help="Print character encoding used")

    parser.add_option("", "--inject-meta-charset", action="store_true",
                      default=False, dest="inject_meta_charset",
                      help="inject <meta charset>")

    parser.add_option("", "--strip-whitespace", action="store_true",
                      default=False, dest="strip_whitespace",
                      help="strip whitespace")

    parser.add_option("", "--omit-optional-tags", action="store_true",
                      default=False, dest="omit_optional_tags",
                      help="omit optional tags")

    parser.add_option("", "--quote-attr-values", action="store_true",
                      default=False, dest="quote_attr_values",
                      help="quote attribute values")

    parser.add_option("", "--use-best-quote-char", action="store_true",
                      default=False, dest="use_best_quote_char",
                      help="use best quote character")

    parser.add_option("", "--quote-char", action="store",
                      default=None, dest="quote_char",
                      help="quote character")

    parser.add_option("", "--no-minimize-boolean-attributes",
                      action="store_false", default=True,
                      dest="minimize_boolean_attributes",
                      help="minimize boolean attributes")

    parser.add_option("", "--use-trailing-solidus", action="store_true",
                      default=False, dest="use_trailing_solidus",
                      help="use trailing solidus")

    parser.add_option("", "--space-before-trailing-solidus",
                      action="store_true", default=False,
                      dest="space_before_trailing_solidus",
                      help="add space before trailing solidus")

    parser.add_option("", "--escape-lt-in-attrs", action="store_true",
                      default=False, dest="escape_lt_in_attrs",
                      help="escape less than signs in attribute values")

    parser.add_option("", "--escape-rcdata", action="store_true",
                      default=False, dest="escape_rcdata",
                      help="escape rcdata element values")

    parser.add_option("", "--sanitize", action="store_true", default=False,
                      dest="sanitize", help="sanitize")

    return parser

if __name__ == "__main__":
    parse()
