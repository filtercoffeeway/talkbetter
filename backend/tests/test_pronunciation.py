"""Tests for the PRONUNCIATION_PROVIDER dispatch."""
from unittest.mock import patch

import pytest

from app.config import settings
from app.services import pronunciation


def _settings(**overrides):
    return patch.multiple(settings, **overrides)


def test_azure_needs_key_and_region():
    with _settings(pronunciation_provider="azure", azure_speech_key="k", azure_speech_region=""):
        assert not pronunciation.is_available()
    with _settings(pronunciation_provider="azure", azure_speech_key="k", azure_speech_region="eastus"):
        assert pronunciation.is_available()


def test_local_needs_espeak():
    with (
        _settings(pronunciation_provider="local"),
        patch("app.services.pronunciation.shutil.which", return_value=None),
    ):
        assert not pronunciation.is_available()


def test_unknown_provider_is_unavailable_and_rejected():
    with _settings(pronunciation_provider="nope"):
        assert not pronunciation.is_available()
        with pytest.raises(ValueError):
            pronunciation.assess(b"audio", "hello")


def test_assess_dispatches_to_configured_provider():
    with (
        _settings(pronunciation_provider="local"),
        patch("app.services.pronunciation_local.assess", return_value="local-report") as local,
    ):
        assert pronunciation.assess(b"audio", "hello", ".wav") == "local-report"
    local.assert_called_once_with(b"audio", "hello", ".wav")
