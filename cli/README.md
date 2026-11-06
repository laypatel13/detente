<p align="center">
  <img src="https://raw.githubusercontent.com/laypatel13/detente/main/art/roger-avatar-256.png" width="72" alt="Roger, the tower">
</p>

<h1 align="center">The Detente CLI</h1>

<p align="center">
  <b>Traffic control for coding agents.</b> Connect each checkout to your team's tower,<br>
  and Detente catches the moment one agent's change breaks code another agent is writing, before anyone pushes.
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/laypatel13/detente/main/cli/images/cli-home.png" width="680" alt="The detente home screen: Roger, where you are, and the commands you'll use most">
</p>

---

## At a glance

| Command | What it does |
|---|---|
| [`detente showcase`](#detente-showcase) | Plays a real recorded run. No tower, no setup. |
| [`detente connect`](#detente-connect) | Connects this checkout to your team's tower. |
| [`detente watch`](#detente-watch) | Tells the tower what this checkout's unpushed work changes and calls. |
| [`detente doctor`](#detente-doctor) | Checks git, both gates, the token and the tower. |
| [`detente status`](#detente-status) | Flights in the air, open conflicts and the latest messages. |
| [`detente conflict`](#detente-conflict) | One conflict in full, with the fixes on offer. |
| [`detente check <file>`](#detente-check) | Is this checkout cleared to edit these files? |
| [`detente disconnect`](#detente-disconnect) | Takes this checkout off the tower. |
| [`detente`](#detente) | Roger, where you are, and the commands you'll use most. |

The CLI never picks a fix. People decide in chat: [what to say](#decisions-happen-in-chat).

## Install

You need Python 3.12 or newer.

```sh
uv tool install detente
```

`pipx install detente` works too. Install it rather than running it with `uvx` before you connect a checkout:
the gates run from wherever the command is installed, and `uvx` keeps it only in a cache.

Or try the showcase without installing anything:

```sh
uvx detente showcase
```

## See it first: the showcase

A real run, recorded through Switch. Three coding agents on three laptops work on one project. One changes
`create_session(user)` to `create_session(user, ttl)` while another writes code that calls it the old way. No
lines overlap, so file locks and merge checks stay quiet. Detente holds both flights, opens a conflict room, and
you pick the fix. No tower, no setup, and it never touches your checkouts.

```sh
detente showcase
```

<p align="center">
  <img src="https://raw.githubusercontent.com/laypatel13/detente/main/cli/images/cli-showcase.png" width="680" alt="detente showcase: flight plans, a collision with Roger alarmed, the person's pick, and three flights landing">
</p>

## Connect a laptop

Someone on your team runs the tower first: Switch and Detente, with the
[setup guide](https://github.com/laypatel13/detente#run-it). Then, in each checkout an agent works in:

**1.** Connect it. It asks for anything you leave out, and checks the pilot token with the tower before it writes
anything:

```sh
detente connect --callsign lay-claude --person lay --vendor "Claude Code" --url http://localhost:8100
```

`--url` is `http://localhost:8100` on the tower machine. From any other laptop it's port 8100 at the tower's
`TOWER_ADDR`, once the tower [lets the team's laptops in](https://github.com/laypatel13/detente#let-the-teams-laptops-in).
`--callsign` is the agent's name in Switch and `--person` is your username in the chat app. The pilot token is
`DETENTE_PILOT_TOKEN` in the tower's `.env`. It's asked for rather than typed on the command line, so it stays out
of your shell history (or set `DETENTE_TOKEN`).

**2.** Keep the watcher running while agents work:

```sh
detente watch
```

**3.** In [Switch Console](https://docs.switchagents.ai/switch-rooms/getting-started/install-switch-console), add the
agent to the `tower` room. Console runs the agent and connects it to the tower's Switch server, port 8110. It
learns the flight-plan rules from the room.

**4.** Check that it's all wired up:

```sh
detente doctor
```

## Every command

<p align="center">
  <img src="https://raw.githubusercontent.com/laypatel13/detente/main/cli/images/cli-help.png" width="680" alt="detente --help: the commands grouped as Start, The tower and Showcase">
</p>

### `detente`

Roger, where you are, and the commands you'll use most. Outside a git checkout it points you to the showcase.

```sh
detente
```

### `detente connect`

Connects the checkout you're in to your team's tower. It installs the commit gate and Claude Code's edit gate,
and saves the callsign and the pilot token. It asks for anything you leave out, and checks the token with the
tower before it writes anything.

```sh
detente connect --callsign lay-claude --person lay --vendor "Claude Code" --url http://localhost:8100
```

| Option | What it sets |
|---|---|
| `--callsign` | The agent's name in Switch, such as `lay-claude` |
| `--person` | Your username in the chat app, such as `lay` |
| `--vendor` | The agent tool: `"Claude Code"`, `"Codex"`, `"OpenCode"`… |
| `--url` | The tower's address, such as `http://localhost:8100` |
| `--token` | The pilot token. Leave it out to be asked, so it stays out of your shell history, or set `DETENTE_TOKEN` |

### `detente watch`

Tells the tower what this checkout's unpushed work changes and calls. While there's unpushed work it also fetches
main every 10 seconds, so a teammate's push that breaks it collides too. Leave it running; Ctrl+C stops it.

```sh
detente watch
```

### `detente doctor`

Checks git, the config, both gates (and that they still point at a Python that exists), and that the tower answers
and takes the token. Exits `3` if anything is wrong.

```sh
detente doctor
```

### `detente status`

Flights in the air, open conflicts and the latest messages.

```sh
detente status -n 10
```

| Option | What it does |
|---|---|
| `--messages`, `-n` | How many recent messages to show (default 5) |

### `detente conflict`

One conflict in full: what changed, what it breaks, the fixes on offer and who picked. Leave the name out for the
open one.

```sh
detente conflict conflict-create-session-3f1a
```

<p align="center">
  <img src="https://raw.githubusercontent.com/laypatel13/detente/main/cli/images/cli-conflict.png" width="680" alt="detente conflict: total_due gained a required currency argument on main, statement.py:5 still calls it the old way, and the two fixes on offer">
</p>

### `detente check`

Is this checkout cleared to edit these files? Exits `1` if any isn't. For agents that don't run Claude Code's hooks,
and for scripts: ask before editing.

```sh
detente check billing/refunds.py
```

### `detente disconnect`

Removes this checkout's gates and config. Anyone else's hooks, your code and your commits stay as they are.

```sh
detente disconnect --yes
```

| Option | What it does |
|---|---|
| `--yes`, `-y` | Don't ask first |

### `detente showcase`

The recorded run. No tower, and it never touches your checkouts.

```sh
detente showcase --fast
```

| Option | What it does |
|---|---|
| `--fast` | Plays it without pauses |

### Options every command shares

| Option | Works with | What it does |
|---|---|---|
| `--repo PATH`, `-r PATH` | every command that uses a checkout | Use another checkout than the one you're in |
| `--json` | `doctor`, `status`, `conflict`, `check` | Print the raw result as JSON, for scripts |
| `--help` | every command | Show the command's options |

### Exit codes

| Code | Means |
|---|---|
| `0` | All fine |
| `1` | A finding: `check` refused a file |
| `2` | A usage problem |
| `3` | The setup or the tower: `doctor` found a problem, or the tower didn't answer |

## Decisions happen in chat

The CLI connects checkouts and reads the tower. It never picks a fix. Decisions happen in Switch, where both people
and both agents see them:

| Who | Says, in chat | What happens |
|---|---|---|
| A person | `A` or `B`, in a conflict room | Picks the fix |
| A person | `@detente ground stop` | Every gate closes until resume |
| A person | `@detente resume` | Gates reopen |
| A person | `@detente land <callsign>` | Clears that flight, for an agent that died or a break you accept |

## What goes where

- `detente connect` writes `.detente` into the checkout: the callsign, the tower's address and the pilot token. It
  keeps that file out of git with the checkout's own `.git/info/exclude`, so it's never committed.
- `detente watch` sends your tower the paths your unpushed work touched, which lines changed, the signatures of
  the functions it changed, and each call's file, line and text. Never whole files.
- The gates send the tower only the paths of the files being edited or committed.
- Everything goes to the tower address you gave, and nowhere else. The CLI sends no telemetry.

## Uninstall

Take each checkout off the tower:

```sh
detente disconnect
```

Then remove the command:

```sh
uv tool uninstall detente
```

---

<p align="center">
  Part of <a href="https://github.com/laypatel13/detente">Detente</a> · MIT license ·
  <i>When rivals stop fighting.</i>
</p>
