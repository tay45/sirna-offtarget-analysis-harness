import socket


def test_imports_do_not_open_network(monkeypatch) -> None:
    def fail_connect(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access during import")

    monkeypatch.setattr(socket.socket, "connect", fail_connect)
    __import__("sirna_offtarget")
