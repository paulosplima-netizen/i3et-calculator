"""Contas locais e papeis (core/accounts.py) e a entrada na T01."""

from __future__ import annotations

import pytest

from core import accounts as ac


@pytest.fixture()
def conn(tmp_path):
    c = ac.connect(str(tmp_path / "a.sqlite"))
    yield c
    c.close()


def _master(conn, email="m@x.org"):
    return ac.bootstrap_master(conn, email, "senha-longa-1", "inst", "inst")


def test_senha_nunca_fica_em_texto_e_usa_sal(conn):
    ac.create_account(conn, "a@x.org", "senha-longa-1")
    ac.create_account(conn, "b@x.org", "senha-longa-1")
    h = [r[0] for r in conn.execute("SELECT PasswordHash FROM Account")]
    assert "senha-longa-1" not in h[0] and h[0] != h[1]          # mesmo texto, hashes distintos


def test_email_invalido_e_senha_curta_sao_recusados(conn):
    with pytest.raises(ac.AccountError):
        ac.create_account(conn, "sem-arroba", "senha-longa-1")
    with pytest.raises(ac.AccountError):
        ac.create_account(conn, "a@x.org", "curta")


def test_conta_nova_e_user_e_email_e_unico_sem_distinguir_caixa(conn):
    assert ac.create_account(conn, " A@X.org ", "senha-longa-1") == "a@x.org"
    assert ac.role_of(conn, "a@x.org") == ac.USER
    with pytest.raises(ac.AccountError):
        ac.create_account(conn, "a@X.ORG", "outra-senha-1")


def test_entrada_certa_e_errada(conn):
    ac.create_account(conn, "a@x.org", "senha-longa-1")
    assert ac.authenticate(conn, "A@x.org", "senha-longa-1") == ac.USER
    for email, pwd in (("a@x.org", "errada-errada"), ("nao@x.org", "senha-longa-1")):
        with pytest.raises(ac.AccountError, match="Wrong e-mail or password"):
            ac.authenticate(conn, email, pwd)


def test_bloqueio_apos_cinco_erros_e_libera_depois(conn):
    ac.create_account(conn, "a@x.org", "senha-longa-1")
    for _ in range(ac.MAX_FAILURES):
        with pytest.raises(ac.AccountError):
            ac.authenticate(conn, "a@x.org", "x", now=1000.0)
    with pytest.raises(ac.AccountError, match="Too many attempts"):
        ac.authenticate(conn, "a@x.org", "senha-longa-1", now=1001.0)    # certa, mas bloqueada
    assert ac.authenticate(conn, "a@x.org", "senha-longa-1",
                           now=1000.0 + ac.LOCK_SECONDS + 1) == ac.USER


def test_primeiro_master_exige_a_senha_de_instalacao(conn):
    with pytest.raises(ac.AccountError, match="Wrong installation"):
        ac.bootstrap_master(conn, "m@x.org", "senha-longa-1", "inst", "outra")
    with pytest.raises(ac.AccountError, match="No installation"):
        ac.bootstrap_master(conn, "m@x.org", "senha-longa-1", None, "inst")
    assert _master(conn) == "m@x.org" and ac.role_of(conn, "m@x.org") == ac.MASTER
    with pytest.raises(ac.AccountError, match="already exists"):     # so uma vez
        ac.bootstrap_master(conn, "n@x.org", "senha-longa-1", "inst", "inst")


def test_so_o_master_muda_papeis_e_o_ultimo_nao_sai(conn):
    _master(conn)
    ac.create_account(conn, "u@x.org", "senha-longa-1")
    with pytest.raises(ac.AccountError, match="Only a master"):
        ac.set_role(conn, "u@x.org", "u@x.org", ac.MASTER)
    with pytest.raises(ac.AccountError, match="last master"):
        ac.set_role(conn, "m@x.org", "m@x.org", ac.USER)
    ac.set_role(conn, "m@x.org", "u@x.org", ac.MASTER)
    assert ac.count_masters(conn) == 2
    ac.set_role(conn, "m@x.org", "m@x.org", ac.USER)                # agora ha outro Master
    assert ac.role_of(conn, "m@x.org") == ac.USER


def test_transferir_o_papel_troca_os_dois(conn):
    _master(conn)
    ac.create_account(conn, "u@x.org", "senha-longa-1")
    ac.transfer_master(conn, "m@x.org", "u@x.org")
    assert ac.role_of(conn, "u@x.org") == ac.MASTER and ac.role_of(conn, "m@x.org") == ac.USER
    assert ac.count_masters(conn) == 1
    with pytest.raises(ac.AccountError):
        ac.transfer_master(conn, "m@x.org", "u@x.org")                # m ja nao e Master


def test_trocar_a_senha(conn):
    ac.create_account(conn, "a@x.org", "senha-longa-1")
    ac.change_password(conn, "a@x.org", "nova-senha-22")
    assert ac.authenticate(conn, "a@x.org", "nova-senha-22") == ac.USER
    with pytest.raises(ac.AccountError):
        ac.authenticate(conn, "a@x.org", "senha-longa-1")
