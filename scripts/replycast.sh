#!/bin/sh
# Replycast: read Claude's replies aloud with the macOS `say` command.
#
#   replycast.sh stop               Stop hook. Reads the hook JSON on stdin and
#                                   speaks the reply when Replycast is on.
#   replycast.sh hush               UserPromptSubmit hook. Stops a reply that is
#                                   still being read.
#   replycast.sh on|off [DATA_DIR]  The /replycast:on and /replycast:off skills.
#   replycast.sh status [DATA_DIR]
#   replycast.sh clean              Markdown on stdin, speakable text on stdout.
#
# `say` runs without a voice name, so it uses the system voice chosen in
# System Settings > Accessibility > Spoken Content.
#
# The reply reaches `say` through a pipe. Nothing is written to disk except
# the on/off flag and the process id of the `say` that is speaking.

DATA_DIR=$CLAUDE_PLUGIN_DATA
if [ -n "$2" ]; then
	DATA_DIR=$2
fi

# Turn a markdown reply into plain text that reads well aloud. Code blocks
# become one spoken marker, tables and a closing "Sources:" list are dropped,
# links keep their text, and markup characters go.
clean() {
	awk '
		/<!--/ && !/-->/ { incomment = 1; next }
		incomment { if (/-->/) incomment = 0; next }
		{ gsub(/<!--.*-->/, "") }
		/^[ \t]*(```|~~~)/ { if (!infence) print "Code omitted."; infence = !infence; next }
		infence { next }
		/^[ \t]*\|/ { next }
		/^[ \t]*[-*_][ \t]*[-*_][ \t]*[-*_][-*_ \t]*$/ { next }
		/^[ \t]*(\*\*)?[Ss]ources:?(\*\*)?[ \t]*$/ { exit }
		{ print }
	' | sed -E \
		-e 's/!\[[^]]*\]\([^)]*\)//g' \
		-e 's/\[([^]]+)\]\([^)]*\)/\1/g' \
		-e 's#https?://[^[:space:]]+##g' \
		-e 's/`([^`]*)`/\1/g' \
		-e 's/^[[:space:]]*#+[[:space:]]+//' \
		-e 's/^[[:space:]]*>[[:space:]]?//' \
		-e 's/^[[:space:]]*([-*+]|[0-9]+[.)])[[:space:]]+//' \
		-e 's/(\*\*|__)([^*_]+)(\*\*|__)/\2/g' \
		-e 's/\*//g' \
		-e 's/→/ to /g' |
		awk '
		{ gsub(/[ \t]+/, " "); sub(/^ /, ""); sub(/ $/, "") }
		$0 == "" { next }
		$0 !~ /[.!?:;]$/ { $0 = $0 "." }
		$0 == "Code omitted." && last == $0 { next }
		{ print; last = $0 }
	'
}

# Stop the reply being read, if one is. Only kills the `say` Replycast started.
hush() {
	[ -n "$DATA_DIR" ] || return 0
	pidfile="$DATA_DIR/say.pid"
	[ -f "$pidfile" ] || return 0
	pid=$(cat "$pidfile")
	rm -f "$pidfile"
	case $pid in '' | *[!0-9]*) return 0 ;; esac
	case $(ps -p "$pid" -o args= 2>/dev/null) in
	*"say -f -"*) kill "$pid" 2>/dev/null ;;
	esac
	return 0
}

# Stop hook: speak the reply that just finished, when Replycast is on.
speak_reply() {
	if [ -z "$DATA_DIR" ] || [ ! -f "$DATA_DIR/on" ] || ! command -v say >/dev/null 2>&1; then
		cat >/dev/null
		return 0
	fi
	reply=$(plutil -extract last_assistant_message raw -expect string -o - - 2>/dev/null) || return 0
	text=$(printf '%s\n' "$reply" | clean)
	[ -n "$text" ] || return 0
	hush
	# Job control puts `say` in its own process group, so it keeps speaking
	# after this hook exits.
	set -m
	printf '%s\n' "$text" | say -f - >/dev/null 2>&1 &
	echo $! >"$DATA_DIR/say.pid"
}

case $1 in
stop) speak_reply ;;
hush)
	cat >/dev/null
	hush
	;;
clean) clean ;;
on)
	if [ -z "$DATA_DIR" ]; then
		echo "Replycast couldn't find its data folder."
	elif ! command -v say >/dev/null 2>&1; then
		echo "Replycast needs macOS: the say command wasn't found."
	else
		mkdir -p "$DATA_DIR" && : >"$DATA_DIR/on"
		echo "Replycast is on. Replies will be read aloud."
	fi
	;;
off)
	if [ -n "$DATA_DIR" ]; then
		rm -f "$DATA_DIR/on"
	fi
	hush
	echo "Replycast is off."
	;;
status)
	if [ -n "$DATA_DIR" ] && [ -f "$DATA_DIR/on" ]; then
		echo "Replycast is on."
	else
		echo "Replycast is off."
	fi
	;;
*) echo "Usage: replycast.sh stop|hush|on|off|status|clean [DATA_DIR]" ;;
esac
exit 0
