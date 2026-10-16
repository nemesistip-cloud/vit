from pathlib import Path
import py_compile

BASE_DIR = Path(__file__).resolve().parent.parent

def test_py_compile():
    py_compile.compile(str(BASE_DIR / 'main.py'), doraise=True)
    py_compile.compile(str(BASE_DIR / 'api' / 'router.py'), doraise=True)

def test_routes_in_file():
    content = (BASE_DIR / 'api' / 'router.py').read_text()
    assert '@router.get("/files")' in content
    assert '@router.post("/files")' in content
    assert '@router.delete("/files/{key:path}")' in content

def test_metrics_in_main():
    content = (BASE_DIR / 'main.py').read_text()
    assert '@app.get("/metrics")' in content
