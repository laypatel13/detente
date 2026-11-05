# Changelog

Each release's notes. When a version tag is pushed, the release workflow copies that version's section
onto its GitHub release page, so write the section before you tag.

## 0.1.0 (2026-11-05)

The first release: the `detente` command, for each laptop where a coding agent works.

```sh
uv tool install detente
```

`pipx install detente` works too. To watch a real recorded run first, with no setup: `uvx detente showcase`.

- `detente connect` connects a checkout to your team's tower: the commit gate, Claude Code's edit gate, the
  callsign and the pilot token. It asks for anything you leave out, and checks the token with the tower
  before it writes anything.
- `detente watch` tells the tower what the checkout's unpushed work changes and calls. While there's
  unpushed work it also fetches main, so a teammate's push that breaks it is caught too.
- `detente status`, `detente conflict` and `detente check <file>` read the tower from the terminal.
- `detente doctor` checks git, the config, both gates and the tower. `detente disconnect` takes a checkout
  off the tower and leaves anyone else's hooks alone.
- `detente showcase` plays the recorded run, with Roger.

Picking a fix stays in Switch: reply A or B in the conflict room.

The CLI guide: [cli/README.md](https://github.com/laypatel13/detente/blob/main/cli/README.md).
