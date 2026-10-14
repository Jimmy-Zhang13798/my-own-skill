# my-own-skill

My personal Claude Code skills.

| Skill | What it does |
|---|---|
| `delete-conversation` | Permanently delete local Claude Code conversations (transcripts, session files, input history, `~/.claude.json` entries and backups). |

## Install on another computer

If `~/.claude/skills` doesn't exist yet:

```sh
git clone https://github.com/Jimmy-Zhang13798/my-own-skill.git ~/.claude/skills
```

If it already exists:

```sh
git clone https://github.com/Jimmy-Zhang13798/my-own-skill.git /tmp/my-own-skill
cp -R /tmp/my-own-skill/delete-conversation ~/.claude/skills/
```

Restart Claude Code afterwards so it picks up the new skill.

## Adding a new skill

Put it in `~/.claude/skills/<name>/`, add `!/<name>/` to `.gitignore`, then commit and push.
