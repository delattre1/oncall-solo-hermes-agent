#!/usr/bin/env python3
# Copyright 2026 Gabriel Ribeiro
# SPDX-License-Identifier: Apache-2.0
"""probe.py -- a metade barata do plantao: detectar, nunca explicar.

Roda a cada 60s sob o s6, sem modelo nenhum. Sonda cada alvo, guarda o
resultado, e so escreve um incidente quando o estado MUDA. O turno caro -- ler
evidencia, formar hipotese, propor conserto -- e do agente, e so acontece
quando este arquivo diz que ha o que explicar.

Essa divisao e o desenho inteiro. Um vigia que chama o modelo a cada tick queima
token sem trabalho real e e exatamente o que o anuncio do hackathon chama de
"rodar seu proprio agente num loop durante a noite". Aqui o modelo so acorda
quando alguma coisa aconteceu de verdade.

Confirmacao antes de incidente: um alvo precisa falhar `confirmations` vezes
seguidas (padrao 2) pra virar DOWN. Uma falha isolada de rede as 3h nao vale
acordar ninguem, e um alerta que o dono aprende a ignorar e pior que nenhum.
"""
import json, os, socket, subprocess, sys, time, urllib.error, urllib.request
# Quanto tempo esperar o turno do agente. A sonda dorme 60s entre ticks, entao um
# turno lento atrasa o proximo tick -- aceitavel, porque quando isto roda EXISTE
# um incidente aberto e a cadencia importa menos que a explicacao chegar.
ESCALATE_TIMEOUT = 150


def escalate(incident_id):
    """Acorda o agente AGORA, no momento em que o incidente abre.

    Esta funcao e a diferenca entre um agente honesto e um que so parece
    ocupado. Sem ela, quem acorda o modelo e um cron de poucos minutos que roda
    o dia inteiro e quase sempre responde `quiet` -- token queimado a esmo,
    exatamente o que o anuncio do hackathon chama de "rodar seu proprio agente
    num loop durante a noite". Medido neste agente antes da mudanca: 730 mil
    tokens em tres horas, com zero incidentes novos.

    Com ela, o gasto acompanha o trabalho: perto de zero enquanto esta tudo no
    ar, e um turno de verdade quando algo cai. De quebra, a mensagem chega em
    segundos em vez de esperar ate o proximo tick.

    Nunca fatal. Se o turno falhar -- chave ausente, modelo fora, o que for --
    o cron de rede de seguranca pega o incidente no proximo passe. Uma sonda que
    morre porque o modelo esta indisponivel para de vigiar, que e o oposto do
    que ela existe para fazer.
    """
    hermes = "/opt/hermes/bin/hermes"
    if not os.path.exists(hermes):
        return False
    prompt = (f"O incidente {incident_id} acabou de abrir. Rode o oc-diagnose "
              "agora: leia a evidencia, forme a hipotese, proponha no maximo um "
              "remedio da lista e avise pelo notify.py.")
    try:
        done = subprocess.run([hermes, "-z", prompt, "--skills", "oc-diagnose", "--cli"],
                              capture_output=True, text=True, timeout=ESCALATE_TIMEOUT)
    except Exception as exc:
        print(f"probe: nao consegui acordar o agente ({type(exc).__name__}); "
              f"o cron de rede de seguranca pega no proximo passe")
        return False
    if done.returncode != 0:
        print(f"probe: o turno do agente saiu {done.returncode}; "
              f"o cron de rede de seguranca pega no proximo passe")
        return False
    return True

from datetime import datetime, timezone

# Saida em linha. Sob o supervisor a saida e um PIPE, e o Python bufferiza em
# blocos quando nao e terminal -- entao tudo que este arquivo imprime fica preso
# num buffer e o log do servico aparece vazio. Medido: a sonda rodou horas
# abrindo incidentes e o `docker compose logs` so mostrava "service starting".
# Um vigia que nao consegue contar o que fez e indistinguivel de um parado.
try:
    sys.stdout.reconfigure(line_buffering=True)
except AttributeError:          # Python < 3.7
    pass

HOME = os.environ.get("HERMES_HOME", "/var/lib/hermes")
BASE = os.path.join(HOME, "oncall")
CONFIG = os.path.join(BASE, "config.json")
STATE = os.path.join(BASE, "state.json")
INCIDENTS = os.path.join(BASE, "incidents")

DEFAULT_CONFIRMATIONS = 2
DEFAULT_TIMEOUT = 10
BODY_SNIPPET = 600


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_json(path, fallback):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return fallback
    except (OSError, ValueError) as exc:
        # Nao inventa um estado vazio por cima de um arquivo ilegivel: isso
        # reabriria todo incidente ja aberto na proxima passada.
        sys.exit(f"probe: {path} existe e nao pode ser lido ({exc}); parando")


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def probe_http(target):
    url = target["url"]
    expect = target.get("expect_status", 200)
    timeout = target.get("timeout", DEFAULT_TIMEOUT)
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"user-agent": "oncall-solo/1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(BODY_SNIPPET).decode("utf-8", "replace")
            elapsed = round((time.monotonic() - started) * 1000)
            ok = response.status == expect
            return ok, {
                "status": response.status, "expected": expect,
                "ms": elapsed, "body_head": body,
            }
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read(BODY_SNIPPET).decode("utf-8", "replace")
        except Exception:
            pass
        return False, {"status": exc.code, "expected": expect,
                       "ms": round((time.monotonic() - started) * 1000),
                       "body_head": body}
    except Exception as exc:
        return False, {"error": f"{type(exc).__name__}: {exc}",
                       "expected": expect,
                       "ms": round((time.monotonic() - started) * 1000)}


def probe_tcp(target):
    host, port = target["host"], int(target["port"])
    timeout = target.get("timeout", DEFAULT_TIMEOUT)
    started = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, {"ms": round((time.monotonic() - started) * 1000)}
    except Exception as exc:
        return False, {"error": f"{type(exc).__name__}: {exc}",
                       "ms": round((time.monotonic() - started) * 1000)}


def probe_github_actions(target):
    """O ultimo run do workflow no branch. Token opcional: repo publico
    responde sem ele, e um repo privado sem token e uma configuracao que o
    dono fez errado -- reportada como falha de SONDA, nao como build quebrado."""
    repo, branch = target["repo"], target.get("branch", "main")
    url = (f"https://api.github.com/repos/{repo}/actions/runs"
           f"?branch={branch}&per_page=1")
    headers = {"accept": "application/vnd.github+json",
               "user-agent": "oncall-solo/1"}
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["authorization"] = "Bearer " + token
    try:
        with urllib.request.urlopen(
                urllib.request.Request(url, headers=headers), timeout=15) as response:
            runs = json.loads(response.read() or b"{}").get("workflow_runs") or []
    except Exception as exc:
        return None, {"probe_error": f"{type(exc).__name__}: {exc}"}
    if not runs:
        return None, {"probe_error": f"nenhum run em {repo}@{branch}"}
    run = runs[0]
    ok = run.get("conclusion") in (None, "success")
    return ok, {"workflow": run.get("name"), "conclusion": run.get("conclusion"),
                "status": run.get("status"), "url": run.get("html_url"),
                "head_sha": (run.get("head_sha") or "")[:12],
                "title": run.get("display_title")}


def tail(path, lines=60):
    try:
        out = subprocess.run(["tail", "-n", str(lines), path],
                             capture_output=True, text=True, timeout=10)
        return out.stdout[-4000:]
    except Exception as exc:
        return f"(nao consegui ler {path}: {type(exc).__name__})"


def evidence_for(target, detail):
    """O que o agente vai ler quando for explicar. Coletado AQUI, no momento da
    falha, porque dois minutos depois o log ja rolou."""
    bundle = {"probe": detail}
    for path in target.get("logs", []):
        bundle.setdefault("logs", {})[path] = tail(path)
    for command in target.get("evidence_commands", []):
        try:
            out = subprocess.run(command, shell=True, capture_output=True,
                                 text=True, timeout=20)
            bundle.setdefault("commands", {})[command] = (out.stdout + out.stderr)[-2000:]
        except Exception as exc:
            bundle.setdefault("commands", {})[command] = f"({type(exc).__name__})"
    return bundle


def holding(config, now=None):
    """Se a escalada deve ESPERAR -- e por que.

    Duas razoes, e as duas sao do dono, nao do agente:

    `snooze_until` -- ele disse "vou fazer deploy, fica quieto ate as X". Sem
    isso, a unica forma de nao ser interrompido durante uma janela de manutencao
    e desligar o agente, e quem desliga esquece de ligar.

    `quiet_hours` -- a faixa em que so o que ele marcou como critico interrompe.
    Um alvo em `except_targets` fura o silencio; o resto espera. Isto NAO impede
    o incidente de abrir: detectar e de graca e o registro tem que existir. So a
    mensagem espera, e o cron de rede de seguranca entrega quando a faixa passa.

    Devolve o motivo (string) ou None. String em vez de bool porque quem chama
    imprime o motivo no log -- um agente que fica em silencio sem dizer por que
    e indistinguivel de um agente quebrado.
    """
    now = now or datetime.now(timezone.utc)
    until = when_iso(config.get("snooze_until"))
    if until and now < until:
        return f"soneca ate {config['snooze_until']}"
    quiet = config.get("quiet_hours") or {}
    start, end = quiet.get("from"), quiet.get("to")
    if start is None or end is None:
        return None
    hour = now.astimezone().hour
    inside = (start <= hour or hour < end) if start > end else (start <= hour < end)
    return f"horario de silencio ({start}h-{end}h)" if inside else None


def when_iso(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


PROBES = {"http": probe_http, "tcp": probe_tcp, "github_actions": probe_github_actions}


def main():
    config = read_json(CONFIG, None)
    if not config:
        # Nao e erro: e um agente que ainda nao foi configurado. O SOUL.md
        # manda o dono pro oc-setup na primeira mensagem.
        print("probe: sem config ainda -- nada a vigiar")
        return 0
    targets = config.get("targets") or []
    confirmations = int(config.get("confirmations", DEFAULT_CONFIRMATIONS))
    state = read_json(STATE, {})
    changed = False

    # Alvos que sairam da config saem do estado junto. Sem isto, remover um alvo
    # que estava fora deixa a entrada dele em `up: false` para sempre, e o
    # oc-status -- que le exatamente este arquivo -- passa a responder que algo
    # esta caido quando ninguem mais esta olhando pra aquilo. Um plantao que
    # mente sobre o proprio escopo e pior que um que nao responde.
    known = {t.get("name") or t.get("url") or t.get("repo") for t in targets}
    for gone in [name for name in state if name not in known]:
        del state[gone]
        changed = True
        print(f"probe: {gone} saiu da config -- removido do estado")

    for target in targets:
        name = target.get("name") or target.get("url") or target.get("repo")
        kind = target.get("kind", "http")
        probe = PROBES.get(kind)
        if not probe:
            continue
        ok, detail = probe(target)
        if ok is None:
            # Sonda quebrada, nao servico quebrado. Nunca vira incidente: o
            # dono nao pode consertar o que nao aconteceu.
            print(f"probe: {name}: sonda indisponivel -- {detail.get('probe_error')}")
            continue

        entry = state.setdefault(name, {"up": True, "fails": 0, "incident": None})
        if ok:
            if not entry["up"]:
                entry.update(up=True, fails=0)
                changed = True
                if entry.get("incident"):
                    path = os.path.join(INCIDENTS, entry["incident"])
                    incident = read_json(path, None)
                    if incident:
                        incident["recovered_at"] = now()
                        incident["state"] = ("recuperado-sozinho"
                                             if incident.get("state") == "novo"
                                             else "recuperado")
                        write_json(path, incident)
                entry["incident"] = None
            else:
                entry["fails"] = 0
            continue

        entry["fails"] += 1
        changed = True
        if entry["up"] and entry["fails"] >= confirmations:
            entry["up"] = False
            ident = f"{time.strftime('%Y%m%dT%H%M%S')}-{name}".replace("/", "_")
            filename = ident + ".json"
            write_json(os.path.join(INCIDENTS, filename), {
                "id": ident,
                "target": name,
                "kind": kind,
                "opened_at": now(),
                "confirmations": entry["fails"],
                # `novo` e o unico estado que faz o agente gastar um turno.
                # Ele mesmo move pra `avisado` depois de mandar a mensagem.
                "state": "novo",
                "evidence": evidence_for(target, detail),
                "remedies_offered": [r.get("name") for r in config.get("remedies", [])],
            })
            entry["incident"] = filename
            print(f"probe: INCIDENTE aberto para {name} ({ident})")
            # O estado vai pro disco ANTES de acordar o agente: o turno le esse
            # arquivo, e um turno que corre na frente da gravacao le um incidente
            # que ainda nao existe.
            write_json(STATE, state)
            changed = False
            # Alvo marcado como excecao fura o silencio; o resto espera. O
            # incidente ja esta em disco de qualquer jeito -- e so a MENSAGEM
            # que segura, e o cron de rede de seguranca a entrega depois.
            excepted = name in ((config.get("quiet_hours") or {}).get("except_targets") or [])
            reason = None if excepted else holding(config)
            if reason:
                print(f"probe: {ident} aberto, mas nao vou acordar ninguem agora — {reason}")
            elif escalate(ident):
                print(f"probe: agente acordado para {ident}")

    if changed:
        write_json(STATE, state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
