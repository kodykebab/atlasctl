from __future__ import annotations

import pytest

from atlasctl.config import Config, Region, load_config, save_config
from atlasctl.errors import AtlasCtlError


def test_load_config_when_no_file_exists_yet(config_path):
    config = load_config()
    assert config.regions == {}
    assert config.default is None


def test_save_then_load_round_trips(config_path):
    region = Region(
        name="mumbai",
        base_url="https://mumbai.example.com",
        api_key="k",
        api_secret="s",
        tenant_id=7,
    )
    save_config(Config(regions={"mumbai": region}, default="mumbai"))

    loaded = load_config()

    assert loaded.default == "mumbai"
    assert loaded.regions["mumbai"] == region


def test_config_file_is_owner_only(config_path):
    save_config(Config(regions={}, default=None))
    mode = config_path.stat().st_mode & 0o777
    assert mode == 0o600


def test_get_returns_the_named_region(configured):
    config = load_config()
    assert config.get("test").tenant_id == 42


def test_get_falls_back_to_default_when_no_name_given(configured):
    config = load_config()
    assert config.get(None).name == "test"


def test_get_raises_for_an_unknown_region(configured):
    config = load_config()
    with pytest.raises(AtlasCtlError, match="no region named"):
        config.get("nope")


def test_get_raises_when_nothing_is_configured(config_path):
    config = load_config()
    with pytest.raises(AtlasCtlError, match="no region given"):
        config.get(None)


def test_values_containing_quotes_round_trip(config_path):
    region = Region(
        name='weird"name', base_url="https://x", api_key='a"b', api_secret="s", tenant_id=1
    )
    save_config(Config(regions={region.name: region}, default=None))

    loaded = load_config()

    assert loaded.regions[region.name] == region


def test_a_credential_containing_a_newline_round_trips(config_path):
    # Regression: the escaper used to handle only backslash and double-quote,
    # so a literal newline in a value produced invalid TOML that raised
    # tomllib.TOMLDecodeError on the very next load_config() call.
    region = Region(
        name="x", base_url="https://x", api_key="a\nb", api_secret="tab\there", tenant_id=1
    )
    save_config(Config(regions={"x": region}, default=None))

    loaded = load_config()

    assert loaded.regions["x"] == region


def test_a_newline_in_a_value_is_written_as_an_escape_not_a_raw_byte(config_path):
    region = Region(name="x", base_url="https://x", api_key="a\nb", api_secret="s", tenant_id=1)
    save_config(Config(regions={"x": region}, default=None))

    lines = config_path.read_text().splitlines()
    key_line = next(line for line in lines if line.startswith("api_key"))

    assert key_line == r'api_key = "a\nb"'
