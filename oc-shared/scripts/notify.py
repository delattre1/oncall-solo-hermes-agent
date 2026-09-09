#!/usr/bin/env python3
# Copyright 2026 Gabriel Ribeiro
# SPDX-License-Identifier: Apache-2.0
"""notify.py -- a unica forma deste agente falar sem ser perguntado.

Um POST em {PLOW_API_BASE}/v1/chats/{PLOW_HOME_CHANNEL}/messages com o
PLOW_AGENT_TOKEN do proprio container. Existe porque `hermes cron --deliver`
repassa TODA resposta final, inclusive as silenciosas: um vigia que fica quieto
99% do tempo nao pode usar aquele braco sem virar spam. Aqui quem decide se ha
mensagem e o chamador, e o silencio e o padrao.

Le o texto do stdin ou de --file. Recusa antes de postar qualquer coisa se a
configuracao de chat estiver em branco, para que uma entrega pela metade nao
seja possivel.
"""
import argparse, json, os, sys, urllib.error, urllib.request


def require(name):
    value = (os.environ.get(name) or "").strip()
    if not value:
        sys.exit(
            f"notify: {name} esta vazio ou ausente no ambiente deste container.\n"
            "  Recusando ANTES de postar: uma configuracao de chat em branco nao\n"
            "  pode virar meia entrega. O primeiro boot publica esses valores a\n"
            "  partir da credencial que o host deixou; rode isto de um turno, que\n"
            "  herda o ambiente do gateway -- um `docker exec` cru nao carrega nada."
        )
    return value


def chat_endpoint():
    base = (os.environ.get("PLOW_API_BASE") or "https://api.plow.co").rstrip("/")
    uid = require("PLOW_HOME_CHANNEL")
    return f"{base}/v1/chats/{uid}/messages", require("PLOW_AGENT_TOKEN")


def post(url, token, body, timeout=30):
    request = urllib.request.Request(
        url,
        data=json.dumps({"body": body}).encode("utf-8"),
        headers={"authorization": "Bearer " + token,
                 "content-type": "application/json",
                 "accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        sys.exit(f"notify: o Plow Chat respondeu {exc.code}")
    except Exception as exc:
        # Sem traceback: um traceback do urllib carrega a URL que recebeu.
        sys.exit(f"notify: nao consegui alcancar o Plow Chat ({type(exc).__name__})")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", help="le o corpo deste arquivo em vez do stdin")
    parser.add_argument("--dry-run", action="store_true",
                        help="mostra o que seria enviado e nao envia")
    args = parser.parse_args(argv)

    body = open(args.file, encoding="utf-8").read() if args.file else sys.stdin.read()
    body = body.strip()
    if not body:
        # Silencio e um resultado valido, nao um erro: e o estado normal de um
        # vigia. Sair 0 sem postar e o contrato.
        print("notify: corpo vazio, nada a dizer")
        return 0

    url, token = chat_endpoint()
    if args.dry_run:
        print(f"dry-run: postaria {len(body)} chars em {url.split('/v1/')[0]}/v1/...")
        return 0
    post(url, token, body)
    print(f"notify: mensagem postada ({len(body)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
