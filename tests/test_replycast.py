"""Tests for scripts/replycast.sh. Run from the repository root:

    python3 -m unittest discover -s tests -v

The hook tests run replycast.sh the way Claude Code does, with a fake `say`
first on PATH that writes what it receives on stdin to a file. Each run gets a
small, explicit environment, never the caller's.
"""

import json
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "replycast.sh"
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"

FAKE_SAY = """#!/bin/sh
[ "$1" = "-f" ] && [ "$2" = "-" ] || exit 2
cat > "$REPLYCAST_TEST_OUT"
sleep "${REPLYCAST_TEST_SLEEP:-0}"
"""


def wait_for(check, seconds=3.0):
    end = time.time() + seconds
    while time.time() < end:
        if check():
            return True
        time.sleep(0.05)
    return False


def running(pid):
    ps = ["/bin/ps", "-p", str(pid), "-o", "stat="]
    out = subprocess.run(ps, check=False, capture_output=True, text=True).stdout.strip()
    return bool(out) and not out.startswith("Z")


def clean(markdown):
    return subprocess.run(
        ["/bin/sh", str(SCRIPT), "clean"],
        input=markdown,
        capture_output=True,
        text=True,
        env={"PATH": SYSTEM_PATH},
        check=True,
    ).stdout.rstrip("\n")


class CleanTest(unittest.TestCase):
    def test_full_reply_keeps_prose_and_drops_markup(self):
        reply = (
            "Yes, it's **feasible**. See [the hooks docs](https://docs.test/hooks) and `say`.\n"
            "\n"
            "## How it would work\n"
            "- A Stop hook runs → the script speaks\n"
            "1. Toggle with *one* command\n"
            "> quoted line\n"
            "\n"
            "```bash\n"
            'say -v Daniel "hi"\n'
            "```\n"
            "| a | b |\n"
            "|---|---|\n"
            "---\n"
            "Raw link https://docs.test/x here.\n"
            "<!-- reply 1 -->\n"
            "\n"
            "Sources:\n"
            "- [Docs](https://docs.test)\n"
        )
        self.assertEqual(
            clean(reply),
            "Yes, it's feasible. See the hooks docs and say.\n"
            "How it would work.\n"
            "A Stop hook runs to the script speaks.\n"
            "Toggle with one command.\n"
            "quoted line.\n"
            "Code omitted.\n"
            "Raw link here.",
        )

    def test_code_blocks_in_a_row_read_as_one_marker(self):
        self.assertEqual(
            clean("Run these:\n\n```bash\na\n```\n\n~~~\nb\n~~~\n\nDone."), "Run these:\nCode omitted.\nDone."
        )

    def test_snake_case_names_survive(self):
        self.assertEqual(clean("Edit last_assistant_message now"), "Edit last_assistant_message now.")

    def test_bold_sources_heading_ends_the_reading(self):
        self.assertEqual(clean("Done.\n\n**Sources:**\n- [a](https://a.test)"), "Done.")

    def test_multiline_html_comment_is_skipped(self):
        self.assertEqual(clean("<!--\nhidden\n-->\nShown"), "Shown.")

    def test_blank_reply_gives_nothing(self):
        self.assertEqual(clean("   \n\n<!-- reply 1 -->"), "")


class HookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        self.data = tmp / "data"
        self.out = tmp / "spoken.txt"
        fake_bin = tmp / "bin"
        fake_bin.mkdir()
        fake = fake_bin / "say"
        fake.write_text(FAKE_SAY)
        fake.chmod(0o755)
        self.env = {
            "PATH": f"{fake_bin}:{SYSTEM_PATH}",
            "CLAUDE_PLUGIN_DATA": str(self.data),
            "REPLYCAST_TEST_OUT": str(self.out),
        }

    def tearDown(self):
        self.run_script("off")
        self.tmp.cleanup()

    def run_script(self, *args, stdin="", **env):
        result = subprocess.run(
            ["/bin/sh", str(SCRIPT), *args],
            check=False,
            input=stdin,
            capture_output=True,
            text=True,
            env={**self.env, **env},
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def stop(self, payload, **env):
        return self.run_script("stop", stdin=payload if isinstance(payload, str) else json.dumps(payload), **env)

    def test_silent_when_off(self):
        self.stop({"last_assistant_message": "Hello there."})
        self.assertFalse(wait_for(self.out.exists, 0.5))

    def test_speaks_cleaned_reply_when_on(self):
        self.run_script("on")
        self.stop({"last_assistant_message": "Done. See `replycast.sh`.\n\n```\nx\n```"})
        self.assertTrue(wait_for(lambda: self.out.exists() and self.out.read_text()))
        self.assertEqual(self.out.read_text(), "Done. See replycast.sh.\nCode omitted.\n")

    def test_reply_text_is_never_written_to_disk(self):
        self.run_script("on")
        self.stop({"last_assistant_message": "A private reply."}, REPLYCAST_TEST_SLEEP="5")
        self.assertTrue(wait_for(self.out.exists))
        self.assertEqual(sorted(p.name for p in self.data.iterdir()), ["on", "say.pid"])

    def test_ignores_payloads_without_a_reply(self):
        self.run_script("on")
        for payload in ["", "not json", "[]", {}, {"last_assistant_message": ""}, {"last_assistant_message": ["x"]}]:
            self.stop(payload)
        self.assertFalse(wait_for(self.out.exists, 0.5))

    def test_next_prompt_stops_the_reading(self):
        self.run_script("on")
        self.stop({"last_assistant_message": "A long reply."}, REPLYCAST_TEST_SLEEP="30")
        pid = int((self.data / "say.pid").read_text())
        self.assertTrue(wait_for(lambda: running(pid)))
        self.run_script("hush")
        self.assertTrue(wait_for(lambda: not running(pid)), "say kept running after hush")

    def test_hush_leaves_other_processes_alone(self):
        other = subprocess.Popen(["/bin/sleep", "30"])
        try:
            self.data.mkdir(parents=True)
            (self.data / "say.pid").write_text(str(other.pid))
            self.run_script("hush")
            self.assertIsNone(other.poll())
        finally:
            other.kill()
            other.wait()

    def test_on_off_status(self):
        self.assertEqual(self.run_script("status"), "Replycast is off.")
        self.assertEqual(self.run_script("on"), "Replycast is on. Replies will be read aloud.")
        self.assertEqual(self.run_script("status"), "Replycast is on.")
        self.assertEqual(self.run_script("off"), "Replycast is off.")
        self.assertEqual(self.run_script("status"), "Replycast is off.")

    def test_data_folder_passed_as_argument(self):
        other = Path(self.tmp.name) / "from-skill"
        self.assertEqual(self.run_script("on", str(other)), "Replycast is on. Replies will be read aloud.")
        self.assertTrue((other / "on").exists())

    def test_on_refuses_without_say(self):
        self.assertEqual(self.run_script("on", PATH="/bin"), "Replycast needs macOS: the say command wasn't found.")
        self.assertFalse((self.data / "on").exists())

    def test_on_refuses_without_data_folder(self):
        self.assertEqual(self.run_script("on", CLAUDE_PLUGIN_DATA=""), "Replycast couldn't find its data folder.")


if __name__ == "__main__":
    unittest.main()
