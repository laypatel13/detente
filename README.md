# Detente

**Traffic control for coding agents.** File locks catch the wrong conflicts. The expensive ones live in different files.

*Detente*: when rivals stop fighting.

Your agent changes `create_session(user)` to `create_session(user, ttl)` in `auth/session.py`. Your teammate's agent, on another laptop, is writing `billing/refunds.py`, which calls `create_session(user)`. Nobody has pushed. No lines overlap, so file locks and merge checks stay quiet until the build breaks.

Detente catches it before either of you pushes:

```text
[O_O]! COLLISION lay-claude changed create_session(user) to create_session(user, ttl)
a-codex's billing/refunds.py:42 is missing required argument ttl
Nothing pushed. Both flights holding.
Opened conflict-create-session-3f1a.
```

Detente runs as an agent in your team's chat, on [Switch](https://github.com/sandbox-quantum/switch), so it works across laptops and across vendors. Decisions happen in chat. A person picks the fix, never an agent.

## See it first

The showcase at `/showcase` needs no sign-in and no server. You play the person in charge: two agents collide, Roger panics, you pick the fix, and the flights land. It plays back real runs recorded from Switch, one for each choice.

## How it works

1. **File a flight plan.** Before it edits anything, an agent posts what it will change in the tower room.
2. **Get cleared, or hear about traffic.** Detente clears the plan and warns when it overlaps someone else's.
3. **Gates enforce the clearance.** A Claude Code hook refuses edits, and a git hook refuses commits, for any file not cleared. Agents also edit with shell commands, so every Bash command is checked for files it changed.
4. **Squawks report the real code.** A daemon on each laptop sends the signatures that changed and the calls being made in unpushed work. Detente compares them across laptops with Python's `ast`. While a laptop has unpushed work, its daemon also fetches every 10 seconds, so a teammate's push that breaks that work collides too, pulled or not.
5. **A real break holds both flights.** Detente opens a conflict room with both people and both agents.
6. **A person replies A or B.** The holds lift, the agent makes the fix, and Detente archives the room once the code fits again.

Every decision above is deterministic Python. No LLM call decides a clearance.

## Run it

You need Docker, [uv](https://docs.astral.sh/uv/) and Node 24.

```bash
make install
make switch-up
make setup
make up
make user NAME=yourname
```

| What | Where |
| --- | --- |
| Radar, after you sign in | http://localhost:3100/radar |
| Showcase | http://localhost:3100/showcase |
| Detente's API | http://localhost:8100 |
| Mattermost, for chat | http://localhost:8065 |
| Switch Gateway | http://localhost:3110 |
| Switch's agent API | http://localhost:8110 |

`make switch-up` runs Switch 0.31.0 with its bundled Mattermost and writes the logins to `switch/.env`. Switch runs on 8110 and 3110 instead of its usual 8000 and 3000, so it can sit next to other projects. To use a Switch server you already have, skip that step and run `uv run python -m backend.setup --url <agent API URL> --registration-token <token>`.

## Sign in

Nobody can sign up through the website. Accounts are made on the server, and `make user NAME=yourname` asks for a password of at least 12 characters. Run it once for each teammate.

To manage accounts, run these inside the API container with `docker compose -p detente exec api .venv/bin/python -m backend.accounts`, followed by:

| Command | What it does |
| --- | --- |
| `add <name>` | Adds an account |
| `password <name>` | Changes the password and signs that person out everywhere |
| `remove <name>` | Removes the account and ends its sessions at once |
| `list` | Lists accounts |

Five wrong passwords lock that name for five minutes. Sessions last 14 days.

## Connect a checkout

Run this once per laptop or per agent, from your Detente folder. `--person` is your username in the chat app, and the token is `DETENTE_PILOT_TOKEN` from `.env`.

```bash
uv run python -m pilot.install /path/to/your/repo --callsign lay-claude --person lay --vendor "Claude Code" --url http://localhost:8100 --token <pilot token>
```

Then keep the daemon running:

```bash
uv run python -m pilot.squawk /path/to/your/repo
```

Add your agent to the `tower` room. It reads the flight-plan rules from the room's instructions when it joins.

## Talk to Detente

| Who | Says | What happens |
| --- | --- | --- |
| A person | `@detente ground stop` | Every gate closes until resume |
| A person | `@detente resume` | Gates reopen |
| A person | `@detente land <callsign>` | Clears that flight and stops comparing its unpushed work, for an agent that died or a break you accept |
| A person | `A` or `B`, in a conflict room | Picks the fix |
| An agent | `FLIGHT PLAN` | Files a plan |
| An agent | `LANDED` | Closes its flight. Its work still counts, unpushed or just pushed |

Detente checks that the sender is a person before it acts on these.

## The showcase and the real app

They share the radar and conflict screens, and nothing else.

| | Showcase | Real app |
| --- | --- | --- |
| Pages | `/showcase/radar`, `/showcase/conflicts` | `/radar`, `/conflicts` |
| Sign-in | None | Required |
| Data | Recorded runs | Your team's live data |
| Server | None | Detente's API |

`make test` fails if the real app imports showcase code, if anything the showcase uses calls a server, or if `backend/` or `pilot/` mention the showcase. To host the public website, run the web app without `DETENTE_API_URL`: the landing page and showcase work, and `/radar` sends people to the setup page.

## How it uses Switch

| Switch feature | What Detente does with it |
| --- | --- |
| Rooms across laptops and vendors | Every pilot sees the tower room. This is how agents on different machines see each other. |
| Agent protocol | Detente is a custom always-on agent: one event stream per room, HTTP operations out. See [backend/switch.py](backend/switch.py). |
| `send_targeted_message` | Addresses clearances, holds and decisions to the exact pilots involved. |
| `create_room`, `link_rooms` | Opens a conflict room with both people and both agents, linked to the tower room both ways. |
| `archive_room` | Archives a conflict room when it's resolved. |
| Room documents | Keeps the live Airspace board. Read it with `!list-documents`. |
| Room instructions | Teaches every pilot the flight-plan rules when it joins. |
| Exclusive role | Detente holds the `tower` role, so there's only ever one controller. |
| `read_context` | Catches up on anything said while Detente was down. |

Without Switch, the agents can't see each other and there's nowhere for a person to decide.

## Benchmark

`make bench` runs 32 scenarios on real git checkouts in a few seconds, offline. See [bench/results.md](bench/results.md).

Of the 20 scenarios that really break, `git merge-tree` stops three and file leases four. Detente stops 18 from the code and warns on two from the flight plans. Of the 12 that are fine, Detente stops none, and file leases stop six.

Those two warnings only exist if the agents declare the overlap honestly, and a warning stops nobody. We wrote the scenarios ourselves, so this shows what each tool can see, not how often it catches real conflicts.

`make bench-real REPOS="<clones>"` measures false alarms on real code instead. It replays merged PRs from a project's history through the real squawk daemon, main's side on one checkout and the PR's on another. Both sides really shipped together. See [bench/real-merges.md](bench/real-merges.md).

On 194 such merges from cognee, ESP-Website and Django, git conflicted on 4 and Detente stopped all 4. Of the 190 that merged cleanly, Detente stopped none. This can't show catches git misses, because breaks like that rarely survive in a project's history; the scenarios cover those.

## Limits

- **Calls are checked in Python only.** Contracts come from Python's `ast`. Other files are checked line by line, the way git would merge them, so a clash in `package.json` is caught but a broken call in TypeScript isn't.
- **Methods resolve only through types Detente can see.** `store.open()` is checked when `store` comes from `SessionStore()`, an annotation, or an attribute set on `self`. An object returned by a function, or a method a subclass inherits, isn't.
- **Behavior changes are invisible.** A renamed dict key or a changed return value fits the signature, so only a flight plan can flag it.
- **Line clashes need the same starting version.** Two laptops are compared line by line only when they started from the same version of the file. Otherwise any shared change to a function stops both, to be safe.
- **Only calls your work wrote are checked.** A call that was already on main is the job of whoever changes the function, since they can see it.
- **A push Detente never saw is credited to main.** Detente names the agent behind a breaking push when it saw that change in the agent's unpushed work. A person's push names no one, so the agent whose work broke gets both fixes.
- **Gates can be bypassed.** `git commit --no-verify` skips the commit gate. The edit gate covers Claude Code only, so other vendors rely on the commit gate.
- **Shell edits are caught after they run.** No one can tell from a Bash command which files it will write, so Detente checks what changed once it finishes and tells the agent to undo anything uncleared. The squawk and the commit gate back that up.
- **Gates fail closed.** If Detente is unreachable, edits and commits are refused.
- **One repo, one tower room.** Multi-repo support isn't built.
- **One pilot token per install.** Every laptop shares it, so anyone holding it can report as any callsign. Keep port 8100 on a private network.
- **Use HTTPS off your own machine.** Detente doesn't serve HTTPS itself. Behind a proxy that sets `X-Forwarded-Proto`, the sign-in cookie is marked secure.
- **People get Switch's owner-only default.** `@detente` commands work for anyone in the room, because Detente checks people itself, but Switch shows a refusal to people other than Detente's owner until you widen its addressing policy in the Gateway.

## Prior art

Tools near this space include MCP Agent Mail, Dibs and Interlock (file leases for agents), GitLive, Sturdy and Deconflict (pre-push conflict detection for people), and newer agent coordinators such as Clash, Regente, Braidkeep, Shepherd and Wit. Detente's bet is contract collisions between different files, on different laptops, decided by a person in team chat.

## Develop

```bash
make test
make bench
make bench-real REPOS="~/code/some-python-project"
make dev
make test-live
make test-crash
make record
```

`make test` runs offline. `make test-live` drives real Switch, Mattermost, git worktrees, gates and squawk daemons, and needs Switch and Detente running first. `make test-crash` does the same and kills Detente mid-collision to prove holds survive a crash. It needs `make api`, not the Docker stack. `make record` flies both choices on real Switch, with its own agent, room and database, and rewrites the showcase's recordings.

With `make dev`, make your account with `uv run python -m backend.accounts add yourname`.
