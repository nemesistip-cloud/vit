import py_compile

def test_py_compile():
    py_compile.compile('tachyon/main.py', doraise=True)
    py_compile.compile('tachyon/api/router.py', doraise=True)

def test_routes_in_file():
    with open('tachyon/api/router.py') as f:
        content = f.read()
    assert '@router.get("/files")' in content
    assert '@router.post("/files")' in content
    assert '@router.delete("/files/{key:path}")' in content

def test_metrics_in_main():
    with open('tachyon/main.py') as f:
        content = f.read()
    assert '@app.get("/metrics")' in content
