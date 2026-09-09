---
name: oc-shared
description: Scripts compartilhados do plantao: a sonda e o canal de mensagem.
---

# Ferramentas do plantao

Este diretorio nao e um procedimento -- e a caixa de ferramentas que os outros
sheets deste agente chamam. Nada aqui deve ser executado "porque o skill foi
carregado"; cada script tem um chamador nomeado.

## `scripts/probe.py`
A sonda. Roda a cada 60s sob o s6 pela copia de `/opt/plow`, sem modelo. Voce
quase nunca a chama a mao -- so se o dono pedir uma verificacao imediata logo
depois de mudar a configuracao.

## `scripts/notify.py`
A unica forma deste agente falar sem ser perguntado. Le o corpo do stdin ou de
`--file`. Corpo vazio sai 0 sem postar: silencio e um resultado valido.
Chamado por `oc-diagnose`, e por mais ninguem.

## O caminho importa

Chame sempre por `$HERMES_HOME/skills/oc-shared/scripts/...`.

A imagem entrega os sheets em `/opt/hermes/skills`, o runtime os reconcilia
para `$HERMES_HOME/skills`, e e o segundo que um agente em execucao encontra.
Um sheet que nomeia o caminho da imagem funciona no dia do build e falha depois.

A copia root-owned em `/opt/plow/` existe para o que roda sozinho sob o
supervisor. Ela nao e sua para chamar: o que voce roda dentro de um turno vem da
casa; o que roda sem ninguem olhando vem de `/opt/plow`, e essa separacao e o
que impede uma unica edicao por prompt-injection de virar codigo agendado.
