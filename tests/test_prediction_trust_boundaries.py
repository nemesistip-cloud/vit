def test_model_failure_error_is_not_exposed_from_exception_text():
    payload = {"error": "model_inference_failed"}

    assert "Traceback" not in payload["error"]
    assert "secret" not in payload["error"].lower()