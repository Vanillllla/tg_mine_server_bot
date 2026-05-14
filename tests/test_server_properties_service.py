from pathlib import Path

from app.models.server import ServerInstance
from app.services.server_properties import ServerPropertiesService


def make_server(tmp_path: Path) -> ServerInstance:
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    return ServerInstance(
        id="test_server",
        display_name="Test Server",
        server_dir=str(server_dir),
        jar_file="server.jar",
    )


def test_updates_properties_values_and_preserves_comments(tmp_path: Path) -> None:
    server = make_server(tmp_path)
    path = Path(server.server_dir) / "server.properties"
    path.write_text("# header\nmotd=Old\nmax-players=10\n", encoding="utf-8")

    result = ServerPropertiesService().update_values(
        server,
        {"motd": "New", "max-players": 20, "online-mode": True},
    )

    assert result.values["motd"] == "New"
    assert result.values["max-players"] == "20"
    assert result.values["online-mode"] == "true"
    assert result.raw.startswith("# header")
    assert list(Path(server.server_dir).glob("server.properties.*.bak"))


def test_rejects_invalid_numeric_property(tmp_path: Path) -> None:
    server = make_server(tmp_path)

    try:
        ServerPropertiesService().update_values(server, {"server-port": 70000})
    except ValueError as exc:
        assert str(exc) == "server-port_must_be_between_1_and_65535"
    else:
        raise AssertionError("invalid port was accepted")
