# converts vim documentation to html

import sys
import re
import cgi
import urllib
import logging


HEADER1 = """
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>
<head>
<title>Vim: {filename}</title>
<link rel="stylesheet" href="vim-stylesheet.css" type="text/css"/>
</head>
<body>
"""

START_HEADER = """
<h1>Vim help files</h1>
<p>This is an HTML version of the <a href="http://www.vim.org/"
target="_blank">Vim</a> help pages. They are kept up-to-date automatically from
the Vim source repository.</p>
"""

SITENAVI = """
<p>
Quick links:
<a href="/">help overview</a> &middot;
<a href="quickref.txt.html">quick reference</a> &middot;
<a href="usr_toc.txt.html">user manual toc</a> &middot;
<a href="help.txt.html#reference_toc">reference manual toc</a>
</p>
"""

SITESEARCH = """
<div id="cse" style="width: 100%;">Loading Google custom search</div>
<script src="http://www.google.com/jsapi" type="text/javascript"></script>
<script type="text/javascript">
  google.load('search', '1', {language : 'en'});
  google.setOnLoadCallback(function() {
    var customSearchControl = new google.search.CustomSearchControl('007529716539815883269:a71bug8rd0k');
    customSearchControl.setResultSetSize(google.search.Search.FILTERED_CSE_RESULTSET);
    customSearchControl.draw('cse');
  }, true);
</script>
"""

HEADER2 = """
<div id="d1">
<div id="d2">
<pre style="visibility: hidden">                                                                                </pre>
<div id="d3">
<pre>
"""

FOOTER = '</pre><hr/>'

FOOTER2 = """
<p style="font-size: 85%">This site is maintained by Carlo Teubner (<i>(my first name) dot (my last name) at gmail dot com</i>).</p>
</div></div></div>
</body>
</html>
"""

RE_TAGLINE = re.compile(r'(\S+)\s+(\S+)')

PAT_PIPEWORD = r'(?P<pipe>(?<!\\)\|[#-)!+-~]+\|)'
PAT_STARWORD = r'(?P<star>\*[#-)!+-~]+\*(?:(?=\s)|$))'
PAT_OPTWORD  = r"(?P<opt>'(?:[a-z]{2,}|t_..)')"
PAT_CTRL     = r'(?P<ctrl>CTRL-(?:W_)?(?:[\w\[\]^+-<>=]|<[A-Za-z]+?>)?)'
PAT_SPECIAL  = r'(?P<special><.*?>|\{.*?}|' + \
	       r'\[(?:range|line|count|offset|\+?cmd|[-+]?num|\+\+opt|' + \
	       r'arg|arg(?:uments)|ident|addr|group)]|' + \
	       r'\s\[[-a-z^A-Z0-9_]{2,}])'
PAT_TITLE    = r'(?P<title>Vim version [0-9.a-z]+|VIM REFERENCE.*)'
PAT_NOTE     = r'(?P<note>Notes?:?)'
PAT_HEADER   = r'(?P<header>^.*~$)'
PAT_URL      = r'(?P<url>(?:https?|ftp)://[^\'"<> \t]+[a-zA-Z0-9/])'
PAT_WORD     = r'(?P<word>[!#-)+-{}~]+)'
RE_LINKWORD = re.compile(
	PAT_OPTWORD  + '|' + \
	PAT_CTRL     + '|' + \
	PAT_SPECIAL)
RE_TAGWORD = re.compile(
	PAT_PIPEWORD + '|' + \
	PAT_STARWORD + '|' + \
	PAT_OPTWORD  + '|' + \
	PAT_CTRL     + '|' + \
	PAT_SPECIAL  + '|' + \
	PAT_TITLE    + '|' + \
	PAT_NOTE     + '|' + \
	PAT_HEADER   + '|' + \
	PAT_URL      + '|' + \
	PAT_WORD)
RE_NEWLINE  = re.compile(r'[\r\n]')
RE_HRULE    = re.compile(r'[-=]{3,}.*[-=]{3,3}$')
RE_EG_START = re.compile(r'(?:.* )?>$')
RE_EG_END   = re.compile(r'\S')
RE_SECTION  = re.compile(r'[-A-Z .][-A-Z0-9 .()]*(?=\s+\*)')

class Link:
    def __init__(self, link_pipe, link_plain):
	self.link_pipe = link_pipe
	self.link_plain = link_plain

class VimH2H:
    urls = { }

    def __init__(self, tags):
	count = 0
	for line in RE_NEWLINE.split(tags):
	    m = RE_TAGLINE.match(line)
	    if m:
		tag, filename = m.group(1, 2)
		part1 = '<a href="' + filename + '.html#' + \
			urllib.quote_plus(tag) + '"'
		part2 = '>' + cgi.escape(tag) + '</a>'
		link_pipe = part1 + ' class="l"' + part2
		classattr = ' class="d"'
		m = RE_LINKWORD.match(tag)
		if m:
		    opt, ctrl, special = m.group('opt', 'ctrl', 'special')
		    if opt is not None: classattr = ' class="o"'
		    elif ctrl is not None: classattr = ' class="k"'
		    elif special is not None: classattr = ' class="s"'
		link_plain = part1 + classattr + part2
		self.urls[tag] = Link(link_pipe, link_plain)
		count += 1
	logging.debug("processed %d tags", count)

    def maplink(self, tag, css_class = None):
	links = self.urls.get(tag)
	if links is not None:
	    if css_class == 'l': return links.link_pipe
	    else: return links.link_plain
	elif css_class is not None:
	    return '<span class="' + css_class + '">' + cgi.escape(tag) + \
		    '</span>'
	else: return cgi.escape(tag)

    def to_html(self, filename, contents, include_sitesearch = True):
	logging.debug("to_html(" + filename + ", len = " + \
		str(len(contents)) + ")")

	out = [ ]

	inexample = 0
	for line in RE_NEWLINE.split(contents):
	    line = line.rstrip('\r\n')
	    line_tabs = line
	    line = line.expandtabs()
	    if RE_HRULE.match(line):
		out.append('<span class="h">' + line + '</span>\n')
		continue
	    if inexample == 2:
		if RE_EG_END.match(line):
		    inexample = 0
		    if line[0] == '<': line = line[1:]
		else:
		    out.append('<span class="e">' + cgi.escape(line) +
			    '</span>\n')
		    continue
	    if RE_EG_START.match(line_tabs):
		inexample = 1
		line = line[0:-1]
	    if RE_SECTION.match(line_tabs):
		m = RE_SECTION.match(line)
		out.append(m.expand(r'<span class="c">\g<0></span>'))
		line = line[m.end():]
	    lastpos = 0
	    for match in RE_TAGWORD.finditer(line):
		pos = match.start()
		if pos > lastpos:
		    out.append(cgi.escape(line[lastpos:pos]))
		lastpos = match.end()
		pipeword, starword, opt, ctrl, special, title, note, \
			header, url, word = \
			match.group('pipe', 'star', 'opt', 'ctrl',
			'special', 'title', 'note', 'header', 'url', 'word')
		if pipeword is not None:
		    out.append(self.maplink(pipeword[1:-1], 'l'))
		elif starword is not None:
		    tag = starword[1:-1]
		    out.append('<a name="' + urllib.quote_plus(tag) +
			    '" class="t">' + cgi.escape(tag) + '</a>')
		elif opt is not None:
		    out.append(self.maplink(opt, 'o'))
		elif ctrl is not None:
		    out.append(self.maplink(ctrl, 'k'))
		elif special is not None:
		    out.append(self.maplink(special, 's'))
		elif title is not None:
		    out.append('<span class="i">' +
			    cgi.escape(title) + '</span>')
		elif note is not None:
		    out.append('<span class="n">' +
			    cgi.escape(note) + '</span>')
		elif header is not None:
		    out.append('<span class="h">' +
			    cgi.escape(header[:-1]) + '</span>')
		elif url is not None:
		    out.append('<a class="u" href="' + url + '">' +
			    cgi.escape(url) + '</a>')
		elif word is not None:
		    out.append(self.maplink(word))
	    if lastpos < len(line):
		out.append(cgi.escape(line[lastpos:]))
	    out.append('\n')
	    if inexample == 1: inexample = 2

	return HEADER1.replace('{filename}', filename) + \
		(START_HEADER if filename == 'help.txt' else '') + \
		SITENAVI + \
		(SITESEARCH if include_sitesearch else '') + \
		HEADER2 + \
		''.join(out) + \
		FOOTER + \
		SITENAVI + \
		FOOTER2

