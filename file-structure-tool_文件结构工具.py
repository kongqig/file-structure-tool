"""
文件夹结构工具 - 递归扫描并展示文件夹结构

终端版本用法:
    python files文件结构工具.py <路径> [选项]
    
    参数:
        <路径>              要扫描的文件夹路径（不填则启动GUI版本）
    
    选项:
        -o, --output <路径>  导出到文件
        -s, --style <数字>   路径样式 (0=当前文件夹开头, 1=点开头, 2=无开头, 3=绝对路径)
        -t, --tree          使用树形结构输出
        -i, --indent <字符>  树形结构缩进字符 (默认: 空格)
        -l, --length <数字>  树形结构缩进长度 (默认: 2)

示例:
    python files文件结构工具.py ./assets
    python files文件结构工具.py ./assets -o structure.txt
    python files文件结构工具.py ./assets -s 1 -o output.txt
    python files文件结构工具.py ./assets -t -i "-" -l 1
    python files文件结构工具.py              # 启动GUI版本

作者: AI Assistant
"""

import os
import sys
import argparse
import threading
from pathlib import Path
from typing import List, Tuple, Optional

try:
    import tkinter as tk
    from tkinter import filedialog, ttk
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False


def scan_directory(path: str, max_depth: int = 500) -> Tuple[List[str], int, int, List[str]]:
    """递归扫描文件夹（深度优先），返回所有文件和文件夹的相对路径，以及统计数
    
    Args:
        path: 要扫描的文件夹路径
        max_depth: 最大递归深度，超过此深度将停止递归（默认500）
    
    Returns:
        (路径列表, 文件数, 文件夹数, 跳过的目录列表)
    """
    result = []
    file_count = 0
    folder_count = 0
    skipped = []
    base_path = Path(path)
    
    if not base_path.exists():
        return result, 0, 0, skipped
    
    visited = set()
    visited.add(base_path.resolve())

    def walk_depth_first(current_path: Path, rel_prefix: str, depth: int):
        nonlocal file_count, folder_count
        
        if depth > max_depth:
            skipped.append(rel_prefix.rstrip(os.sep) + " (深度超限)")
            return
        
        try:
            items = os.listdir(current_path)
        except OSError as e:
            skipped.append(rel_prefix.rstrip(os.sep) + f" ({e})")
            return
        
        dirs = []
        files = []
        
        for item in items:
            item_path = current_path / item
            if item_path.is_dir():
                resolved = item_path.resolve()
                if resolved not in visited:
                    dirs.append(item)
                    visited.add(resolved)
            else:
                files.append(item)
        
        dirs.sort(key=str.lower)
        files.sort(key=str.lower)
        
        for d in dirs:
            rel_path = rel_prefix + d + os.sep
            result.append(rel_path)
            folder_count += 1
            walk_depth_first(current_path / d, rel_path, depth + 1)
        
        for f in files:
            rel_path = rel_prefix + f
            result.append(rel_path)
            file_count += 1
    
    folder_name = base_path.name
    walk_depth_first(base_path, folder_name + os.sep, 1)
    
    return result, file_count, folder_count, skipped


def format_path_style(paths: List[str], style: int = 0, base_path: str = "") -> List[str]:
    """
    格式化路径样式
    
    style: 0=当前文件夹开头, 1=点开头, 2=无开头, 3=绝对路径
    base_path: 用于生成绝对路径的基础路径
    """
    if not paths:
        return paths
    
    formatted = []
    for p in paths:
        parts = p.split(os.sep)
        if style == 0:
            formatted.append(p)
        elif style == 1:
            if len(parts) > 1:
                formatted.append('.' + os.sep + os.sep.join(parts[1:]))
            else:
                formatted.append('.' + os.sep + parts[0])
        elif style == 2:
            if len(parts) > 1:
                formatted.append(os.sep.join(parts[1:]))
            else:
                formatted.append(parts[0])
        else:
            if base_path:
                formatted.append(os.path.join(base_path, os.sep.join(parts[1:])))
            else:
                formatted.append(p)
    
    return formatted


def format_tree_style(paths: List[str], indent_char: str = ' ', indent_length: int = 2) -> List[str]:
    """
    格式化为树形结构
    
    indent_char: 缩进字符
    indent_length: 每级缩进的字符数
    """
    if not paths:
        return paths
    
    formatted = []
    indent_str = indent_char * indent_length
    
    for p in paths:
        parts = p.rstrip(os.sep).split(os.sep)
        depth = len(parts) - 1
        name = parts[-1]
        if p.endswith(os.sep):
            name += os.sep
        formatted.append(indent_str * depth + name)
    
    return formatted


class FileStructureGUI:
    """现代化简约风格的GUI界面"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("文件夹结构工具")
        self.root.geometry("800x600")
        self.root.configure(bg='#ffffff')
        
        self.current_path = ""
        self.raw_paths = []
        self.file_count = 0
        self.folder_count = 0
        self.is_scanning = False
        self.scan_thread = None
        
        self._setup_style()
        self._create_widgets()
        
    def _setup_style(self):
        """设置现代化简约风格"""
        self.colors = {
            'bg': '#ffffff',
            'fg': '#333333',
            'accent': '#0066cc',
            'hover': '#f0f0f0',
            'border': '#e0e0e0',
            'text_bg': '#fafafa'
        }
        
        self.default_font = ('Microsoft YaHei UI', 10)
        self.root.option_add('*Font', self.default_font)
        
    def _create_context_menu(self, widget, readonly=False):
        """创建右键菜单"""
        menu = tk.Menu(widget, tearoff=0, font=self.default_font)
        
        def show_menu(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
        
        def copy():
            try:
                if isinstance(widget, tk.Text):
                    if widget.tag_ranges(tk.SEL):
                        widget.clipboard_clear()
                        widget.clipboard_append(widget.get(tk.SEL_FIRST, tk.SEL_LAST))
                else:
                    widget.clipboard_clear()
                    widget.clipboard_append(widget.selection_get())
            except tk.TclError:
                pass
        
        def select_all():
            if isinstance(widget, tk.Text):
                widget.tag_add(tk.SEL, '1.0', tk.END)
            else:
                widget.select_range(0, tk.END)
        
        menu.add_command(label="复制", command=copy)
        menu.add_command(label="全选", command=select_all)
        
        if not readonly:
            def paste():
                try:
                    text = widget.clipboard_get()
                    if isinstance(widget, tk.Text):
                        if widget.tag_ranges(tk.SEL):
                            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                        widget.insert(tk.INSERT, text)
                    else:
                        widget.delete(0, tk.END)
                        widget.insert(0, text)
                except tk.TclError:
                    pass
            
            def cut():
                copy()
                try:
                    if isinstance(widget, tk.Text):
                        if widget.tag_ranges(tk.SEL):
                            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    else:
                        widget.delete(0, tk.END)
                except tk.TclError:
                    pass
            
            def clear():
                if isinstance(widget, tk.Text):
                    widget.delete('1.0', tk.END)
                else:
                    widget.delete(0, tk.END)
            
            menu.insert_command(0, label="粘贴", command=paste)
            menu.insert_command(0, label="剪切", command=cut)
            menu.add_command(label="清空", command=clear)
        
        widget.bind('<Button-3>', show_menu)
        return menu
        
    def _create_widgets(self):
        """创建界面组件"""
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        row1 = tk.Frame(main_frame, bg=self.colors['bg'])
        row1.pack(fill=tk.X, pady=(0, 8))
        
        self.select_btn = tk.Label(
            row1, text="选择文件夹", bg=self.colors['bg'],
            fg=self.colors['accent'], cursor='hand2', padx=8, pady=3
        )
        self.select_btn.pack(side=tk.LEFT)
        self.select_btn.bind('<Button-1>', self._select_folder)
        self.select_btn.bind('<Enter>', lambda e: self.select_btn.configure(fg='#004499'))
        self.select_btn.bind('<Leave>', lambda e: self.select_btn.configure(fg=self.colors['accent']))
        
        self.copy_btn = tk.Label(
            row1, text="复制", bg=self.colors['bg'],
            fg=self.colors['accent'], cursor='hand2', padx=8, pady=3
        )
        self.copy_btn.pack(side=tk.LEFT, padx=(15, 0))
        self.copy_btn.bind('<Button-1>', self._copy_to_clipboard)
        self.copy_btn.bind('<Enter>', lambda e: self.copy_btn.configure(fg='#004499'))
        self.copy_btn.bind('<Leave>', lambda e: self.copy_btn.configure(fg=self.colors['accent']))
        
        self.export_btn = tk.Label(
            row1, text="导出", bg=self.colors['bg'],
            fg=self.colors['accent'], cursor='hand2', padx=8, pady=3
        )
        self.export_btn.pack(side=tk.LEFT, padx=(15, 0))
        self.export_btn.bind('<Button-1>', self._export_file)
        self.export_btn.bind('<Enter>', lambda e: self.export_btn.configure(fg='#004499'))
        self.export_btn.bind('<Leave>', lambda e: self.export_btn.configure(fg=self.colors['accent']))
        
        self.stats_label = tk.Label(
            row1, text="", bg=self.colors['bg'], fg='#666666'
        )
        self.stats_label.pack(side=tk.RIGHT)
        
        row2 = tk.Frame(main_frame, bg=self.colors['bg'])
        row2.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(row2, text="样式:", bg=self.colors['bg'], fg=self.colors['fg']).pack(side=tk.LEFT)
        self.output_style = tk.StringVar(value="path")
        for text, value in [("路径", "path"), ("树形", "tree")]:
            rb = tk.Radiobutton(
                row2, text=text, variable=self.output_style, value=value,
                bg=self.colors['bg'], fg=self.colors['fg'],
                selectcolor=self.colors['bg'], activebackground=self.colors['bg'],
                command=self._on_style_change
            )
            rb.pack(side=tk.LEFT, padx=(6, 0))
        
        self.prefix_widgets = []
        self.sep1 = tk.Label(row2, text="│", bg=self.colors['bg'], fg='#cccccc', padx=10)
        self.prefix_widgets.append(self.sep1)
        self.sep1.pack(side=tk.LEFT)
        
        lbl = tk.Label(row2, text="前缀:", bg=self.colors['bg'], fg=self.colors['fg'])
        lbl.pack(side=tk.LEFT)
        self.prefix_widgets.append(lbl)
        
        self.path_prefix = tk.StringVar(value="folder")
        for text, value in [("文件夹", "folder"), ("点", "dot"), ("无", "none"), ("绝对", "absolute")]:
            rb = tk.Radiobutton(
                row2, text=text, variable=self.path_prefix, value=value,
                bg=self.colors['bg'], fg=self.colors['fg'],
                selectcolor=self.colors['bg'], activebackground=self.colors['bg'],
                command=self._update_display
            )
            rb.pack(side=tk.LEFT, padx=(6, 0))
            self.prefix_widgets.append(rb)
        
        self.indent_widgets = []
        self.sep2 = tk.Label(row2, text="│", bg=self.colors['bg'], fg='#cccccc', padx=10)
        self.indent_widgets.append(self.sep2)
        self.sep2.pack(side=tk.LEFT)
        
        lbl = tk.Label(row2, text="字符:", bg=self.colors['bg'], fg=self.colors['fg'])
        lbl.pack(side=tk.LEFT)
        self.indent_widgets.append(lbl)
        
        self.indent_char = tk.StringVar(value=" ")
        for text, value in [("空格", " "), ("-", "-"), ("|", "|"), (".", ".")]:
            rb = tk.Radiobutton(
                row2, text=text, variable=self.indent_char, value=value,
                bg=self.colors['bg'], fg=self.colors['fg'],
                selectcolor=self.colors['bg'], activebackground=self.colors['bg'],
                command=self._update_display
            )
            rb.pack(side=tk.LEFT, padx=(6, 0))
            self.indent_widgets.append(rb)
        
        lbl = tk.Label(row2, text="长度:", bg=self.colors['bg'], fg=self.colors['fg'])
        lbl.pack(side=tk.LEFT, padx=(12, 0))
        self.indent_widgets.append(lbl)
        
        self.indent_length = tk.StringVar(value="2")
        self.length_entry = tk.Entry(
            row2, textvariable=self.indent_length, width=3,
            bg=self.colors['text_bg'], fg=self.colors['fg'],
            relief=tk.FLAT, highlightthickness=1,
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['accent']
        )
        self.length_entry.pack(side=tk.LEFT, padx=(4, 0))
        self.length_entry.bind('<KeyRelease>', lambda e: self._update_display())
        self._create_context_menu(self.length_entry)
        self.indent_widgets.append(self.length_entry)
        
        self._update_options_visibility()
        
        row3 = tk.Frame(main_frame, bg=self.colors['bg'])
        row3.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(row3, text="路径:", bg=self.colors['bg'], fg=self.colors['fg']).pack(side=tk.LEFT)
        self.status_label = tk.Entry(
            row3, bg=self.colors['text_bg'], fg='#666666',
            relief=tk.FLAT, readonlybackground=self.colors['text_bg'],
            state='readonly', font=self.default_font, cursor='arrow'
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        self._create_context_menu(self.status_label, readonly=True)
        
        self.copy_path_btn = tk.Label(
            row3, text="复制路径", bg=self.colors['bg'],
            fg=self.colors['accent'], cursor='hand2', padx=8, pady=2
        )
        self.copy_path_btn.pack(side=tk.LEFT, padx=(10, 0))
        self.copy_path_btn.bind('<Button-1>', self._copy_path_to_clipboard)
        self.copy_path_btn.bind('<Enter>', lambda e: self.copy_path_btn.configure(fg='#004499'))
        self.copy_path_btn.bind('<Leave>', lambda e: self.copy_path_btn.configure(fg=self.colors['accent']))
        
        text_frame = tk.Frame(main_frame, bg=self.colors['border'], highlightthickness=0)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.text_area = tk.Text(
            text_frame, wrap=tk.NONE, bg=self.colors['text_bg'],
            fg=self.colors['fg'], relief=tk.FLAT, padx=8, pady=8,
            font=('Consolas', 10), highlightthickness=0
        )
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._create_context_menu(self.text_area)
        
        scrollbar_y = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.config(yscrollcommand=scrollbar_y.set)
        
        scrollbar_x = tk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=self.text_area.xview)
        scrollbar_x.pack(fill=tk.X, pady=(5, 0))
        self.text_area.config(xscrollcommand=scrollbar_x.set)
        
    def _on_style_change(self):
        """样式改变时更新选项可见性"""
        self._update_options_visibility()
        self._update_display()
        
    def _update_options_visibility(self):
        """根据当前样式更新选项可见性"""
        style = self.output_style.get()
        
        for w in self.prefix_widgets:
            w.pack_forget()
        for w in self.indent_widgets:
            w.pack_forget()
        
        if style == "path":
            for w in self.prefix_widgets:
                w.pack(side=tk.LEFT)
        else:
            for w in self.indent_widgets:
                w.pack(side=tk.LEFT)
        
    def _select_folder(self, event=None):
        """选择文件夹"""
        if self.is_scanning:
            return
            
        folder = filedialog.askdirectory(title="选择文件夹")
        if folder:
            self.current_path = folder
            self._set_status_text(f"当前目录: {folder}")
            self._start_async_scan(folder)
            
    def _start_async_scan(self, folder):
        """启动异步扫描"""
        self.is_scanning = True
        self._update_ui_for_scanning(True)
        self.stats_label.config(text="扫描中...")
        
        def scan_task():
            try:
                raw_paths, file_count, folder_count, skipped = scan_directory(folder)
                self.root.after(0, lambda: self._on_scan_complete(folder, raw_paths, file_count, folder_count, skipped))
            except Exception as e:
                self.root.after(0, lambda: self._on_scan_error(str(e)))
        
        self.scan_thread = threading.Thread(target=scan_task, daemon=True)
        self.scan_thread.start()
        
    def _on_scan_complete(self, folder, raw_paths, file_count, folder_count, skipped):
        """扫描完成回调（主线程执行）"""
        self.is_scanning = False
        self.raw_paths = raw_paths
        self.file_count = file_count
        self.folder_count = folder_count
        self._update_ui_for_scanning(False)
        self._update_display()
        self._set_status_text(f"当前目录: {folder}")
        total = self.file_count + self.folder_count
        stats_text = f"文件: {self.file_count} | 文件夹: {self.folder_count} | 总计: {total}"
        if skipped:
            stats_text += f" | 跳过: {len(skipped)}"
        self.stats_label.config(text=stats_text)
        
    def _on_scan_error(self, error_msg):
        """扫描错误回调（主线程执行）"""
        self.is_scanning = False
        self._update_ui_for_scanning(False)
        self._set_status_text("扫描失败")
        self.stats_label.config(text=f"错误: {error_msg}")
        
    def _update_ui_for_scanning(self, is_scanning):
        """更新UI扫描状态"""
        state = 'disabled' if is_scanning else 'normal'
        cursor = 'watch' if is_scanning else 'arrow'
        self.select_btn.config(cursor='watch' if is_scanning else 'hand2')
        self.copy_btn.config(cursor='watch' if is_scanning else 'hand2')
        self.export_btn.config(cursor='watch' if is_scanning else 'hand2')
        if is_scanning:
            self.select_btn.config(fg='#999999')
        else:
            self.select_btn.config(fg=self.colors['accent'])
            
    def _set_status_text(self, text):
        """设置状态栏文本"""
        self.status_label.config(state='normal')
        self.status_label.delete(0, tk.END)
        self.status_label.insert(0, text)
        self.status_label.config(state='readonly')
            
    def _update_display(self):
        """更新显示内容"""
        if not self.raw_paths:
            return
            
        style = self.output_style.get()
        prefix = self.path_prefix.get()
        indent_char = self.indent_char.get()
        
        try:
            indent_length = max(1, int(self.indent_length.get()))
        except ValueError:
            indent_length = 2
            
        if style == "path":
            style_map = {"folder": 0, "dot": 1, "none": 2, "absolute": 3}
            style_num = style_map.get(prefix, 0)
            formatted = format_path_style(self.raw_paths, style_num, self.current_path)
        else:
            formatted = format_tree_style(self.raw_paths, indent_char, indent_length)
            
        self.text_area.delete('1.0', tk.END)
        self.text_area.insert('1.0', '\n'.join(formatted))
        
    def _copy_to_clipboard(self, event=None):
        """复制到剪贴板"""
        content = self.text_area.get('1.0', tk.END + '-1c')
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        self.copy_btn.config(text="已复制!", fg='#28a745')
        self.root.after(1500, self._reset_copy_btn)
        
    def _reset_copy_btn(self):
        """重置复制按钮"""
        self.copy_btn.config(text="复制", fg=self.colors['accent'])
        
    def _copy_path_to_clipboard(self, event=None):
        """复制当前路径到剪贴板"""
        if self.current_path:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.current_path)
            self.copy_path_btn.config(text="已复制!", fg='#28a745')
            self.root.after(1500, self._reset_copy_path_btn)
            
    def _reset_copy_path_btn(self):
        """重置复制路径按钮"""
        self.copy_path_btn.config(text="复制路径", fg=self.colors['accent'])
        
    def _export_file(self, event=None):
        """导出到文件"""
        content = self.text_area.get('1.0', tk.END + '-1c')
        file_path = filedialog.asksaveasfilename(
            title="导出文件",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.export_btn.config(text="已导出!", fg='#28a745')
                self.root.after(1500, self._reset_export_btn)
            except PermissionError:
                self.export_btn.config(text="权限不足!", fg='#dc3545')
                self.root.after(2000, self._reset_export_btn)
            except OSError as e:
                self.export_btn.config(text=f"导出失败: {e}", fg='#dc3545')
                self.root.after(2000, self._reset_export_btn)
            
    def _reset_export_btn(self):
        """重置导出按钮"""
        self.export_btn.config(text="导出", fg=self.colors['accent'])
            
    def run(self):
        """运行GUI"""
        self.root.mainloop()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='文件夹结构工具 - 递归扫描并展示文件夹结构',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python files文件结构工具.py ./assets
    python files文件结构工具.py ./assets -o structure.txt
    python files文件结构工具.py ./assets -s 1 -o output.txt
    python files文件结构工具.py ./assets -t -i "-" -l 1
    python files文件结构工具.py              # 启动GUI版本
        """
    )
    
    parser.add_argument(
        'path',
        nargs='?',
        default=None,
        help='要扫描的文件夹路径（不填则启动GUI版本）'
    )
    
    parser.add_argument(
        '-o', '--output',
        metavar='<路径>',
        help='导出到文件'
    )
    
    parser.add_argument(
        '-s', '--style',
        type=int,
        choices=[0, 1, 2, 3],
        default=0,
        metavar='<数字>',
        help='路径样式 (0=文件夹开头, 1=点开头, 2=无开头, 3=绝对路径)'
    )
    
    parser.add_argument(
        '-t', '--tree',
        action='store_true',
        help='使用树形结构输出'
    )
    
    parser.add_argument(
        '-i', '--indent',
        default=' ',
        metavar='<字符>',
        help='树形结构缩进字符 (默认: 空格)'
    )
    
    parser.add_argument(
        '-l', '--length',
        type=int,
        default=2,
        metavar='<数字>',
        help='树形结构缩进长度 (默认: 2)'
    )
    
    args = parser.parse_args()
    
    if args.path is None:
        if GUI_AVAILABLE:
            app = FileStructureGUI()
            app.run()
        else:
            print("错误: tkinter 不可用，无法启动GUI版本")
            print("请使用命令行模式: python files文件结构工具.py <路径> [选项]")
            sys.exit(1)
    else:
        path = args.path
        
        if not os.path.exists(path):
            print(f"错误: 路径不存在 - {path}")
            sys.exit(1)
            
        if not os.path.isdir(path):
            print(f"错误: 不是文件夹 - {path}")
            sys.exit(1)
            
        paths, file_count, folder_count, skipped = scan_directory(path)
        total_count = file_count + folder_count
        
        if args.tree:
            formatted = format_tree_style(paths, args.indent, args.length)
        else:
            formatted = format_path_style(paths, args.style, path)
            
        output = '\n'.join(formatted)
        
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output)
                print(f"已导出到: {args.output}")
                print(f"统计: 文件 {file_count} | 文件夹 {folder_count} | 总计 {total_count}")
            except PermissionError:
                print(f"错误: 权限不足，无法写入文件 - {args.output}")
                sys.exit(1)
            except OSError as e:
                print(f"错误: 写入文件失败 - {e}")
                sys.exit(1)
        else:
            print(output)
            stats_line = f"\n统计: 文件 {file_count} | 文件夹 {folder_count} | 总计 {total_count}"
            print(stats_line)
        
        if skipped:
            print(f"\n警告: {len(skipped)} 个目录被跳过:")
            for s in skipped:
                print(f"  - {s}")


if __name__ == '__main__':
    main()
