---
name: off
description: Turn Earshot off, so Claude's replies are no longer read aloud.
disable-model-invocation: true
allowed-tools: Bash(/bin/sh ${CLAUDE_PLUGIN_ROOT}/scripts/earshot.sh *)
---

Run this one command with Bash, and nothing else:

/bin/sh "${CLAUDE_PLUGIN_ROOT}/scripts/earshot.sh" off "${CLAUDE_PLUGIN_DATA}"

Then reply with the line it printed, word for word, and nothing more.
