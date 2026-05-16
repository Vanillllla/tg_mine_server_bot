from pathlib import Path

from app.models.server import ServerInstance
from app.services.minecraft_manager import MinecraftServerManager


def make_server(tmp_path: Path, eula_accept: bool = False) -> ServerInstance:
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    (server_dir / "server.jar").write_bytes(b"jar")
    return ServerInstance(
        id="test_server",
        display_name="Test Server",
        server_dir=str(server_dir),
        jar_file="server.jar",
        eula_accept=eula_accept,
    )


def test_launch_validation_uses_eula_file_not_servers_config_flag(tmp_path: Path) -> None:
    server = make_server(tmp_path, eula_accept=False)
    Path(server.server_dir, "eula.txt").write_text("# comment\neula=true\n", encoding="utf-8")

    MinecraftServerManager._validate_launch(server)


def test_launch_validation_rejects_missing_or_false_eula_file(tmp_path: Path) -> None:
    server = make_server(tmp_path, eula_accept=True)

    try:
        MinecraftServerManager._validate_launch(server)
    except ValueError as exc:
        assert str(exc) == "eula_must_be_accepted_before_start"
    else:
        raise AssertionError("missing eula.txt was accepted")

    Path(server.server_dir, "eula.txt").write_text("eula=false\n", encoding="utf-8")

    try:
        MinecraftServerManager._validate_launch(server)
    except ValueError as exc:
        assert str(exc) == "eula_must_be_accepted_before_start"
    else:
        raise AssertionError("eula=false was accepted")


def test_player_events_are_parsed_from_minecraft_logs() -> None:
    joined = "[12:00:00] [Server thread/INFO]: Steve joined the game"
    left = "[12:10:00] [Server thread/INFO]: Steve left the game"

    assert MinecraftServerManager._player_event_from_log_line(joined) == ("join", "Steve")
    assert MinecraftServerManager._player_event_from_log_line(left) == ("leave", "Steve")
    assert MinecraftServerManager._player_event_from_log_line("Done (1.0s)!") is None
