---
name: on
description: Turn Replycast on, so every Claude reply is read aloud in the Mac's system voice.
disable-model-invocation: true
allowed-tools: Bash(/bin/sh ${CLAUDE_PLUGIN_ROOT}/scripts/replycast.sh *)
---

Run this one command with Bash, and nothing else:

/bin/sh "${CLAUDE_PLUGIN_ROOT}/scripts/replycast.sh" on "${CLAUDE_PLUGIN_DATA}"

Then reply with the line it printed, word for word, and nothing more.
