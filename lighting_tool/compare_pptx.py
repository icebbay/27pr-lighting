"""Compare two .pptx files slide by slide (slide XML, exact).

    python compare_pptx.py A.pptx B.pptx
Prints IDENTICAL or the first differing slides with a short diff hint. Exit code 0 = identical.
"""
import sys, zipfile, re, difflib


def slides(path):
    z = zipfile.ZipFile(path)
    names = sorted((n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)),
                   key=lambda n: int(re.findall(r"\d+", n)[-1]))
    return [z.read(n).decode("utf-8") for n in names]


def compare(a, b, quiet=False):
    A, B = slides(a), slides(b)
    diffs = []
    if len(A) != len(B):
        diffs.append(f"slide count {len(A)} vs {len(B)}")
    for i, (x, y) in enumerate(zip(A, B), 1):
        if x != y:
            xs, ys = re.split(r"(?=<p:sp>|<p:cxnSp>|<p:grpSp>|<p:graphicFrame>)", x), re.split(r"(?=<p:sp>|<p:cxnSp>|<p:grpSp>|<p:graphicFrame>)", y)
            d = [l for l in difflib.unified_diff(xs, ys, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
            diffs.append(f"slide {i}: {len(d)} shape-level changes; first: {d[0][:300] if d else '?'}")
    if not quiet:
        print("IDENTICAL" if not diffs else "DIFFERENT\n  " + "\n  ".join(diffs))
    return not diffs


if __name__ == "__main__":
    sys.exit(0 if compare(sys.argv[1], sys.argv[2]) else 1)
