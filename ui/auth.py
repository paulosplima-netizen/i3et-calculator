"""Entrada do usuario (e-mail e senha) e papel Master na interface.

A regra esta em `core/accounts.py`; aqui ficam so a sessao e os controles da T01.
`master_ok` na sessao e verdadeiro quando quem entrou tem o papel Master: as telas de
dados de mercado (T39, T40, T42) e a T48 consultam `is_master()`.
"""

from __future__ import annotations

import contextlib
import os

import streamlit as st

from core import accounts

from . import state

EMAIL_KEY = "user_email"
ROLE_KEY = "user_role"
MASTER_KEY = "master_ok"


def accounts_path() -> str:
    return os.environ.get("I3ET_ACCOUNTS_DB") or os.path.join(state.REPO, "local_accounts.sqlite")


@contextlib.contextmanager
def connect():
    conn = accounts.connect(accounts_path())
    try:
        yield conn
    finally:
        conn.close()


def current_email() -> str | None:
    return st.session_state.get(EMAIL_KEY)


def is_master() -> bool:
    return bool(st.session_state.get(MASTER_KEY))


def _enter(email: str, role: str) -> None:
    st.session_state[EMAIL_KEY] = email
    st.session_state[ROLE_KEY] = role
    st.session_state[MASTER_KEY] = role == accounts.MASTER


def sign_out() -> None:
    for k in (EMAIL_KEY, ROLE_KEY, MASTER_KEY):
        st.session_state.pop(k, None)


def require_master_message(title: str) -> None:
    st.info(f"{title} is available to the master user only. Sign in with a master account "
            "on the Home page (T01).")


def _signed_in_panel() -> None:
    email, role = current_email(), st.session_state.get(ROLE_KEY)
    c1, c2 = st.columns([4, 1])
    c1.markdown(f"Signed in as **{email}** · {role}")
    if c2.button("Sign out", key="sign_out"):
        sign_out()
        st.rerun()
    if role == accounts.MASTER:
        _manage_users(email)


def _manage_users(me: str) -> None:
    with st.expander("Manage users (master)"):
        with connect() as conn:
            rows = accounts.list_accounts(conn)
            st.dataframe([{"E-mail": r["Email"], "Role": r["Role"]} for r in rows],
                         hide_index=True, use_container_width=True)
            others = [r["Email"] for r in rows if r["Email"] != me]
            if not others:
                st.caption("No other accounts yet. Ask people to create an account first.")
                return
            target = st.selectbox("Account", others, key="manage_target")
            cur = accounts.role_of(conn, target)
            a, b, c = st.columns(3)
            msg = None
            try:
                if cur == accounts.USER and a.button("Make master", key="make_master"):
                    accounts.set_role(conn, me, target, accounts.MASTER)
                    msg = f"{target} is now a master."
                if cur == accounts.MASTER and b.button("Make user", key="make_user"):
                    accounts.set_role(conn, me, target, accounts.USER)
                    msg = f"{target} is now a regular user."
                if c.button("Transfer my master role", key="transfer_master",
                            help="You become a regular user; the selected account becomes "
                                 "the master."):
                    accounts.transfer_master(conn, me, target)
                    _enter(me, accounts.USER)
                    msg = f"Master role transferred to {target}."
            except accounts.AccountError as e:
                st.error(str(e))
            if msg:
                st.success(msg)
                if not is_master():
                    st.rerun()


def _signed_out_panel() -> None:
    with connect() as conn:
        n_master = accounts.count_masters(conn)
        tabs = ["Sign in", "Create account"]
        secret = state.master_password()
        if not n_master:
            tabs.append("First master")
        views = st.tabs(tabs)
        with views[0]:
            with st.form("sign_in_form"):
                email = st.text_input("E-mail", key="si_email")
                pwd = st.text_input("Password", type="password", key="si_pwd")
                ok = st.form_submit_button("Sign in")
            if ok:
                try:
                    role = accounts.authenticate(conn, email, pwd)
                except accounts.AccountError as e:
                    st.error(str(e))
                else:
                    _enter(accounts.normalize_email(email), role)
                    st.rerun()
        with views[1]:
            with st.form("create_account_form"):
                email = st.text_input("E-mail", key="ca_email")
                pwd = st.text_input("Password", type="password", key="ca_pwd",
                                    help=f"At least {accounts.MIN_PASSWORD} characters.")
                ok = st.form_submit_button("Create account")
            if ok:
                try:
                    e = accounts.create_account(conn, email, pwd)
                except accounts.AccountError as err:
                    st.error(str(err))
                else:
                    _enter(e, accounts.USER)
                    st.rerun()
        if not n_master:
            with views[2]:
                if not secret:
                    st.info("No master exists yet and no installation master password is "
                            "configured. Set `I3ET_MASTER_PASSWORD` (or `master_password` in "
                            "`.streamlit/secrets.toml`) and reload to create the first master.")
                else:
                    st.caption("Creates the first master account. It asks for the "
                               "installation master password once; after that the master "
                               "manages who else is master.")
                    with st.form("first_master_form"):
                        email = st.text_input("E-mail", key="fm_email")
                        pwd = st.text_input("New password", type="password", key="fm_pwd")
                        inst = st.text_input("Installation master password", type="password",
                                             key="fm_inst")
                        ok = st.form_submit_button("Create master account")
                    if ok:
                        try:
                            e = accounts.bootstrap_master(conn, email, pwd, secret, inst)
                        except accounts.AccountError as err:
                            st.error(str(err))
                        else:
                            _enter(e, accounts.MASTER)
                            st.rerun()


def panel() -> None:
    """Bloco de entrada da T01."""
    if current_email():
        _signed_in_panel()
    else:
        with st.expander("Sign in · master access", expanded=False):
            _signed_out_panel()
