from __future__ import annotations

from unittest.mock import Mock

import pytest

from atlasctl.errors import AtlasCtlError, raise_for_response, require_parsed


def test_raise_for_response_passes_through_2xx():
    raise_for_response(Mock(status_code=204))


def test_raise_for_response_raises_with_the_body_on_failure():
    response = Mock(status_code=404, content=b"not found")
    with pytest.raises(AtlasCtlError, match="404: not found"):
        raise_for_response(response)


def test_require_parsed_returns_the_parsed_body():
    response = Mock(status_code=200, parsed="the-model")
    assert require_parsed(response) == "the-model"


def test_require_parsed_raises_on_a_2xx_status_with_no_parsed_body():
    # Regression: found by test_vm_commands using the wrong mock status code —
    # each generated endpoint only parses one exact success status (201 for a
    # create, 202 for an action, ...); a 2xx response on any other code passes
    # raise_for_response but leaves .parsed as None, which used to crash deep
    # in output.py with an unhelpful AttributeError instead of a clear message.
    response = Mock(status_code=200, parsed=None)
    with pytest.raises(AtlasCtlError, match="doesn't recognize"):
        require_parsed(response)


def test_require_parsed_raises_the_status_error_first():
    response = Mock(status_code=404, content=b"not found", parsed=None)
    with pytest.raises(AtlasCtlError, match="404"):
        require_parsed(response)
