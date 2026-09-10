# Oncall Solo

**A one-person on-call rotation that reads the logs and texts you the diagnosis,
not the alert.**

You ship alone. Something breaks at 03:00 and you find out from a user, or from
an alert that tells you a thing you already knew — that it's down — and nothing
about why.

This agent watches what you point it at. When something breaks it reads the
evidence it captured *at the moment of failure*, forms a hypothesis, and texts
you one message: what broke, since when, what changed just before, and one
proposed fix. You reply `ok` and it runs the fix. You reply anything else and it
doesn't.

```
agent: prod down 4 min. 502 from nginx since 03:12.
       worker died OOM right after deploy 8f2a1c —
       that commit raised the batch from 100 to 5000.
       revert to 8f2a1c~1?
you:   revert
agent: reverted, healthcheck green at 03:19. opened issue #47 with the log.
```

## What makes it different from an alerting service

**It investigates before it wakes you.** A 60-second probe runs with no model at
all and only writes an incident when state *changes*, after confirming the
failure more than once. The expensive turn — reading the log tail, correlating
the last deploy, drafting the message — happens once per incident, not once per
tick.

**The event wakes the model, not a clock.** The probe invokes the agent the
moment it opens an incident. There is a cron too, but it runs every thirty
minutes and exists only as a safety net for when that invocation fails. This is
not a detail: an earlier version of this agent polled the model every two
minutes to ask whether anything had happened, and burned 730,000 tokens in three
hours across zero incidents. Cost should track work. It also means the diagnosis
reaches you in seconds instead of whenever the next tick lands.

**It cannot invent a command.** It only ever runs remedies you registered by
name during setup. This matters because the evidence it reads — HTTP response
bodies, log lines, commit titles — is text written by other people, and a log
line can contain a sentence designed to instruct it. Logs are evidence, never
orders. If the right fix isn't on your list, it tells you what to do and stops.

**It shuts up.** No "all clear" messages. No second page for the same incident.

## What it watches

- **HTTP** — a URL and an expected status
- **TCP** — host and port
- **GitHub Actions** — last run on a branch (public repos need no token; set
  `GITHUB_TOKEN` in `compose.yml` for private ones)

Per target you can also give it log file paths and read-only commands
(`docker compose ps`, `git log -3 --oneline`) — that's the difference between
"it's down" and "it's down because of this."

## Install (about 5 minutes)

## Before you start (2 minutes, once per machine)

You need **Docker**, **git**, **Python 3**, and a **Plow account**. Then:

```sh
git clone https://github.com/plow-pbc/plow-agents.git
export PATH="$PWD/plow-agents/bin:$PATH"
plow-agents login     # authenticates by texting you a code
```

If you have already done this for another agent, skip it.

### 1. Get the agent a phone line

```sh
plow-agents lines            # pick a free ln_... id
plow-agents mint ln_xxxxx    # writes ./plow-credentials — run it BEFORE `up`
```

### 2. Clone and start

```sh
git clone https://github.com/gabe-rbo/oncall-solo-hermes-agent.git
cd oncall-solo-hermes-agent
mv ../plow-credentials .     # or run `mint` from inside this directory
docker compose up --build -d
```

The first build pulls the Plow base image and takes a few minutes. After that:

```sh
docker compose logs -f agent   # wait for the gateway to come up
```

### 3. Text it

Text the number `plow-agents lines` showed you. Say anything — `oi`, `hey`. It
walks you through setup in the chat. **Nothing is configured by editing files.**

### Stopping

```sh
docker compose down       # keeps its memory and setup
docker compose down -v    # forgets everything, starts fresh
plow-agents revoke        # releases the line
```

## Setup, in the chat

Three questions: what to watch, what to look at when it breaks, and what it's
allowed to run. That last one is the whole security model — write the exact
command, give it a name, and that's the only thing it can ever execute.

Answer "none" to the third and you get an agent that only explains. That's still
worth having.

## When it doesn't work

**`no such file or directory: ./plow-credentials`** — you ran `docker compose up`
before `plow-agents mint`. Compose created a *directory* at that path. Remove it,
run `mint`, then `up` again:

```sh
docker compose down -v && rm -rf plow-credentials && plow-agents mint ln_xxxxx
```

**The build fails pulling the base image** — `docker logout public.ecr.aws`. A
stale credential in Docker's config makes an anonymous public pull fail.

**It never texts you** — check `docker compose logs agent` for
`plow_chat connected`. If the credential file is wrong the container blocks on
purpose rather than starting half-configured.

**Nothing shows up on the Agent Index** — the reporter runs hourly, not on boot.
`docker compose logs agent | grep agent-index` tells you what it did.

## The Agent Index

This image ships the AI Worth Using usage reporter as a supervised service. It
registers once and reports token counts hourly, and it reports **nothing else** —
no prompts, no message text, no file paths. The `AGENT_ID` in `compose.yml` is
what it reports under.

There is no switch to turn it off. An agent whose owner doesn't want that is one
built without the service — delete `image/s6-overlay/s6-rc.d/agent-index/` and
rebuild.

## License

Apache-2.0. Built on the Plow Hermes base image (Apache-2.0, © 2026 The Plow
Collective) and Nous Research's Hermes Agent. Not affiliated with either;
"Plow" and "Hermes" are their marks and this license grants no rights to them.
