"""
语音转文字工具 - GUI v0.0.2
双击运行，调用 py -3.12 + pipeline.py
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
import subprocess, os, sys, json, threading, time

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    TOOL_DIR = os.path.dirname(sys.executable)
PIPELINE = os.path.join(TOOL_DIR, "pipeline.py")
PY_EXE = "py"
PY_ARGS = ["-3.12"]

PLACEHOLDER = "拖拽音频/视频文件或输入路径"


class TranscriberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("语音转文字工具 v0.0.2")
        self.root.minsize(680, 500)
        self.root.configure(bg="#f0f0f0")
        self.running = False
        self.proc = None
        self.file_list = []

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        w, h = 720, 540
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.build_ui()

    def build_ui(self):
        main = tk.Frame(self.root, bg="#f0f0f0")
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        # 上半：左右
        top = tk.Frame(main, bg="white")
        top.pack(fill=tk.BOTH, expand=True)

        # 左侧
        left = tk.Frame(top, bg="white", padx=16, pady=12)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="文件路径：", bg="white", font=("微软雅黑", 10)).pack(anchor="w")
        f1 = tk.Frame(left, bg="white")
        f1.pack(fill=tk.X, pady=(2, 2))
        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(f1, textvariable=self.input_var, font=("微软雅黑", 9),
                                     relief="solid", bd=1, fg="gray")
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        self.input_entry.insert(0, PLACEHOLDER)
        self.input_entry.bind("<FocusIn>", lambda e: self._clear_placeholder())
        self.input_entry.bind("<FocusOut>", lambda e: self._restore_placeholder())
        self.input_entry.drop_target_register(DND_FILES)
        self.input_entry.dnd_bind("<<Drop>>", self._on_drop)
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind("<<Drop>>", self._on_drop)
        tk.Button(f1, text="浏览", bg="#e8e8e8", relief="flat", padx=12,
                  font=("微软雅黑", 9), command=self.browse_input).pack(side=tk.LEFT, padx=(6, 0))

        # 文件列表（多文件时显示）
        self.file_list_frame = tk.Frame(left, bg="white")
        self.file_list_text = tk.Text(self.file_list_frame, height=3, font=("Consolas", 8),
                                       bg="#fafafa", relief="solid", bd=1, wrap=tk.NONE)
        fl_scroll = tk.Scrollbar(self.file_list_frame, orient=tk.HORIZONTAL,
                                  command=self.file_list_text.xview)
        self.file_list_text.configure(xscrollcommand=fl_scroll.set)
        self.file_list_text.pack(fill=tk.X)
        fl_scroll.pack(fill=tk.X)

        tk.Label(left, text="输出目录：", bg="white", font=("微软雅黑", 10)).pack(anchor="w", pady=(8, 0))
        f2 = tk.Frame(left, bg="white")
        f2.pack(fill=tk.X, pady=(2, 0))
        self.output_var = tk.StringVar(value="默认：输入文件同目录")
        self.output_entry = tk.Entry(f2, textvariable=self.output_var, font=("微软雅黑", 9),
                                      relief="solid", bd=1, fg="gray")
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        tk.Button(f2, text="浏览", bg="#e8e8e8", relief="flat", padx=12,
                  font=("微软雅黑", 9), command=self.browse_output).pack(side=tk.LEFT, padx=(6, 0))

        # 右侧
        rf = tk.Frame(top, bg="white", padx=0, pady=12)
        rf.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(0, 12))
        right = tk.LabelFrame(rf, text="转写选项", bg="white", font=("微软雅黑", 10, "bold"),
                               fg="#333", padx=16, pady=10, relief="groove", bd=1)
        right.pack(fill=tk.BOTH, expand=True)

        tk.Label(right, text="转写语言：", bg="white", font=("微软雅黑", 10)).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.lang_var = tk.StringVar(value="自动检测")
        ttk.Combobox(right, textvariable=self.lang_var, values=["自动检测", "中文", "英语", "日语"],
                     state="readonly", font=("微软雅黑", 9), width=12).grid(row=0, column=1, sticky="w", pady=(0, 8))

        tk.Label(right, text="输出格式：", bg="white", font=("微软雅黑", 10)).grid(row=1, column=0, sticky="w")
        ff = tk.Frame(right, bg="white")
        ff.grid(row=1, column=1, sticky="w", pady=(0, 8))
        self.fmt_var = tk.StringVar(value="TXT")
        tk.Radiobutton(ff, text="SRT", variable=self.fmt_var, value="SRT", bg="white", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        tk.Radiobutton(ff, text="TXT", variable=self.fmt_var, value="TXT", bg="white", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(16, 0))

        tk.Label(right, text="区分对话人：", bg="white", font=("微软雅黑", 10)).grid(row=2, column=0, sticky="w")
        df = tk.Frame(right, bg="white")
        df.grid(row=2, column=1, sticky="w", pady=(0, 8))
        self.diar_var = tk.StringVar(value="否")
        tk.Radiobutton(df, text="是", variable=self.diar_var, value="是", bg="white", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        tk.Radiobutton(df, text="否", variable=self.diar_var, value="否", bg="white", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(16, 0))

        tk.Label(right, text="合并同对话人段落：", bg="white", font=("微软雅黑", 10)).grid(row=3, column=0, sticky="w")
        mf = tk.Frame(right, bg="white")
        mf.grid(row=3, column=1, sticky="w")
        self.merge_var = tk.StringVar(value="否")
        tk.Radiobutton(mf, text="是", variable=self.merge_var, value="是", bg="white", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        tk.Radiobutton(mf, text="否", variable=self.merge_var, value="否", bg="white", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(16, 0))

        tk.Label(right, text="添加标点：", bg="white", font=("微软雅黑", 10)).grid(row=4, column=0, sticky="w")
        pf = tk.Frame(right, bg="white")
        pf.grid(row=4, column=1, sticky="w")
        self.punct_var = tk.StringVar(value="是")
        tk.Radiobutton(pf, text="是", variable=self.punct_var, value="是", bg="white", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        tk.Radiobutton(pf, text="否", variable=self.punct_var, value="否", bg="white", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=(16, 0))

        # 底部
        bottom = tk.Frame(main, bg="#e8e8e8", padx=12, pady=10)
        bottom.pack(fill=tk.X, pady=(10, 0))

        # 按钮区：转写居中，取消靠右
        btn_frame = tk.Frame(bottom, bg="#e8e8e8")
        btn_frame.pack(fill=tk.X, pady=(0, 6))

        self.cancel_btn = tk.Button(btn_frame, text="取消", bg="#ff4d4f", fg="white",
                                     font=("微软雅黑", 10), relief="flat",
                                     padx=20, pady=4, activebackground="#d9363e",
                                     command=self.cancel)
        # 取消按钮初始隐藏，转写时显示在右侧

        self.btn = tk.Button(btn_frame, text="转写", bg="#1677ff", fg="white",
                              font=("微软雅黑", 12, "bold"), relief="flat",
                              padx=40, pady=6, activebackground="#0958d9",
                              command=self.start)
        self.btn.pack(expand=True)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(bottom, variable=self.progress_var, maximum=100, length=500)
        self.progress_bar.pack(fill=tk.X)

        self.status_var = tk.StringVar(value="就绪")
        tk.Label(bottom, textvariable=self.status_var, bg="#e8e8e8",
                 font=("微软雅黑", 8), fg="#666").pack(anchor="w")

        # 日志栏
        log_frame = tk.Frame(bottom, bg="#e8e8e8")
        log_frame.pack(fill=tk.X, pady=(4, 0))
        self.log_text = tk.Text(log_frame, height=5, font=("Consolas", 8),
                                 bg="#fafafa", relief="solid", bd=1, wrap=tk.WORD)
        sb = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=sb.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.insert("1.0", "就绪，等待操作...\n")

    def _clear_placeholder(self):
        if self.input_var.get() == PLACEHOLDER:
            self.input_var.set("")
            self.input_entry.config(fg="black")

    def _restore_placeholder(self):
        if not self.input_var.get().strip() and not self.file_list:
            self.input_var.set(PLACEHOLDER)
            self.input_entry.config(fg="gray")

    def _update_file_display(self):
        if len(self.file_list) <= 1:
            self.file_list_frame.pack_forget()
            if self.file_list:
                self.input_var.set(self.file_list[0])
                self.input_entry.config(fg="black")
        else:
            self.file_list_frame.pack(fill=tk.X, after=self.input_entry.master, pady=(2, 0))
            self.input_var.set(f"已选择 {len(self.file_list)} 个文件")
            self.input_entry.config(fg="black")
            self.file_list_text.delete("1.0", "end")
            for i, f in enumerate(self.file_list, 1):
                self.file_list_text.insert("end", f"{i}. {os.path.basename(f)}\n")
            self.file_list_text.config(state="disabled")

    def browse_input(self):
        paths = filedialog.askopenfilenames(
            title="选择音频/视频文件（可多选）",
            filetypes=[("音视频文件", "*.m4a *.mp3 *.wav *.aac *.ogg *.flac *.mp4 *.avi *.mov *.mkv *.wmv *.webm"),
                       ("所有文件", "*.*")]
        )
        if paths:
            self.file_list = list(paths)
            self._update_file_display()

    def browse_output(self):
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.output_var.set(path)

    def _on_drop(self, event):
        raw = event.data.strip()
        # tkinterdnd2 多文件拖拽格式：{path1} {path2} ...
        paths = []
        brace = False
        buf = ""
        for ch in raw:
            if ch == "{":
                brace = True
                buf = ""
            elif ch == "}":
                brace = False
                if buf:
                    paths.append(buf)
                buf = ""
            elif brace:
                buf += ch
            elif ch == " ":
                if buf:
                    paths.append(buf)
                    buf = ""
            else:
                buf += ch
        if buf:
            paths.append(buf)
        if not paths:
            return
        self.file_list = paths
        self._update_file_display()

    def _resolve_output_dir(self, inp):
        out = self.output_var.get().strip()
        if out and not out.startswith("默认"):
            return out
        parent = os.path.dirname(os.path.abspath(inp))
        # 根目录回退到桌面
        if os.path.splitdrive(parent)[1] in ("\\", "/", ""):
            parent = os.path.join(os.path.expanduser("~"), "Desktop")
        return parent

    def start(self):
        if not self.file_list:
            inp = self.input_var.get().strip()
            if not inp or inp == PLACEHOLDER:
                messagebox.showwarning("提示", "请先选择音频/视频文件")
                return
            if not os.path.exists(inp):
                messagebox.showerror("错误", f"文件不存在：\n{inp}")
                return
            self.file_list = [inp]

        # 校验所有文件存在
        for f in self.file_list:
            if not os.path.exists(f):
                messagebox.showerror("错误", f"文件不存在：\n{f}")
                return

        lang = {"自动检测": "auto", "中文": "zh", "英语": "en", "日语": "ja"}[self.lang_var.get()]
        fmt = self.fmt_var.get().lower()
        diar = self.diar_var.get() == "是"
        merge = self.merge_var.get() == "是"
        punct = self.punct_var.get() == "是"

        self.running = True
        self.proc = None
        self.btn.config(state="disabled", text="转写中...")
        self.cancel_btn.pack(side=tk.RIGHT, padx=(0, 20))
        self.progress_var.set(0)
        self.status_var.set("启动...")

        thread = threading.Thread(target=self._run, args=(lang, fmt, diar, merge, punct), daemon=True)
        thread.start()

    def _run(self, lang, fmt, diar, merge, punct):
        total = len(self.file_list)
        results = []
        for idx, inp in enumerate(self.file_list):
            if not self.running:
                return
            out = self._resolve_output_dir(inp)
            self.root.after(0, self._set_status,
                            f"[{idx + 1}/{total}] 处理中: {os.path.basename(inp)}")

            cmd = list(PY_ARGS) + [PIPELINE, inp, "--output-dir", out,
                                    "--lang", lang, "--format", fmt]
            if diar:
                cmd.append("--diarize")
            if merge:
                cmd.append("--merge")
            if punct:
                cmd.append("--punctuate")

            try:
                self.proc = subprocess.Popen([PY_EXE] + cmd, stdout=subprocess.PIPE,
                                              stderr=subprocess.DEVNULL, text=True,
                                              encoding="utf-8", errors="replace")
                last_ui = 0
                for line in self.proc.stdout:
                    if not self.running:
                        self.proc.terminate()
                        return
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                        now = time.time()
                        if now - last_ui > 0.25:
                            status = d.get("status", "")
                            if total > 1:
                                status = f"[{idx + 1}/{total}] {status}"
                            self.root.after(0, self._set_status, status)
                            last_ui = now
                        if "progress" in d:
                            # 总体进度 = 已完文件进度 + 当前文件内部进度
                            base = int(idx / total * 100)
                            file_pct = int(d["progress"] / total)
                            self.root.after(0, self._set_progress, base + file_pct)
                        if d.get("status") == "done":
                            results.append(d.get("output", ""))
                            self.root.after(0, self._set_progress, int((idx + 1) / total * 100))
                            break
                        if d.get("status") == "error":
                            self.root.after(0, self._set_status,
                                            f"[{idx + 1}/{total}] 出错: {d.get('message', '未知错误')[:60]}")
                            break
                    except json.JSONDecodeError:
                        pass
                self.proc.wait()
            except Exception as e:
                self.root.after(0, self._set_status, f"[{idx + 1}/{total}] 异常: {str(e)[:60]}")
                continue

        if self.running:
            self.root.after(0, self._done, results)

    def _set_status(self, text):
        self.status_var.set(text)
        self.log_text.insert("end", f"{text}\n")
        self.log_text.see("end")

    def _set_progress(self, pct):
        self.progress_var.set(pct)

    def _done(self, results):
        self.running = False
        self.proc = None
        self.btn.config(state="normal", text="转写")
        self.cancel_btn.pack_forget()
        self.status_var.set("完成")
        self.progress_var.set(100)
        self.file_list = []
        self._update_file_display()
        if len(results) == 1:
            path = results[0]
            msg = f"转写完成！\n\n{path}"
        else:
            msg = f"全部转写完成！共处理 {len(results)} 个文件"
            path = results[0] if results else ""
        messagebox.showinfo("完成", msg)
        if path and os.path.exists(os.path.dirname(path)):
            os.startfile(os.path.dirname(path))

    def _err(self, msg):
        self.running = False
        self.proc = None
        self.btn.config(state="normal", text="转写")
        self.cancel_btn.pack_forget()
        self.status_var.set("出错")
        messagebox.showerror("错误", msg)

    def cancel(self):
        if not self.running:
            return
        self.running = False
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.btn.config(state="normal", text="转写")
        self.cancel_btn.pack_forget()
        self.status_var.set("已取消")
        self.file_list = []
        self._update_file_display()
        self._set_status("用户取消转写")

    def _on_close(self):
        if self.running and self.proc and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        self.root.destroy()


if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = TranscriberApp(root)
    root.mainloop()
