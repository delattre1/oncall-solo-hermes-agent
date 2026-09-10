---
name: oc-setup
description: Primeira conversa. Idioma, o que vigiar, o que olhar quando quebrar, e o que voce tem permissao de rodar.
---

# Colocar o plantao de pe

Uma conversa curta, no chat, na primeira vez que o dono fala com voce. Nada de
formulario: **uma pergunta por mensagem**, e voce escreve o arquivo no fim.

Se `$HERMES_HOME/oncall/config.json` ja existe, isto nao e uma primeira conversa
-- e um ajuste. Leia o que ja esta la, mostre em duas linhas, e mude so o que ele
pedir.

## As perguntas, nesta ordem

### 1. Idioma

Primeira, porque decide como o resto da conversa acontece. Pergunte nas duas
linguas, uma linha:

```
en or pt-br? / ingles ou portugues?
```

Grave em `language` (`en-US` ou `pt-BR`) e **siga nesse idioma a partir da
proxima mensagem**. Evidencia e comando nunca sao traduzidos.

### 2. O que vigiar

Uma URL serve pra comecar. Aceite tambem `host:porta`, ou `dono/repo` do GitHub
pra vigiar CI. Varios, tudo bem.

### 3. O que olhar quando quebrar

**Esta e a pergunta que separa "esta fora" de "esta fora por causa disto"**, e e
onde ele conecta o agente ao processo dele. Peca um caminho de log ou um comando
que mostre o estado, e de um exemplo que caiba na stack dele:

| se ele roda | o que sugerir |
|---|---|
| docker compose | `docker compose ps`, `docker compose logs --tail 50 <servico>` |
| systemd | `systemctl status <unidade>`, `journalctl -u <unidade> -n 50` |
| pm2 / node | `pm2 list`, `pm2 logs <app> --lines 50 --nostream` |
| kubernetes | `kubectl get pods -n <ns>`, `kubectl logs deploy/<app> --tail 50` |
| qualquer um | `git log -3 --oneline`, `df -h`, `free -m` |

Opcional -- sem isso voce ainda diagnostica pelo que a sonda viu, so que com
menos na mao. Diga isso e nao insista.

Dois avisos que valem dizer em voz alta, porque protegem ele:

- **Comandos de leitura apenas.** Isto e evidencia, nao conserto. Nada que
  reinicie, apague ou publique entra aqui.
- **O container precisa alcancar.** Se o servico dele roda na maquina host e nao
  no container, a URL e `http://host.docker.internal:PORTA`, e um comando como
  `docker compose ps` so funciona se aquele caminho existir de dentro. Se nao
  tiver certeza, e melhor ele mandar um comando simples primeiro e ver.

### 4. O que voce tem permissao de rodar

A pergunta mais importante, e vale explicar por que antes de fazer: **voce so
roda comandos que ele registrar aqui, com nome**. Voce nunca formula um comando
proprio, nem em emergencia.

Um exemplo concreto ajuda:

```
"reverter" = cd /srv/app && git reset --hard HEAD~1 && docker compose up -d --build
```

Se ele nao quiser nenhum, tudo bem -- **voce vira um plantao que so explica, e
isso ja e util**. E o padrao mais seguro pra quem acabou de instalar.

### 5. Horario de silencio (opcional, so se ele levantar)

Se ele mencionar nao querer ser acordado, ofereca uma faixa e um alvo que fura
ela. Nao pergunte isso do nada na primeira conversa.

Nao pergunte mais nada. Fuso, limiar de confirmacao, cadencia -- tudo tem padrao
e nada disso vale uma pergunta agora.

## Escrever a configuracao

```json
{
  "language": "pt-BR",
  "confirmations": 2,
  "quiet_hours": {"from": 23, "to": 7, "except_targets": ["checkout-api"]},
  "targets": [
    {"name": "checkout-api", "kind": "http", "url": "https://exemplo.com/health",
     "expect_status": 200,
     "logs": ["/var/log/app.log"],
     "evidence_commands": ["docker compose ps", "git log -3 --oneline"]},
    {"name": "ci", "kind": "github_actions", "repo": "dono/nome", "branch": "main"}
  ],
  "remedies": [
    {"name": "reverter", "description": "volta um commit e sobe de novo",
     "command": "cd /srv/app && git reset --hard HEAD~1 && docker compose up -d --build"}
  ]
}
```

Em `$HERMES_HOME/oncall/config.json`. `kind` e um de `http`, `tcp`,
`github_actions`. `quiet_hours` e `remedies` podem ficar de fora.

## Ligar a vigilancia

A sonda le a config sozinha a cada 60s e, quando abre um incidente, ela mesma te
acorda na hora. Nao ha nada a ligar nela.

O que precisa existir e a REDE DE SEGURANCA -- um cron esparso, pro caso de a
sonda nao conseguir acordar ninguem:

```
hermes cron create "*/30 * * * *" \
  "Rode o oc-diagnose agora: se houver incidente em estado novo, diagnostique e avise. Se nao houver, responda exatamente quiet." \
  --name oc-diagnose --skill oc-diagnose
```

Meia hora, nao dois minutos, e isso importa: **quem acorda o agente e o evento,
nao o relogio**. Um cron curto acorda o modelo o dia inteiro pra responder
`quiet`.

Sem `--deliver`, tambem deliberado: ele repassa TODA resposta final, inclusive as
silenciosas. Quem manda mensagem e o `notify.py`, so quando ha o que dizer.

`hermes cron list` antes; se ja existe, nao crie de novo.

## Fechar

Confirme em duas ou tres linhas, no idioma escolhido: o que voce vai vigiar, o
que tem permissao de fazer, e o que ele pode te perguntar depois --
"como esta tudo?" pro agora, "teve problema essa semana?" pra tendencia, e
"fica quieto 1h" durante um deploy.

Termine dizendo que a partir de agora ele so ouve sua voz se algo quebrar. **Nao
mande mensagem de teste.**
