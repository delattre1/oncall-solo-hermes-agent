---
name: oc-health
description: Responde "como voce esta indo?" com tendencia — uptime, tempo ate detectar, alvos instaveis, o que ficou sem resposta.
---

# Como o plantao esta indo

"Algo caiu?" o agente responde sozinho, na hora. **"Esta tudo bem?" e outra
pergunta**: e sobre tendencia, e ninguem manda mensagem sobre tendencia as 3h da
manha. Este sheet existe pra quando o dono pergunta.

Gatilhos: "como esta indo?", "tudo bem por ai?", "teve problema essa semana?",
"o que caiu ultimamente?", "isso ta instavel?", "vale a pena olhar alguma coisa?".

## Os numeros

```
python3 "$HERMES_HOME/skills/oc-shared/scripts/health.py" --days 7
```

**A primeira chave da saida e `language`** — responda nela, sempre. `en-US` ou
`pt-BR`; se vier "(nao configurado)", siga o idioma em que o dono perguntou.
Numeros, nomes de alvo e saida de comando nao mudam com o idioma.

Sai JSON, calculado dos incidentes em disco. Sem modelo, sem sondar nada, sem
estimativa: **chave que nao aparece e dado que nao existe**, e nesse caso voce
diz que nao tem — nunca preenche com um numero plausivel.

O que vem, e o que cada coisa quer dizer:

- `language` — em que idioma escrever a resposta.
- `now` — o estado agora, por alvo.
- `incidents` — quantos na janela.
- `time_to_detect_seconds` — quanto a sonda levou pra perceber. Sai das
  confirmacoes gravadas x o tick de 60s, nao de palpite.
- `outage_minutes` — so incidentes que **fecharam**. Um ainda aberto entra em
  `still_open`, separado, porque somar "ate agora" faria a media mudar sozinha a
  cada leitura.
- `per_target` — incidentes, quantos se resolveram sozinhos, quantos remediados.
- `flapping` — alvo com 3+ incidentes na janela. **E um problema diferente** de
  um alvo que caiu uma vez, e e o que mais gasta a paciencia de quem recebe as
  mensagens. Se aparecer, e a primeira coisa que voce fala.
- `notified_never_answered` — voce avisou, ninguem respondeu, e continua fora.
  Nao e falha sua; e informacao sobre a operacao dele, e vale dizer.

## Como responder

Duas ou tres linhas, no idioma configurado, sem cabecalho e sem marcador. Lidere
pelo que exige acao; termine pelo que e so contexto.

Tudo calmo:

```
semana tranquila: 1 incidente, o checkout voltou sozinho em 4 min.
detecto em ~2 min na mediana. nada instavel.
```

Ha um padrao:

```
o checkout-api caiu 4x essa semana -- isso e instabilidade, nao azar.
sempre volta sozinho em poucos minutos, entao ninguem te acorda, mas
o padrao ta la. vale olhar o que reinicia ele.
```

Ha coisa sem resposta:

```
te avisei do worker as 02:14 e ele continua fora -- 6h ate agora.
propus reverter e nao teve resposta. quer que eu reverta?
```

Sem historico:

```
sem incidente nenhum nos ultimos 7 dias. vigiando checkout-api e o ci.
```

Nao encha de numero. O JSON tem uma dezena de campos; a mensagem cita os dois ou
tres que mudam o que ele faria. E **nunca invente causa** a partir da tendencia:
"caiu 4x" e um fato; "provavelmente e memoria" so se a evidencia dos incidentes
disser isso.
