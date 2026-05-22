from pathlib import Path

from app.models.server import LaunchMode, ServerInstance
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


def test_jar_launch_args_use_jar_flag(tmp_path: Path) -> None:
    server = make_server(tmp_path)

    args = MinecraftServerManager._build_launch_args(server)

    assert "-jar" in args
    assert args[-2] == str(Path(server.server_dir) / "server.jar")
    assert args[-1] == "nogui"


def test_forge_args_launch_args_do_not_use_jar_flag(tmp_path: Path) -> None:
    server_dir = tmp_path / "server"
    forge_args = server_dir / "libraries" / "net" / "minecraftforge" / "forge" / "1.20.1-47.2.0" / "win_args.txt"
    forge_args.parent.mkdir(parents=True)
    forge_args.write_text("--launchTarget forge_server\n", encoding="utf-8")
    (server_dir / "user_jvm_args.txt").write_text("# user args\n", encoding="utf-8")
    server = ServerInstance(
        id="forge_server",
        display_name="Forge Server",
        server_dir=str(server_dir),
        jar_file="libraries/net/minecraftforge/forge/1.20.1-47.2.0/win_args.txt",
        launch_mode=LaunchMode.FORGE_ARGS,
    )

    args = MinecraftServerManager._build_launch_args(server)

    assert "-jar" not in args
    assert "@user_jvm_args.txt" in args
    assert "@libraries/net/minecraftforge/forge/1.20.1-47.2.0/win_args.txt" in args
    assert args[-1] == "nogui"


def test_launch_validation_rejects_txt_in_jar_mode(tmp_path: Path) -> None:
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    (server_dir / "server.txt").write_text("not a jar", encoding="utf-8")
    (server_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    server = ServerInstance(
        id="bad_server",
        display_name="Bad Server",
        server_dir=str(server_dir),
        jar_file="server.txt",
    )

    try:
        MinecraftServerManager._validate_launch(server)
    except ValueError as exc:
        assert str(exc) == "jar_file_must_be_jar"
    else:
        raise AssertionError("txt launch target was accepted in jar mode")


def test_launch_validation_accepts_forge_args_mode(tmp_path: Path) -> None:
    server_dir = tmp_path / "server"
    forge_args = server_dir / "libraries" / "net" / "minecraftforge" / "forge" / "1.20.1-47.2.0" / "unix_args.txt"
    forge_args.parent.mkdir(parents=True)
    forge_args.write_text("--launchTarget forge_server\n", encoding="utf-8")
    (server_dir / "user_jvm_args.txt").write_text("# user args\n", encoding="utf-8")
    (server_dir / "eula.txt").write_text("eula=true\n", encoding="utf-8")
    server = ServerInstance(
        id="forge_server",
        display_name="Forge Server",
        server_dir=str(server_dir),
        jar_file="libraries/net/minecraftforge/forge/1.20.1-47.2.0/unix_args.txt",
        launch_mode=LaunchMode.FORGE_ARGS,
    )

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


def test_tps_is_parsed_from_server_logs() -> None:
    line = "[12:00:00] [Server thread/INFO]: TPS from last 1m, 5m, 15m: *19.97, *20.0, *20.0"

    assert MinecraftServerManager._tps_from_log_line(line) == 19.97
    assert MinecraftServerManager._tps_from_log_line("Unknown command") is None
