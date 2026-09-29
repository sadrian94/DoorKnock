import typst
from pathlib import Path

def test_typst_smoke(tmp_path: Path):
    source = """
    #set page(paper: "us-letter", margin: 1cm)
    #set text(font: "Liberation Sans", size: 11pt)
    = Candidate Name
    Business Systems & Data Operations Analyst
    """
    typ_file = tmp_path / "test.typ"
    typ_file.write_text(source, encoding="utf-8")
    
    out_pdf = tmp_path / "test.pdf"
    typst.compile(typ_file, output=out_pdf)
    
    assert out_pdf.is_file()
    assert out_pdf.stat().st_size > 500
    print(f"Compiled successfully! PDF size: {out_pdf.stat().st_size} bytes")

if __name__ == "__main__":
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as td:
        test_typst_smoke(Path(td))
