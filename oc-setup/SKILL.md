---
name: oc-setup
description: Primeira conversa. Descobre o que vigiar e quais consertos sao permitidos, e liga a vigilancia.
---

# Colocar o plantao de pe

Uma conversa curta, no chat, na primeira vez que o dono fala com voce. Nada de
formulario: uma pergunta por mensagem, e voce escreve o arquivo no fim.

Se `$HERMES_HOME/oncall/config.json` ja existe, isto nao e uma primeira
conversa -- e um ajuste. Leia o que ja esta la, mostre em duas linhas, e mude so
o que ele pedir.

## O que perguntar, nesta ordem

1. **O que vigiar.** Uma URL serve pra comecar. Aceite tambem host:porta, ou um
   repo do GitHub no formato `dono/nome` se ele quiser vigiar CI. Se ele mandar
   varios, tudo bem.
2. **O que ver quando quebrar.** Um caminho de arquivo de log, ou um comando que
   mostre o estado (`docker compose ps`, `systemctl status x`, `git log -3
   --oneline`). Opcional -- sem isso voce ainda diagnostica pelo que a sonda viu,
   so que com menos na mao. Diga isso, nao insista.
3. **O que voce tem permissao de fazer.** Esta e a pergunta importante e vale
   explicar por que: voce so vai rodar comandos que ele registrar aqui, com nome.
   Um exemplo concreto ajuda -- `reverter` = `cd /srv/app && git reset --hard
   HEAD~1 && docker compose up -d --build`. Se ele nao quiser nenhum, tudo bem:
   voce vira um plantao que so explica, e isso ja e util.

Nao pergunte mais nada. Fuso, janela de silencio, limiar -- tudo tem padrao e
nada disso vale uma pergunta na primeira conversa.

## Escrever a configuracao

```json
{
  "confirmations": 2,
  "targets": [
    {"name": "site", "kind": "http", "url": "https://exemplo.com/health",
     "expect_status": 200, "logs": ["/var/log/app.log"],
     "evidence_commands": ["docker compose ps"]},
    {"name": "ci", "kind": "github_actions", "repo": "dono/nome", "branch": "main"}
  ],
  "remedies": [
    {"name": "reverter", "description": "volta um commit e sobe de novo",
     "command": "cd /srv/app && git reset --hard HEAD~1 && docker compose up -d --build"}
  ]
}
```

Escreva em `$HERMES_HOME/oncall/config.json`. `kind` e um de `http`, `tcp`,
`github_actions`.

## Ligar a vigilancia

A sonda le a config sozinha a cada 60s -- nao ha nada a ligar nela. O que
precisa existir e o cron que faz VOCE olhar os incidentes:

```
hermes cron create "*/2 * * * *" \
  "Rode o oc-diagnose agora: se houver incidente em estado novo, diagnostique e avise. Se nao houver, responda exatamente quiet." \
  --name oc-diagnose --skill oc-diagnose
```

Sem `--deliver`, e isso e deliberado: `--deliver` repassa TODA resposta final,
inclusive as silenciosas, e este agente fica quieto quase o tempo todo. Quem
manda mensagem e o `notify.py`, so quando ha o que dizer.

Registre uma vez so. `hermes cron list` mostra o que ja existe -- se `oc-diagnose`
esta la, nao crie de novo.

## Fechar

Confirme em duas linhas o que voce vai vigiar e o que tem permissao de fazer, e
diga que a partir de agora ele so ouve sua voz se algo quebrar. Nao mande
mensagem de teste.
