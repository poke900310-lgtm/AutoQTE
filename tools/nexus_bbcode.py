#!/usr/bin/env python3
r"""Convert NEXUS.md into the BBCode the Nexus description field wants.

    python tools/nexus_bbcode.py          # writes nexus-description.bbcode.txt

The description cannot be written through the API (v3 has no endpoint for it and
v1 is read-only for mods), so it has to be pasted. Generating it from NEXUS.md
keeps the page and the repo in step - hand-maintaining both is how the live page
ended up naming a dead game build and a folder layout that no longer existed.

Prose is emitted unwrapped, one line per paragraph: Nexus reflows to the
reader's width, so baked-in line breaks only fight it. Fenced blocks keep their
line structure inside [code], because a file tree read as a paragraph is noise.
"""
import io
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "NEXUS.md")
OUT = os.path.join(ROOT, "nexus-description.bbcode.txt")


def inline(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"[b]\1[/b]", s)      # bold
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"[i]\1[/i]", s)   # italic
    s = s.replace("`", "")                              # inline code: plain text
    return s.strip()


def main():
    src = io.open(SRC, encoding="utf-8", newline="").read()
    src = src[src.index("## Description"):]   # H1 and summary live in other fields

    out, para, block, fence = [], [], [], False

    def flush_para():
        if para:
            out.append(inline(" ".join(x.strip() for x in para)))
            para.clear()

    def flush_list():
        if block:
            out.append("[list]")
            out.extend("[*]%s[/*]" % x for x in block)
            out.append("[/list]")
            block.clear()

    for ln in src.split("\n"):
        if ln.startswith("```"):
            flush_para(); flush_list()
            out.append("[/code]" if fence else "[code]")
            fence = not fence
            continue
        if fence:
            out.append(ln)                    # verbatim: tree / ini block
            continue
        h = re.match(r"^## (.+)$", ln)
        if h:
            flush_para(); flush_list()
            out += ["", "[heading][size=5]%s[/size][/heading]" % h.group(1)]
            continue
        if ln.startswith("- "):
            flush_para()
            block.append(inline(ln[2:]))
            continue
        if ln.startswith("  ") and block:     # wrapped continuation of a list item
            block[-1] = block[-1].rstrip() + " " + inline(ln)
            continue
        if not ln.strip():
            flush_para(); flush_list()
            out.append("")
            continue
        para.append(ln)
    flush_para(); flush_list()

    text = re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip() + "\n"
    io.open(OUT, "w", encoding="utf-8", newline="").write(text)
    print("wrote %s (%d chars, %d lines)"
          % (os.path.relpath(OUT, ROOT), len(text), text.count("\n")))


if __name__ == "__main__":
    main()
