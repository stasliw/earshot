# Earshot: Auto Read Aloud

![Earshot icon](assets/icon.svg)

Reads every Claude reply aloud automatically in your Mac's system voice, so there's no speaker button to click each time. Turn it on with `/earshot:on`; your next message cuts it off.

## Requirements

- macOS. Earshot speaks through the `say` command built into every Mac. On other systems `/earshot:on` tells you it needs macOS and does nothing else.
- Claude Code. Earshot works through hooks, which claude.ai chat doesn't run.

## Install

In Claude Code:

```
/plugin marketplace add stasliw/earshot
/plugin install earshot@earshot
```

## Use it

- `/earshot:on` starts reading replies aloud, in every Claude Code session on this Mac.
- `/earshot:off` stops it.
- Sending a new message stops a reply that's still being read.

Some ways to use it:

1. Ask Claude to explain an error, and listen while you look at the code it's talking about.
2. Start a long task, step away from the screen, and hear the summary when Claude finishes.
3. Rest your eyes and listen to a long explanation instead of reading it.

## What it reads

The whole reply, cleaned up for listening. Each code block is read as "Code omitted." Tables and web addresses are skipped, link text is kept, and a closing "Sources:" list is dropped.

## Choose the voice

Earshot uses your Mac's system voice. Change it in System Settings → Accessibility → Spoken Content → System voice. The Siri voices usually sound the most natural; Manage Voices downloads more.

## Privacy

Earshot runs on your Mac and makes no network connections of its own. After each reply it passes the text to macOS `say` through a pipe. It never writes replies to disk or logs them. The only files it keeps are an on/off switch and the process ID of the `say` that is speaking, both in the plugin's data folder, which Claude Code deletes when you uninstall the plugin.

Replies are spoken out loud, so people near you can hear them.

## How it works

Everything is in one shell script, [`scripts/earshot.sh`](scripts/earshot.sh), run by two hooks:

- **Stop**, after each reply: if Earshot is on, it reads the reply from the hook input, strips the markdown, and starts `say` in the background.
- **UserPromptSubmit**, when you send a message: it stops that `say`.

It uses only tools that ship with macOS: `sh`, `plutil`, `sed`, `awk`, `ps` and `say`.

## Troubleshooting

- Nothing is spoken: run `/earshot:on` again, then check your Mac's output device and volume. In Terminal, `say hello` should speak.
- It sounds robotic: choose a Siri voice in System Settings, as above.
- Two sessions are open: a new reply in either one interrupts the reply being read.

## Development

The tests run the script the way Claude Code does, with a fake `say`:

```
python3 -m unittest discover -s tests -v
```

## Support

Report problems at [github.com/stasliw/earshot/issues](https://github.com/stasliw/earshot/issues).

## License

MIT. See [LICENSE](LICENSE).
