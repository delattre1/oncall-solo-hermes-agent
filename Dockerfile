# Oncall Solo -- imagem do agente, derivada da base cloud da Plow.
#
# Sem conteudo de agente proprio na base: a persona e os skills copiados abaixo
# sao os arquivos versionados que este repo possui. O contexto e a raiz do
# repo, entao essas copias sao o produto: `docker build .`
#
# A tag e um `base-<sha>` imutavel nomeando um commit do repo-fonte da base,
# plow-pbc/plow-hermes-agent, fixado tambem por digest. Ela nunca e movida:
# toda VM inquilina herda exatamente este filesystem enquanto segura a
# credencial Plow daquele dono, e uma tag movel trocaria codigo por baixo deles.
# A base e publicada SO pra linux/amd64. Sem declarar isso, o build num Mac
# Apple Silicon imprime um aviso de plataforma incompativel -- inofensivo (o
# Docker Desktop emula) mas ele aparece no PRIMEIRO build de todo instalador em
# Mac ARM, que e exatamente o momento em que a pessoa decide se algo quebrou.
#
# Um ARG e nao uma constante: `FROM --platform=linux/amd64` dispara o lint
# FromPlatformFlagConstDisallowed, que existe porque fixar plataforma no FROM
# costuma ser engano. Aqui nao e -- e a unica que a base tem -- entao o ARG diz
# isso e ainda deixa alguem sobrescrever (`--build-arg BASE_PLATFORM=...`) no dia
# em que a Plow publicar arm64.
ARG BASE_PLATFORM=linux/amd64
FROM --platform=${BASE_PLATFORM} public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-ef0019372ff8bca593611b31ebd2e08f9f1458ff@sha256:a8a2f97ad78b8192d80a984dce81d3bf5a9a883d18cb7b677704913a09b56aee

# Substitui o SOUL.md da propria base; o primeiro boot reafirma a posse root
# nesse arquivo, e e a isso que o chmod no fim responde.
COPY runtime/SOUL.md /var/lib/hermes/SOUL.md
COPY LICENSE NOTICE /usr/share/doc/oncall-solo/

# Entregues em /opt/hermes/skills, fora de toda casa, pra que uma casa
# bind-montada ainda receba e uma atualizacao de imagem ainda alcance um skill
# nao customizado -- as duas coisas via reconcile do runtime da base.
COPY oc-setup/            /opt/hermes/skills/oc-setup/
COPY oc-diagnose/         /opt/hermes/skills/oc-diagnose/
COPY oc-act/              /opt/hermes/skills/oc-act/
COPY oc-status/           /opt/hermes/skills/oc-status/
COPY oc-health/           /opt/hermes/skills/oc-health/
COPY oc-shared/           /opt/hermes/skills/oc-shared/

# Normaliza os modos que o checkout carregou, preservando o bit de executavel:
# varios SKILL.md invocam um script por caminho nu, entao um 0644 geral os faz
# falhar com Permission denied. A posse fica como root.
# -mindepth 1: a raiz de skills e da base, root-owned e sticky; recursar sobre
# ela resetaria esse modo e deixaria o diretorio nao-gravavel pro proprio
# install de skills do gateway, que entao nao varre nada.
RUN find /opt/hermes/skills -mindepth 1 -type d -exec chmod 0755 {} + \
 && find /opt/hermes/skills -mindepth 1 -type f ! -perm -u+x -exec chmod 0644 {} + \
 && find /opt/hermes/skills -mindepth 1 -type f -perm -u+x -exec chmod 0755 {} + \
 && chmod 0644 /var/lib/hermes/SOUL.md

# A copia root-owned do que o supervisor roda sozinho, fora do alcance do agente.
#
# O que roda sem ninguem olhando nao pode ser um arquivo que um turno reescreve.
# Tudo sob $HERMES_HOME/skills pertence ao uid 10000 num container em execucao
# -- o runtime faz chown do que semeia a cada boot -- entao agendar a copia que
# vive la transformaria uma unica edicao por prompt-injection em codigo que roda
# sozinho, pra sempre, segurando a credencial. Esta copia e root-owned em
# diretorio root-owned: o agente le e nao muda.
#
# A copia na casa fica exatamente como esta -- e o que o agente le, edita e roda
# a mao durante o setup. Só o AGENDAMENTO aponta pra ca.
COPY oc-shared/ /opt/plow/oc-shared/
RUN chown -R root:root /opt/plow \
 && find /opt/plow -type d -exec chmod 0755 {} + \
 && find /opt/plow -type f -exec chmod 0644 {} + \
 && find /opt/plow -type f -name '*.py' -exec chmod 0755 {} +

COPY image/s6-overlay/ /etc/s6-overlay/
