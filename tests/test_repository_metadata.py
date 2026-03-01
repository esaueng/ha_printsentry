from pathlib import Path


def test_repository_yaml_points_to_real_repo_and_maintainer() -> None:
    text = Path("repository.yaml").read_text(encoding="utf-8")
    assert 'name: "ha_printsentry Add-ons"' in text
    assert 'url: "https://github.com/esaueng/ha_printsentry"' in text
    assert 'maintainer: "esaueng"' in text
