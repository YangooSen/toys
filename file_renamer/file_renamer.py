# -*- coding: utf-8 -*-
"""
文件名自动整理工具
按清单顺序自动识别文件内容并重命名。
规则：每行一个清单项，格式：名称|关键词1,关键词2（不写关键词则用名称本身匹配）
重命名结果：序号.名称A / 序号.名称B（同一项多个文件用 A、B、C 区分）
"""
import os
import re
import sys
import json
import zipfile
import traceback

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ---------- 配置保存路径（exe 或脚本同目录） ----------
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "匹配规则.txt")

DEFAULT_RULES = """公司资质|资质,营业执照,许可证
派遣函|派遣函
说明书|说明书,使用说明"""

PDF_EXTS = {".pdf"}
WORD_EXTS = {".docx", ".doc"}

# ---------- 文本提取 ----------

def extract_text_pdf(path):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("缺少 pypdf 库，请先执行：pip install pypdf")
    reader = PdfReader(path)
    pages = []
    for i, page in enumerate(reader.pages):
        if i >= 10:  # 只看前 10 页，够用且快
            break
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pass
    return "\n".join(pages)


def extract_text_docx(path):
    """docx 就是 zip 包，直接读 word/document.xml，不需要额外依赖"""
    try:
        with zipfile.ZipFile(path) as z:
            with z.open("word/document.xml") as f:
                xml = f.read().decode("utf-8", errors="ignore")
        # 去掉标签，只留文字；段尾标签换成换行
        text = re.sub(r"</w:p>", "\n", xml)
        text = re.sub(r"<[^>]+>", "", text)
        return text
    except Exception:
        return ""


def extract_text_doc(path):
    """老版 .doc 二进制格式，尽力而为：用 utf-16 和 gbk 各扫一遍"""
    try:
        with open(path, "rb") as f:
            data = f.read(2 * 1024 * 1024)  # 最多读 2MB
        parts = []
        try:
            parts.append(data.decode("utf-16-le", errors="ignore"))
        except Exception:
            pass
        try:
            parts.append(data.decode("gbk", errors="ignore"))
        except Exception:
            pass
        return "\n".join(parts)
    except Exception:
        return ""


def extract_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in PDF_EXTS:
        return extract_text_pdf(path)
    if ext == ".docx":
        return extract_text_docx(path)
    if ext == ".doc":
        return extract_text_doc(path)
    return ""


# ---------- 规则与匹配 ----------

def parse_rules(text):
    """每行：名称|关键词1,关键词2；不写 | 则名称即关键词。行号即清单序号。"""
    rules = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            name, kw = line.split("|", 1)
            name = name.strip()
            kws = [k.strip() for k in kw.split(",") if k.strip()]
        else:
            name = line
            kws = [line]
        if name and kws:
            rules.append({"num": len(rules) + 1, "name": name, "keywords": kws})
    return rules


def list_files(folder):
    files = []
    for fn in sorted(os.listdir(folder)):
        if fn.startswith("~$") or fn.startswith("."):
            continue  # 跳过 Word 临时文件
        if os.path.splitext(fn)[1].lower() in (PDF_EXTS | WORD_EXTS):
            files.append(fn)
    return files


def match_files(folder, rules):
    """返回结果列表：[{file, new, status, reason}]"""
    results = []
    counters = {}  # 每条规则已分配的个数
    for fn in list_files(folder):
        path = os.path.join(folder, fn)
        new_name = None
        reason = ""
        try:
            text = extract_text(path)
        except Exception as e:
            text = ""
            reason = f"读取失败（{e}）"
        if text:
            for rule in rules:
                if any(kw in text for kw in rule["keywords"]):
                    counters[rule["num"]] = counters.get(rule["num"], 0) + 1
                    n = counters[rule["num"]]
                    letter = chr(ord("A") + n - 1) if n <= 26 else str(n)
                    stem, ext = os.path.splitext(fn)
                    new_name = f"{rule['num']}.{rule['name']}{letter}{ext}"
                    break
        if new_name is None:
            results.append({"file": fn, "new": "", "status": "未匹配",
                            "reason": reason or "内容中没有找到任何关键词"})
        else:
            results.append({"file": fn, "new": new_name, "status": "待重命名", "reason": ""})
    return results


def apply_renames(folder, results):
    """执行重命名，返回 (成功数, 失败列表, 跳过列表)"""
    ok, fails, skips = 0, [], []
    for r in results:
        if r["status"] != "待重命名":
            continue
        src = os.path.join(folder, r["file"])
        dst = os.path.join(folder, r["new"])
        if os.path.exists(dst) and not os.path.samefile(src, dst):
            # 目标名已被占用（比如重跑），加序号后缀
            stem, ext = os.path.splitext(r["new"])
            i = 1
            while os.path.exists(os.path.join(folder, f"{stem}_{i}{ext}")):
                i += 1
            dst = os.path.join(folder, f"{stem}_{i}{ext}")
        try:
            os.rename(src, dst)
            ok += 1
        except Exception as e:
            fails.append(f"{r['file']} -> {e}")
    return ok, fails, skips


# ---------- 界面 ----------

class App:
    def __init__(self, root):
        self.root = root
        self.folder = None
        self.results = []
        root.title("文件名自动整理工具")
        root.geometry("880x640")

        # 规则区
        top = ttk.LabelFrame(root, text="清单与关键词（每行一项，格式：名称|关键词1,关键词2；不写关键词则直接用名称匹配）")
        top.pack(fill="x", padx=10, pady=8)
        self.rules_text = tk.Text(top, height=6, font=("Microsoft YaHei", 11))
        self.rules_text.pack(fill="x", padx=8, pady=6)
        self.rules_text.insert("1.0", self.load_rules())

        # 文件夹区
        mid = ttk.Frame(root)
        mid.pack(fill="x", padx=10)
        ttk.Button(mid, text="选择文件夹", command=self.pick_folder).pack(side="left")
        self.folder_label = ttk.Label(mid, text="未选择文件夹", foreground="gray")
        self.folder_label.pack(side="left", padx=10)
        ttk.Button(mid, text="开始匹配", command=self.do_match).pack(side="right")

        # 结果区
        bottom = ttk.LabelFrame(root, text="匹配结果（确认前不会改名）")
        bottom.pack(fill="both", expand=True, padx=10, pady=8)
        cols = ("orig", "new", "status")
        self.tree = ttk.Treeview(bottom, columns=cols, show="headings")
        self.tree.heading("orig", text="原文件名")
        self.tree.heading("new", text="新文件名")
        self.tree.heading("status", text="状态")
        self.tree.column("orig", width=300)
        self.tree.column("new", width=300)
        self.tree.column("status", width=140)
        sb = ttk.Scrollbar(bottom, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.tag_configure("unmatched", foreground="red")
        self.tree.tag_configure("ready", foreground="green")

        # 底部按钮
        foot = ttk.Frame(root)
        foot.pack(fill="x", padx=10, pady=(0, 10))
        self.rename_btn = ttk.Button(foot, text="确认重命名", command=self.do_rename, state="disabled")
        self.rename_btn.pack(side="left")
        self.status = ttk.Label(foot, text="先填规则，选文件夹，点开始匹配", foreground="gray")
        self.status.pack(side="left", padx=10)

    def load_rules(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return DEFAULT_RULES

    def save_rules(self):
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(self.rules_text.get("1.0", "end"))
        except Exception:
            pass

    def pick_folder(self):
        folder = filedialog.askdirectory(title="选择要整理的文件夹")
        if folder:
            self.folder = folder
            n = len(list_files(folder))
            self.folder_label.config(text=f"{folder}（{n} 个 PDF/Word 文件）", foreground="black")

    def do_match(self):
        self.save_rules()
        if not self.folder:
            messagebox.showwarning("提示", "请先选择文件夹")
            return
        rules = parse_rules(self.rules_text.get("1.0", "end"))
        if not rules:
            messagebox.showwarning("提示", "请先填写清单规则")
            return
        self.status.config(text="正在识别文件内容，请稍候……", foreground="gray")
        self.root.update()
        try:
            self.results = match_files(self.folder, rules)
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("出错", f"匹配过程出错：{e}")
            return
        self.tree.delete(*self.tree.get_children())
        unmatched = 0
        for r in self.results:
            tag = "unmatched" if r["status"] == "未匹配" else "ready"
            self.tree.insert("", "end", values=(r["file"], r["new"] or "（保持原名）", r["status"]), tags=(tag,))
            if r["status"] == "未匹配":
                unmatched += 1
        ready = sum(1 for r in self.results if r["status"] == "待重命名")
        msg = f"共 {len(self.results)} 个文件：{ready} 个待重命名"
        if unmatched:
            msg += f"，{unmatched} 个未匹配（保持原名）"
            self.status.config(text=msg, foreground="red")
        else:
            self.status.config(text=msg, foreground="green")
        self.rename_btn.config(state="normal" if ready else "disabled")

    def do_rename(self):
        if not self.results:
            return
        if not messagebox.askyesno("确认", "确定按上面结果重命名吗？\n（未匹配的文件不会被改动）"):
            return
        ok, fails, _ = apply_renames(self.folder, self.results)
        msg = f"已重命名 {ok} 个文件。"
        if fails:
            msg += "\n失败：\n" + "\n".join(fails)
        messagebox.showinfo("完成", msg)
        self.status.config(text=f"已重命名 {ok} 个文件", foreground="green")
        self.rename_btn.config(state="disabled")
        # 刷新列表为最终状态
        self.tree.delete(*self.tree.get_children())
        for r in self.results:
            if r["status"] == "待重命名":
                self.tree.insert("", "end", values=(r["file"], r["new"], "已重命名"), tags=("ready",))
            else:
                self.tree.insert("", "end", values=(r["file"], "（保持原名）", r["status"]), tags=("unmatched",))


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
