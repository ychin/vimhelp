# Translates Vim documentation to HTML

import flask
import functools
import html
import re
import urllib.parse


class VimProject:
    name = "Vim"
    contrasted_name = "the original Vim"
    url = "https://www.vim.org/"
    vimdoc_site = "vimhelp.org"
    doc_src_url = "https://github.com/vim/vim/tree/master/runtime/doc"
    favicon_notice = "favicon is based on http://amnoid.de/tmp/vim_solidbright_512.png and is used with permission by its author"


class NeovimProject:
    name = "Neovim"
    contrasted_name = "Neovim"
    url = "https://neovim.io/"
    vimdoc_site = "neo.vimhelp.org"
    doc_src_url = "https://github.com/neovim/neovim/tree/master/runtime/doc"
    favicon_notice = "favicon taken from https://neovim.io/favicon.ico, which is licensed under CC-BY-3.0: https://creativecommons.org/licenses/by/3.0/"


VimProject.other = NeovimProject
NeovimProject.other = VimProject


PROJECTS = {"vim": VimProject, "neovim": NeovimProject}

FAQ_LINE = '<a href="vim_faq.txt.html#vim_faq.txt" class="l">vim_faq.txt</a>   Frequently Asked Questions\n'

RE_TAGLINE = re.compile(r"(\S+)\s+(\S+)")

PAT_WORDCHAR = "[!#-)+-{}~\xC0-\xFF]"

PAT_HEADER = r"(^.*~$)"
PAT_GRAPHIC = r"(^.* `$)"
PAT_PIPEWORD = r"(?<!\\)\|([#-)!+-{}~]+)\|"
PAT_STARWORD = r"\*([#-)!+-~]+)\*(?:(?=\s)|$)"
PAT_COMMAND = r"`([^` ]+)`"
PAT_OPTWORD = r"('(?:[a-z]{2,}|t_..)')"
PAT_CTRL = r"((?:CTRL(?:-SHIFT)?|META|ALT)-(?:W_)?(?:\{char\}|<[A-Za-z]+?>|.)?)"
PAT_SPECIAL = (
    r"(<(?:[-a-zA-Z0-9_]+|[SCM]-.)>|\{.+?}|"
    r"\[(?:range|line|count|offset|\+?cmd|[-+]?num|\+\+opt|"
    r"arg|arguments|ident|addr|group)]|"
    r"(?<=\s)\[[-a-z^A-Z0-9_]{2,}])"
)
PAT_TITLE = r"(Vim version [0-9.a-z]+|N?VIM REFERENCE.*)"
PAT_NOTE = (
    r"((?<!" + PAT_WORDCHAR + r")(?:note|NOTE|Notes?):?(?!" + PAT_WORDCHAR + r"))"
)
PAT_URL = r'((?:https?|ftp)://[^\'"<> \t]+[a-zA-Z0-9/])'
PAT_WORD = (
    r"((?<!" + PAT_WORDCHAR + r")" + PAT_WORDCHAR + r"+(?!" + PAT_WORDCHAR + r"))"
)

RE_LINKWORD = re.compile(PAT_OPTWORD + "|" + PAT_CTRL + "|" + PAT_SPECIAL)
# fmt: off
RE_TAGWORD = re.compile(
    PAT_HEADER + "|" +
    PAT_GRAPHIC + "|" +
    PAT_PIPEWORD + "|" +
    PAT_STARWORD + "|" +
    PAT_COMMAND + "|" +
    PAT_OPTWORD + "|" +
    PAT_CTRL + "|" +
    PAT_SPECIAL + "|" +
    PAT_TITLE + "|" +
    PAT_NOTE + "|" +
    PAT_URL + "|" +
    PAT_WORD
)
# fmt: on
RE_NEWLINE = re.compile(r"[\r\n]")
RE_HRULE = re.compile(r"(?:===.*===|---.*---)$")
RE_HRULE1 = re.compile(r"===.*===$")
RE_HEADING = re.compile(
    r"[0-9. *]*"
    r"(?! *vim:| *Next chapter:| *Copyright: | *Table of contents:| *Advance information about|$)"
    r"(.+?) *(?:\*|~?$)"
)
RE_EG_START = re.compile(r"(?:.* )?>$")
RE_EG_END = re.compile(r"[^ \t]")
RE_SECTION = re.compile(r"(?!NOTE$|CTRL-|\.\.\.$)([A-Z.][-A-Z0-9 .,()_?]*)(?:\s+\*|$)")
RE_STARTAG = re.compile(r'\*([^ \t"*]+)\*(?:\s|$)')
RE_LOCAL_ADD = re.compile(r"LOCAL ADDITIONS:\s+\*local-additions\*$")


class Link:
    def __init__(self, filename, htmlfilename, tag):
        self.filename = filename
        self._htmlfilename = htmlfilename
        if tag == "help-tags" and filename == "tags":
            self._tag_quoted = None
        else:
            self._tag_quoted = urllib.parse.quote_plus(tag)
        self._tag_escaped = html_escape(tag)
        self._cssclass = "d"
        if m := RE_LINKWORD.match(tag):
            opt, ctrl, special = m.groups()
            if opt is not None:
                self._cssclass = "o"
            elif ctrl is not None:
                self._cssclass = "k"
            elif special is not None:
                self._cssclass = "s"

    @functools.cache
    def href(self, is_same_doc):
        if self._tag_quoted is None:
            return self._htmlfilename
        doc = "" if is_same_doc else self._htmlfilename
        return f"{doc}#{self._tag_quoted}"

    @functools.cache
    def html(self, is_pipe, is_same_doc):
        cssclass = "l" if is_pipe else self._cssclass
        return (
            f'<a href="{self.href(is_same_doc)}" class="{cssclass}">'
            f"{self._tag_escaped}</a>"
        )


class VimH2H:
    def __init__(self, mode="online", project="vim", version=None, tags=None):
        self._mode = mode
        self._project = PROJECTS[project]
        self._version = version
        self._urls = {}
        if tags is not None:
            for line in RE_NEWLINE.split(tags):
                if m := RE_TAGLINE.match(line):
                    tag, filename = m.group(1, 2)
                    self.do_add_tag(filename, tag)
        self._urls["help-tags"] = Link("tags", "tags.html", "help-tags")

    def add_tags(self, filename, contents):
        in_example = False
        for line in RE_NEWLINE.split(contents):
            if in_example:
                if RE_EG_END.match(line):
                    in_example = False
                else:
                    continue
            for anchor in RE_STARTAG.finditer(line):
                tag = anchor.group(1)
                self.do_add_tag(filename, tag)
            if RE_EG_START.match(line):
                in_example = True

    def do_add_tag(self, filename, tag):
        if self._mode == "online" and filename == "help.txt":
            htmlfilename = "/"
        else:
            htmlfilename = filename + ".html"
        self._urls[tag] = Link(filename, htmlfilename, tag)

    def sorted_tag_href_pairs(self):
        result = [
            (tag, link.href(is_same_doc=False)) for tag, link in self._urls.items()
        ]
        result.sort()
        return result

    def maplink(self, tag, curr_filename, css_class=None):
        links = self._urls.get(tag)
        if links is not None:
            is_pipe = css_class == "l"
            is_same_doc = links.filename == curr_filename
            return links.html(is_pipe, is_same_doc)
        elif css_class is not None:
            return f'<span class="{css_class}">{html_escape(tag)}</span>'
        else:
            return html_escape(tag)

    def synthesize_tag(self, curr_filename, text):
        def xform(c):
            if c.isalnum():
                return c.lower()
            elif c in " ,.?!'\"":
                return "-"
            else:
                return ""

        base_tag = "_" + "".join(map(xform, text[:25]))
        tag = base_tag
        i = 0
        while True:
            link = self._urls.get(tag)
            if link is None or link.filename != curr_filename:
                return tag
            tag + f"{base_tag}_{i}"
            i += 1

    @staticmethod
    def prelude(theme):
        return flask.render_template("prelude.html", theme=theme)

    def to_html(self, filename, contents):
        is_help_txt = filename == "help.txt"
        lines = [line.rstrip("\r\n") for line in RE_NEWLINE.split(contents)]

        out = []
        sidebar_headings = []
        in_example = False
        for idx, line in enumerate(lines):
            line_tabs = line
            line = line.expandtabs()
            prev_line_tabs = "" if idx == 0 else lines[idx - 1]
            if prev_line_tabs == "" and idx > 1:
                prev_line_tabs = lines[idx - 2]
            if in_example:
                if RE_EG_END.match(line):
                    in_example = False
                    if line[0] == "<":
                        line = line[1:]
                else:
                    out.extend(('<span class="e">', html_escape(line), "</span>\n"))
                    continue
            if RE_HRULE.match(line_tabs):
                out.extend(('<span class="h">', html_escape(line), "</span>\n"))
                continue
            if RE_EG_START.match(line_tabs):
                in_example = True
                line = line[:-1]
            span_opened = False
            if m := RE_SECTION.match(line_tabs):
                out.extend(('<span class="c">', m.group(1), "</span>"))
                line = line[m.end(1) :]
            elif RE_HRULE1.match(prev_line_tabs) and (m := RE_HEADING.match(line)):
                heading = m.group(1)
                if m := RE_STARTAG.search(line):
                    tag = m.group(1)
                else:
                    tag = self.synthesize_tag(filename, heading)
                    out.append(f'<span id="{tag}">')
                    span_opened = True
                tag_escaped = urllib.parse.quote_plus(tag)
                sidebar_headings.append(
                    flask.Markup(f'<a href="#{tag_escaped}">{html_escape(heading)}</a>')
                )
            is_faq_line = (
                self._project is VimProject
                and is_help_txt
                and RE_LOCAL_ADD.match(line_tabs)
            )
            lastpos = 0
            for match in RE_TAGWORD.finditer(line):
                pos = match.start()
                if pos > lastpos:
                    out.append(html_escape(line[lastpos:pos]))
                lastpos = match.end()
                # fmt: off
                (header, graphic, pipeword, starword, command, opt, ctrl, special,
                 title, note, url, word) = match.groups()
                # fmt: on
                if pipeword is not None:
                    out.append(self.maplink(pipeword, filename, "l"))
                elif starword is not None:
                    out.extend(
                        (
                            '<span id="',
                            urllib.parse.quote_plus(starword),
                            '" class="t">',
                            html_escape(starword),
                            "</span>",
                        )
                    )
                elif command is not None:
                    out.extend(('<span class="e">', html_escape(command), "</span>"))
                elif opt is not None:
                    out.append(self.maplink(opt, filename, "o"))
                elif ctrl is not None:
                    out.append(self.maplink(ctrl, filename, "k"))
                elif special is not None:
                    out.append(self.maplink(special, filename, "s"))
                elif title is not None:
                    out.extend(('<span class="i">', html_escape(title), "</span>"))
                elif note is not None:
                    out.extend(('<span class="n">', html_escape(note), "</span>"))
                elif header is not None:
                    out.extend(
                        ('<span class="h">', html_escape(header[:-1]), "</span>")
                    )
                elif graphic is not None:
                    out.append(html_escape(graphic[:-2]))
                elif url is not None:
                    out.extend(
                        ('<a class="u" href="', url, '">', html_escape(url), "</a>")
                    )
                elif word is not None:
                    out.append(self.maplink(word, filename))
            if lastpos < len(line):
                out.append(html_escape(line[lastpos:]))
            if span_opened:
                out.append("</span>")
            out.append("\n")
            if is_faq_line:
                out.append(FAQ_LINE)

        static_dir = "/" if self._mode == "online" else ""
        helptxt = "./" if self._mode == "online" else "help.txt.html"

        return flask.render_template(
            "page.html",
            mode=self._mode,
            project=self._project,
            version=self._version,
            filename=filename,
            static_dir=static_dir,
            helptxt=helptxt,
            content=flask.Markup("".join(out)),
            sidebar_headings=sidebar_headings,
        )


@functools.cache
def html_escape(s):
    return html.escape(s, quote=False)
