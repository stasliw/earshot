---
name: off
description: Turn Replycast off, so Claude's replies are no longer read aloud.
disable-model-invocation: true
allowed-tools: Bash(/bin/sh ${CLAUDE_PLUGIN_ROOT}/scripts/replycast.sh *)
---

Run this one command with Bash, and nothing else:

/bin/sh "${CLAUDE_PLUGIN_ROOT}/scripts/replycast.sh" off "${CLAUDE_PLUGIN_DATA}"

Then reply with the line it printed, word for word, and nothing more.
