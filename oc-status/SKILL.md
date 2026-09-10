---
name: oc-status
description: Responde "como esta tudo?" agora, e aceita o pedido de silencio durante uma manutencao.
---

# Responder quando perguntam

O dono perguntou. Leia `$HERMES_HOME/oncall/state.json` e os incidentes
recentes, e responda em uma ou duas linhas.

**Leia `language` do `oncall/config.json` antes de escrever.** `en-US` ou
`pt-BR`. Se nao estiver definido, responda no idioma em que ele falou.

**Nao sonde nada.** A sonda roda a cada 60 segundos; o estado em disco tem no
maximo um minuto e isso e novo o suficiente pra qualquer pergunta feita por
mensagem. Sondar aqui gastaria um turno pra descobrir o que voce ja sabe.

Tudo no ar:

```
tudo no ar. site ok, ci verde. ultimo susto foi terca, 6 min de 502.
```

Algo fora:

```
site fora ha 12 min, ja te avisei as 03:14. ci verde.
```

Se ele perguntar sobre um incidente especifico, leia o arquivo e conte o que
aconteceu -- inclusive se voce errou o diagnostico. Um plantao que esconde os
proprios erros nao merece acesso de producao.

Se a pergunta for sobre a SEMANA e nao sobre agora -- "teve problema?", "ta
instavel?" -- isso e `oc-health`, nao aqui.

# "Fica quieto, vou fazer deploy"

Quando ele pedir silencio por um tempo, grave `snooze_until` no
`oncall/config.json` com o instante em que acaba, em ISO 8601 com fuso:

```json
{"snooze_until": "2026-09-10T15:30:00+00:00"}
```

Confirme em uma linha, dizendo **ate quando** e o que continua acontecendo:

```
quieto ate 12:30. sigo vigiando e registrando -- so nao te interrompo.
```

Duas coisas que voce nunca faz aqui: soneca sem prazo (se ele nao disser quanto
tempo, pergunte -- um agente silenciado pra sempre e um agente desinstalado sem
saber), e soneca que apaga incidente. A sonda continua abrindo o registro; o
que espera e so a mensagem, e o cron de rede de seguranca entrega quando passar.

Se ele pedir pra voltar antes -- "pode falar", "terminei" -- apague o
`snooze_until` e confirme.
