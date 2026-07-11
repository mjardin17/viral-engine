"""
empire_runner.py — Empire OS Command Runner
============================================
Claude writes a command to _pending_cmd.txt.
This window shows it and lets Josh run it with one click.
Output is saved to _cmd_output.txt so Claude can read results.

Run once, leave open. It watches for new commands automatically.
"""

import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from datetime import datetime

BASE_DIR    = Path(__file__).parent
CMD_FILE    = BASE_DIR / "_pending_cmd.txt"
OUTPUT_FILE = BASE_DIR / "_cmd_output.txt"
DONE_FILE   = BASE_DIR / "_cmd_done.txt"
POLL_MS     = 1000  # check for new command every second


class EmpireRunner(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Empire OS Runner")
        self.geometry("720x500")
        self.configure(bg="#0d0d0d")
        self.resizable(True, True)

        self._current_cmd: str = ""
        self._running: bool = False

        self._build_ui()
        self._poll()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = tk.Label(
            self, text="EMPIRE OS  ·  Command Runner",
            bg="#0d0d0d", fg="#f0a500",
            font=("Consolas", 13, "bold"), pady=8
        )
        hdr.pack(fill=tk.X)

        # Status badge
        self.status_var = tk.StringVar(value="Waiting for command...")
        self.status_lbl = tk.Label(
            self, textvariable=self.status_var,
            bg="#0d0d0d", fg="#888888",
            font=("Consolas", 10)
        )
        self.status_lbl.pack()

        # Command box
        cmd_frame = tk.Frame(self, bg="#1a1a1a", bd=1, relief=tk.SOLID)
        cmd_frame.pack(fill=tk.X, padx=12, pady=(8, 4))

        tk.Label(cmd_frame, text="COMMAND", bg="#1a1a1a", fg="#f0a500",
                 font=("Consolas", 9, "bold"), padx=8, pady=4).pack(anchor="w")

        self.cmd_text = tk.Text(
            cmd_frame, height=4, bg="#0d0d0d", fg="#00ff88",
            font=("Consolas", 11), padx=8, pady=6,
            insertbackground="#00ff88", relief=tk.FLAT, wrap=tk.WORD
        )
        self.cmd_text.pack(fill=tk.X)
        self.cmd_text.insert("1.0", "No command queued yet.")
        self.cmd_text.config(state=tk.DISABLED)

        # RUN button
        self.run_btn = tk.Button(
            self,
            text="▶  RUN",
            command=self._run_command,
            bg="#1a6e2e", fg="white",
            font=("Consolas", 14, "bold"),
            activebackground="#22a040",
            relief=tk.FLAT, padx=20, pady=10,
            state=tk.DISABLED, cursor="arrow"
        )
        self.run_btn.pack(pady=8)

        # Output box
        out_frame = tk.Frame(self, bg="#1a1a1a", bd=1, relief=tk.SOLID)
        out_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        tk.Label(out_frame, text="OUTPUT", bg="#1a1a1a", fg="#888888",
                 font=("Consolas", 9, "bold"), padx=8, pady=4).pack(anchor="w")

        scroll = tk.Scrollbar(out_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.output_text = tk.Text(
            out_frame, bg="#0d0d0d", fg="#cccccc",
            font=("Consolas", 10), padx=8, pady=6,
            yscrollcommand=scroll.set, relief=tk.FLAT, state=tk.DISABLED
        )
        self.output_text.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=self.output_text.yview)

        # Tag colors
        self.output_text.tag_config("ok",    foreground="#00ff88")
        self.output_text.tag_config("error", foreground="#ff4444")
        self.output_text.tag_config("info",  foreground="#888888")

    # ── Command polling ───────────────────────────────────────────────────────

    def _poll(self):
        """Check _pending_cmd.txt every second for a new command."""
        if not self._running:
            try:
                if CMD_FILE.exists():
                    cmd = CMD_FILE.read_text(encoding="utf-8").strip()
                    if cmd and cmd != self._current_cmd:
                        self._load_command(cmd)
            except Exception:
                pass
        self.after(POLL_MS, self._poll)

    def _load_command(self, cmd: str):
        self._current_cmd = cmd
        self.cmd_text.config(state=tk.NORMAL)
        self.cmd_text.delete("1.0", tk.END)
        self.cmd_text.insert("1.0", cmd)
        self.cmd_text.config(state=tk.DISABLED)

        self.run_btn.config(state=tk.NORMAL, bg="#1a6e2e", cursor="hand2")
        self.status_var.set("Command ready — click RUN")
        self.status_lbl.config(fg="#f0a500")
        self.lift()
        self.focus_force()
        self._log(f"New command loaded at {datetime.now().strftime('%H:%M:%S')}", "info")

    # ── Execution ─────────────────────────────────────────────────────────────

    def _run_command(self):
        if not self._current_cmd or self._running:
            return
        self._running = True
        self.run_btn.config(state=tk.DISABLED, bg="#444444", cursor="arrow")
        self.status_var.set("Running...")
        self.status_lbl.config(fg="#f0a500")
        threading.Thread(target=self._execute, daemon=True).start()

    def _execute(self):
        cmd = self._current_cmd
        self._log(f"\n$ {cmd}", "info")
        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=3600,  # 1 hour max
                encoding="utf-8",
                errors="replace"
            )
            elapsed = time.time() - start
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if stdout:
                self._log(stdout, "ok")
            if stderr:
                self._log(stderr, "error")

            tag = "ok" if result.returncode == 0 else "error"
            self._log(f"\n[Exit {result.returncode} in {elapsed:.1f}s]", tag)

            # Write output for Claude to read
            output_text = f"EXIT: {result.returncode}\n{stdout}\n{stderr}".strip()
            OUTPUT_FILE.write_text(output_text, encoding="utf-8")
            DONE_FILE.write_text(str(result.returncode), encoding="utf-8")

            # Clear the pending command so we don't re-run
            CMD_FILE.unlink(missing_ok=True)
            self._current_cmd = ""

            status = "Done." if result.returncode == 0 else f"Failed (exit {result.returncode})."
            self.after(0, lambda: self.status_var.set(status))
            self.after(0, lambda: self.status_lbl.config(fg="#00ff88" if result.returncode == 0 else "#ff4444"))

        except subprocess.TimeoutExpired:
            self._log("\n[TIMEOUT — killed after 1 hour]", "error")
            OUTPUT_FILE.write_text("TIMEOUT", encoding="utf-8")
        except Exception as e:
            self._log(f"\n[ERROR] {e}", "error")
            OUTPUT_FILE.write_text(f"ERROR: {e}", encoding="utf-8")
        finally:
            self._running = False
            self.after(0, lambda: self.run_btn.config(
                state=tk.NORMAL, bg="#1a4a8e", cursor="hand2"
            ))

    def _log(self, text: str, tag: str = ""):
        def _do():
            self.output_text.config(state=tk.NORMAL)
            self.output_text.insert(tk.END, text + "\n", tag)
            self.output_text.see(tk.END)
            self.output_text.config(state=tk.DISABLED)
        self.after(0, _do)


if __name__ == "__main__":
    app = EmpireRunner()
    app.mainloop()
