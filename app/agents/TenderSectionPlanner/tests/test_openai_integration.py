import os

import pytest


@pytest.mark.skipif(
    os.getenv("RUN_OPENAI_INTEGRATION_TEST", "").lower() != "true",
    reason="Set RUN_OPENAI_INTEGRATION_TEST=true for the paid manual smoke test",
)
def test_manual_openai_integration_is_explicitly_opt_in():
    # The full integration path requires matching live MongoDB fixtures. This guard
    # prevents accidental paid calls during normal unit-test execution.
    assert os.getenv("OPENAI_API_KEY")
