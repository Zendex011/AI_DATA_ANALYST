import base64
import os
import tempfile
from app.core.chart_generator import run_chart_code


def _make_test_csv() -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(path, "w", encoding="utf-8") as f:
        f.write("x,y\n1,2\n2,4\n3,9\n")
    return path


def test_run_chart_code_with_savefig_directly():
    csv_path = _make_test_csv()
    try:
        b64 = run_chart_code("df.plot(x='x', y='y', kind='line')\nplt.savefig(output_path)", csv_path)
        png = base64.b64decode(b64)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
    finally:
        os.remove(csv_path)


def test_run_chart_code_with_show_only():
    csv_path = _make_test_csv()
    try:
        b64 = run_chart_code("df.plot(x='x', y='y', kind='line')\nplt.show()", csv_path)
        png = base64.b64decode(b64)
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
    finally:
        os.remove(csv_path)
