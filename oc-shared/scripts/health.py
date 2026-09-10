#!/usr/bin/env python3
# Copyright 2026 Gabriel Ribeiro
# SPDX-License-Identifier: Apache-2.0
"""health.py -- o que este plantao viu, em numeros, sem modelo nenhum.

Existe porque "esta tudo bem?" e uma pergunta diferente de "algo caiu?". A
segunda o agente responde sozinho, no momento em que acontece. A primeira e
sobre TENDENCIA -- o alvo que cai toda terca, o incidente que voce nunca
respondeu, o tempo que a sonda leva pra perceber -- e ninguem manda mensagem
sobre tendencia as 3h da manha.

Tudo aqui sai dos incidentes ja gravados em disco. Nao sonda nada, nao chama
modelo, nao inventa numero: se um dado nao existe, a chave nao aparece, e quem
le a saida diz isso em vez de estimar.

    health.py            resumo dos ultimos 7 dias, JSON
    health.py --days 30  outra janela
"""
import argparse, json, os, statistics, sys
from datetime import datetime, timedelta, timezone

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
CONFIG, STATE, INCIDENTS = (os.path.join(BASE, "config.json"),
                            os.path.join(BASE, "state.json"),
                            os.path.join(BASE, "incidents"))
PROBE_EVERY = 60


def read_json(path, fallback):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return fallback


def when(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def load(days):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    for name in sorted(os.listdir(INCIDENTS)) if os.path.isdir(INCIDENTS) else []:
        if not name.endswith(".json"):
            continue
        inc = read_json(os.path.join(INCIDENTS, name), None)
        opened = when((inc or {}).get("opened_at"))
        if inc and opened and opened >= cutoff:
            inc["_opened"], inc["_recovered"] = opened, when(inc.get("recovered_at"))
            out.append(inc)
    return out


def summarise(days=7):
    config, state = read_json(CONFIG, {}), read_json(STATE, {})
    incidents = load(days)
    targets = [t.get("name") or t.get("url") or t.get("repo") for t in config.get("targets", [])]

    report = {
        # O idioma viaja COM os numeros, de proposito. Sem isto o sheet teria
        # que lembrar de abrir o config.json por conta propria pra saber em que
        # lingua responder -- e na primeira vez que rodou, nao lembrou: pediram
        # em ingles, a config dizia en-US, e a resposta saiu em portugues.
        # Dado que decide como responder anda junto com o dado que se responde.
        "language": config.get("language") or "(nao configurado -- siga o idioma do dono)",
        "window_days": days,
        "watching": targets,
        "now": {name: ("up" if (state.get(name) or {}).get("up", True) else "down")
                for name in targets if name in state},
        "incidents": len(incidents),
    }

    # Quanto tempo a sonda levou pra PERCEBER. Nao e adivinhado: cada incidente
    # grava quantas confirmacoes foram precisas, e o tick e fixo.
    detects = [inc.get("confirmations", 0) * PROBE_EVERY for inc in incidents if inc.get("confirmations")]
    if detects:
        report["time_to_detect_seconds"] = {
            "median": int(statistics.median(detects)),
            "worst": max(detects),
        }

    # Downtime so conta o que TEM fim. Um incidente ainda aberto entra separado,
    # porque somar "ate agora" numa media faz o numero mudar sozinho a cada
    # leitura -- e um painel que muda sem nada acontecer nao e um painel.
    closed = [(inc["_recovered"] - inc["_opened"]).total_seconds()
              for inc in incidents if inc.get("_recovered")]
    if closed:
        report["outage_minutes"] = {
            "total": round(sum(closed) / 60, 1),
            "median": round(statistics.median(closed) / 60, 1),
            "longest": round(max(closed) / 60, 1),
        }
    still_open = [inc["target"] for inc in incidents if not inc.get("_recovered")]
    if still_open:
        report["still_open"] = still_open

    per_target = {}
    for inc in incidents:
        row = per_target.setdefault(inc["target"], {"incidents": 0, "self_healed": 0, "remediated": 0})
        row["incidents"] += 1
        if inc.get("state") == "recuperado-sozinho":
            row["self_healed"] += 1
        if inc.get("state") in ("remediado", "recuperado"):
            row["remediated"] += 1
    if per_target:
        report["per_target"] = per_target

    # Instabilidade: o mesmo alvo caindo repetidamente e um problema DIFERENTE de
    # um alvo que caiu uma vez, e e o que mais gasta a paciencia de quem recebe.
    flapping = {name: row["incidents"] for name, row in per_target.items() if row["incidents"] >= 3}
    if flapping:
        report["flapping"] = flapping

    # O que ficou sem resposta. Um incidente avisado e nunca respondido nao e
    # falha do agente -- e informacao sobre a operacao, e vale dizer em voz alta.
    unanswered = [{"target": inc["target"], "opened": inc["opened_at"],
                   "proposed": inc.get("proposed_remedy")}
                  for inc in incidents
                  if inc.get("state") == "avisado" and not inc.get("_recovered")]
    if unanswered:
        report["notified_never_answered"] = unanswered

    if not incidents:
        report["note"] = "nenhum incidente na janela -- silencio e o estado normal"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args(argv)
    if args.days < 1:
        sys.exit("health: --days precisa ser 1 ou mais")
    print(json.dumps(summarise(args.days), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
