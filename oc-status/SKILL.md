---
name: oc-status
description: Responde "como esta tudo?" a partir do estado em disco, sem sondar nada.
---

# Responder quando perguntam

O dono perguntou. Leia `$HERMES_HOME/oncall/state.json` e os incidentes
recentes, e responda em uma ou duas linhas.

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
