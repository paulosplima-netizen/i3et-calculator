# Superados

Arquivos que saíram do aplicativo mas ficam aqui como histórico. Não fazem parte do menu nem do `st.navigation`.

| Arquivo | Substituído por | Desde |
|---|---|---|
| `pages/1_Home.py` | `pages/T01_Home.py` | 0.10.0 (decisão do autor em 18/11/2026) |
| `pages/4_Scenario.py` | `pages/T03_Project_configuration.py` e `pages/T41_Validate_and_freeze.py` | idem |
| `pages/7_Export.py` | `pages/T08_Export.py` | idem |

Os testes de `tests/test_app.py` que abrem essas páginas seguem apontando para cá. Se um dia forem apagadas, apagar também esses testes.
