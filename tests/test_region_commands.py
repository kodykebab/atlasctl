from __future__ import annotations

from atlasctl.config import load_config
from tests.conftest import run_cli


def add_region(runner, name: str, tenant_id: int, *, default: bool = False):
    args = [
        "region",
        "add",
        name,
        "--base-url",
        f"https://{name}.example.com",
        "--api-key",
        "k",
        "--api-secret",
        "s",
        "--tenant-id",
        str(tenant_id),
    ]
    if default:
        args.append("--default")
    return run_cli(runner, *args)


def test_add_creates_a_region_and_makes_it_the_default(config_path, runner):
    result = add_region(runner, "mumbai", 7)

    assert result.exit_code == 0, result.output
    config = load_config()
    assert config.default == "mumbai"
    assert config.regions["mumbai"].tenant_id == 7


def test_a_second_region_does_not_become_default_without_the_flag(config_path, runner):
    add_region(runner, "a", 1)
    add_region(runner, "b", 2)

    assert load_config().default == "a"


def test_default_flag_switches_the_default(config_path, runner):
    add_region(runner, "a", 1)
    add_region(runner, "b", 2, default=True)

    assert load_config().default == "b"


def test_use_switches_the_default(config_path, runner):
    add_region(runner, "a", 1)
    add_region(runner, "b", 2)

    result = run_cli(runner, "region", "use", "a")

    assert result.exit_code == 0
    assert load_config().default == "a"


def test_remove_clears_the_default_when_it_was_removed(configured, runner):
    result = run_cli(runner, "region", "remove", "test")

    assert result.exit_code == 0
    config = load_config()
    assert "test" not in config.regions
    assert config.default is None


def test_list_marks_the_default(configured, runner):
    result = run_cli(runner, "region", "list")
    assert "* test" in result.output


def test_list_with_no_regions(config_path, runner):
    result = run_cli(runner, "region", "list")
    assert "no regions configured" in result.output
