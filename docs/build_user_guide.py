"""Export the user guide docs/USER_GUIDE.md to Word (.docx) with pandoc.

The Markdown file is the source of truth (it also renders on GitHub). The Word
look comes from a reference document generated here: pandoc's default
reference.docx with Calibri text, Roboto Mono code blocks on a light background
with a border, syntax highlighting, bordered tables, centred figures and the
template's A4 page margins. Styles are then flattened into direct formatting,
because the document is meant to be imported into Google Docs.

Run:  uv run python docs/build_user_guide.py
"""

from __future__ import annotations

import copy
import subprocess
import tempfile
from pathlib import Path

import pypandoc
from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

DOCS = Path(__file__).resolve().parent
SOURCE = DOCS / "USER_GUIDE.md"
OUTPUT = DOCS / "Инструкция_пользователя_PyRainCloud.docx"

BODY_FONT = "Calibri"
CODE_FONT = "Roboto Mono"  # a Google Font: available in Google Docs
ACCENT = RGBColor(0x1F, 0x3A, 0x5F)
CODE_FILL = "F4F6F8"
BORDER = "D0D7DE"


def _set_font(style, name: str, size: float | None = None) -> None:
    style.font.name = name
    rfonts = style.element.get_or_add_rPr().get_or_add_rFonts()
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), name)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        rfonts.attrib.pop(qn(attr), None)
    if size:
        style.font.size = Pt(size)


def _border(tag: str, sides: tuple[str, ...], color: str = BORDER, size: int = 4):
    el = OxmlElement(tag)
    for side in sides:
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"), "single")
        b.set(qn("w:sz"), str(size))
        b.set(qn("w:space"), "4")
        b.set(qn("w:color"), color)
        el.append(b)
    return el


def _shading(fill: str):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    return shd


def _insert_in_order(parent, el, successors: tuple[str, ...]) -> None:
    """Insert ``el`` before the first existing successor (OOXML child order matters)."""
    tags = {qn(t) for t in successors}
    for child in parent:
        if child.tag in tags:
            child.addprevious(el)
            return
    parent.append(el)


def make_reference(path: Path) -> None:
    path.write_bytes(
        subprocess.run(
            [pypandoc.get_pandoc_path(), "--print-default-data-file", "reference.docx"],
            capture_output=True,
            check=True,
        ).stdout
    )
    doc = Document(str(path))
    styles = doc.styles

    for name in ("Normal", "Body Text", "First Paragraph", "Compact"):
        if name in styles:
            _set_font(styles[name], BODY_FONT, 11)
    styles["Body Text"].paragraph_format.space_after = Pt(6)

    for name, size in (("Title", 22), ("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 12)):
        st = styles[name]
        _set_font(st, BODY_FONT, size)
        st.font.bold = True
        st.font.color.rgb = ACCENT
        st.paragraph_format.keep_with_next = True
    styles["Heading 1"].paragraph_format.space_before = Pt(18)
    styles["Heading 2"].paragraph_format.space_before = Pt(12)

    # pandoc only adds its own code styles when the reference lacks them, so define ours.
    if "Verbatim Char" not in styles:
        styles.add_style("Verbatim Char", WD_STYLE_TYPE.CHARACTER)
    if "Source Code" not in styles:
        styles.add_style("Source Code", WD_STYLE_TYPE.PARAGRAPH).base_style = styles["Normal"]

    # Code blocks: the whole paragraph on a light background with a thin border.
    code = styles["Source Code"]
    _set_font(code, CODE_FONT, 9.5)
    ppr = code.element.get_or_add_pPr()
    after_bdr = ("w:shd", "w:tabs", "w:suppressAutoHyphens", "w:spacing", "w:ind", "w:jc", "w:rPr")
    _insert_in_order(ppr, _border("w:pBdr", ("top", "left", "bottom", "right")), after_bdr)
    _insert_in_order(ppr, _shading(CODE_FILL), after_bdr[1:])
    code.paragraph_format.space_before = Pt(4)
    code.paragraph_format.space_after = Pt(8)
    code.paragraph_format.left_indent = Cm(0.2)
    code.paragraph_format.right_indent = Cm(0.2)
    _set_font(styles["Verbatim Char"], CODE_FONT, 9.5)

    for name in ("Captioned Figure", "Figure"):
        if name in styles:
            styles[name].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            styles[name].paragraph_format.keep_with_next = True
    for name in ("Image Caption", "Table Caption"):
        if name in styles:
            st = styles[name]
            _set_font(st, BODY_FONT, 9.5)
            st.font.italic = True
            st.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
            st.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            st.paragraph_format.space_after = Pt(12)

    # Tables: thin grey grid.
    tbl_pr = styles["Table"].element.find(qn("w:tblPr"))
    for old in tbl_pr.findall(qn("w:tblBorders")):
        tbl_pr.remove(old)
    _insert_in_order(
        tbl_pr,
        _border("w:tblBorders", ("top", "left", "bottom", "right", "insideH", "insideV")),
        ("w:shd", "w:tblLayout", "w:tblCellMar", "w:tblLook", "w:tblCaption"),
    )

    # Page: A4 with the template's margins.
    for section in doc.sections:
        section.page_width, section.page_height = Cm(21), Cm(29.7)
        section.top_margin = section.bottom_margin = Cm(2)
        section.left_margin, section.right_margin = Cm(3), Cm(1.5)
        section.header_distance = section.footer_distance = Cm(1.25)
        section.gutter = Cm(0)
    doc.save(str(path))


P_ORDER = (
    "pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr", "widowControl", "numPr",
    "suppressLineNumbers", "pBdr", "shd", "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
    "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
    "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc",
    "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl", "divId", "cnfStyle",
    "rPr", "sectPr", "pPrChange",
)  # fmt: skip
R_ORDER = (
    "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps", "strike", "dstrike",
    "outline", "shadow", "emboss", "imprint", "noProof", "snapToGrid", "vanish", "webHidden",
    "color", "spacing", "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect", "bdr",
    "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang", "eastAsianLayout", "specVanish",
)  # fmt: skip
# Styles Google Docs maps to its own; everything else is flattened into direct formatting.
NATIVE_STYLES = {"Normal", "Title", "Heading1", "Heading2", "Heading3", "Hyperlink"}


def _merge(target, source, order: tuple[str, ...]) -> None:
    """Copy children of ``source`` missing in ``target``, keeping the schema order."""
    rank = {qn(f"w:{t}"): i for i, t in enumerate(order)}
    present = {child.tag for child in target}
    for child in source:
        if child.tag in present or child.tag not in rank:
            continue
        el = copy.deepcopy(child)
        later = [c for c in target if rank.get(c.tag, len(order)) > rank[child.tag]]
        if later:
            later[0].addprevious(el)
        else:
            target.append(el)


def _style_chain(styles_el, style_id: str) -> list:
    """The style and its ``basedOn`` ancestors, most specific first."""
    chain = []
    while style_id:
        st = styles_el.find(f"w:style[@w:styleId='{style_id}']", styles_el.nsmap)
        if st is None or st in chain:
            break
        chain.append(st)
        based = st.find(qn("w:basedOn"))
        style_id = based.get(qn("w:val")) if based is not None else None
        if style_id in NATIVE_STYLES:
            break
    return chain


def flatten_styles(doc) -> None:
    """Google Docs drops character and custom paragraph styles on import.

    Write their formatting (code font, shading, borders, token colours, captions)
    directly onto every paragraph and run so the document looks the same there.
    """
    styles_el = doc.styles.element
    body = doc.element.body
    for p in body.iter(qn("w:p")):
        ppr = p.find(qn("w:pPr"))
        pstyle = ppr.find(qn("w:pStyle")) if ppr is not None else None
        pid = pstyle.get(qn("w:val")) if pstyle is not None else None
        chain = _style_chain(styles_el, pid) if pid and pid not in NATIVE_STYLES else []
        for st in chain:
            if st.find(qn("w:pPr")) is not None:
                _merge(p.get_or_add_pPr(), st.find(qn("w:pPr")), P_ORDER)
        para_rpr = [st.find(qn("w:rPr")) for st in chain if st.find(qn("w:rPr")) is not None]
        for r in p.iter(qn("w:r")):
            rpr = r.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr")
                r.insert(0, rpr)
            rstyle = rpr.find(qn("w:rStyle"))
            rid = rstyle.get(qn("w:val")) if rstyle is not None else None
            if rid and rid not in NATIVE_STYLES:
                for st in _style_chain(styles_el, rid):
                    if st.find(qn("w:rPr")) is not None:
                        _merge(rpr, st.find(qn("w:rPr")), R_ORDER)
            for src in para_rpr:
                _merge(rpr, src, R_ORDER)


def finish(path: Path) -> None:
    """Flatten styles for Google Docs, shade table header rows, set properties."""
    doc = Document(str(path))
    flatten_styles(doc)
    for table in doc.tables:
        for cell in table.rows[0].cells:
            _insert_in_order(
                cell._tc.get_or_add_tcPr(),
                _shading("E8EEF5"),
                ("w:noWrap", "w:tcMar", "w:textDirection", "w:tcFitText", "w:vAlign", "w:hideMark"),
            )
            for p in cell.paragraphs:
                for run in p.runs:
                    run.bold = True
    doc.core_properties.title = "PyRainCloud — инструкция пользователя"
    doc.core_properties.author = "PyRainCloud"
    doc.save(str(path))


def build() -> Path:
    with tempfile.TemporaryDirectory() as tmp:
        reference = Path(tmp) / "reference.docx"
        make_reference(reference)
        pypandoc.convert_file(
            str(SOURCE),
            "docx",
            format="markdown",
            outputfile=str(OUTPUT),
            extra_args=[
                f"--reference-doc={reference}",
                f"--resource-path={DOCS}",
                "--syntax-highlighting=tango",
            ],
        )
    finish(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(f"Saved {build()}")
