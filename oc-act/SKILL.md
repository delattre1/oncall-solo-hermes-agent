---
name: oc-act
description: Executa um remedio que o dono aprovou. So o que ele registrou, so o que voce propos, so com sim explicito.
---

# Agir depois do sim

## As tres condicoes

Todas as tres, sempre:

1. Existe um incidente em `"state": "avisado"` com `proposed_remedy` preenchido.
2. A ultima mensagem do dono e uma **aprovacao clara** daquilo. "ok", "pode",
   "reverte", "manda", "isso" aprovam. "por que?", "hmm", "e se", uma pergunta,
   ou silencio **nao aprovam**. Na duvida, pergunte -- perguntar custa uma
   mensagem, agir errado custa a producao dele.
3. O remedio esta em `remedies` no `config.json`, e voce roda **o comando que
   esta escrito la**, sem editar, sem acrescentar, sem adaptar.

Se o dono pedir algo que nao esta na lista, diga que voce so roda o que ele
registrou e mostre o comando que ele mesmo rodaria. Isso nao e limitacao a ser
contornada -- e o que torna seguro te dar acesso a uma maquina de producao.

## Rodar

Rode o comando. Guarde saida e codigo de saida no incidente.

Espere ate 90 segundos e deixe a sonda confirmar: se o alvo voltar, o proximo
tick fecha o incidente sozinho. Nao declare vitoria pela saida do comando --
declare pela sonda.

## Contar o que houve

Uma linha, com o resultado real:

```
revertido, healthcheck verde as 03:19.
```

Se nao resolveu, diga isso com a mesma clareza e nao tente um segundo remedio
por conta propria. Marque o incidente como `"state": "remediado"` ou
`"state": "remedio-falhou"`.
