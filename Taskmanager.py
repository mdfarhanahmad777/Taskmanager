import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import psutil
from datetime import datetime
import threading
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import GPUtil
import time

class ProcessMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("Real-Time Process Monitoring Dashboard")
        self.root.geometry("1300x600")
        self.cpu_data = []

        self.create_widgets()
        self.init_monitoring_frame()
        self.update_graphs()
        self.update_process_list()

    def create_widgets(self):
        self.search_var = tk.StringVar()
        search_frame = tk.Frame(self.root)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(search_frame, text="Search Process:").pack(side=tk.LEFT)
        tk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, padx=5)
        tk.Button(search_frame, text="Search", command=self.update_process_list).pack(side=tk.LEFT)

        filter_frame = tk.Frame(self.root)
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(filter_frame, text="Filter by CPU % >=").pack(side=tk.LEFT)
        self.cpu_filter_var = tk.DoubleVar(value=0.0)
        tk.Entry(filter_frame, textvariable=self.cpu_filter_var, width=5).pack(side=tk.LEFT, padx=5)
        tk.Label(filter_frame, text="Memory % >=").pack(side=tk.LEFT)
        self.memory_filter_var = tk.DoubleVar(value=0.0)
        tk.Entry(filter_frame, textvariable=self.memory_filter_var, width=5).pack(side=tk.LEFT, padx=5)
        tk.Button(filter_frame, text="Apply Filter", command=self.update_process_list).pack(side=tk.LEFT)

        columns = ("PID", "Name", "CPU %", "Memory %")
        self.tree = ttk.Treeview(self.root, columns=columns, show='headings')
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="center")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.tree.bind("<Double-1>", self.show_process_details)

        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(button_frame, text="Refresh", command=self.update_process_list).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Kill Process", command=self.kill_process, fg="red").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Kill All Selected", command=self.kill_all_selected, fg="red").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Save to File", command=self.save_to_file).pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar()
        self.status_var.set("Last refresh: Never")
        status_bar = tk.Label(self.root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, padx=10, pady=5)

    def init_monitoring_frame(self):
        self.monitoring_frame = tk.Frame(self.root)
        self.monitoring_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=10, pady=5)

        tk.Label(self.monitoring_frame, text="System Resource Monitor", font=("Arial", 12, "bold")).pack()

        self.cpu_fig, self.cpu_ax = plt.subplots(figsize=(4, 2))
        self.cpu_line, = self.cpu_ax.plot([], [], label="CPU Usage %")
        self.cpu_ax.set_ylim(0, 100)
        self.cpu_ax.set_title("CPU Usage Over Time")
        self.cpu_ax.set_ylabel("%")
        self.cpu_ax.set_xlabel("Time (s)")

        self.canvas = FigureCanvasTkAgg(self.cpu_fig, master=self.monitoring_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack()

        self.gpu_label = tk.Label(self.monitoring_frame, text="GPU Usage: N/A")
        self.gpu_label.pack()
        self.cpu_usage_label = tk.Label(self.monitoring_frame, text="CPU Usage: N/A")
        self.cpu_usage_label.pack()
        self.idle_label = tk.Label(self.monitoring_frame, text="System Idle: N/A")
        self.idle_label.pack()

        cores = psutil.cpu_count(logical=False)
        logical = psutil.cpu_count(logical=True)
        self.core_label = tk.Label(self.monitoring_frame, text=f"Physical Cores: {cores}, Logical Processors: {logical}")
        self.core_label.pack()

    def update_graphs(self):
        def monitor():
            while True:
                cpu = psutil.cpu_percent(interval=1)
                self.cpu_data.append(cpu)
                if len(self.cpu_data) > 20:
                    self.cpu_data.pop(0)

                self.cpu_line.set_data(range(len(self.cpu_data)), self.cpu_data)
                self.cpu_ax.set_xlim(0, len(self.cpu_data))
                self.cpu_ax.set_ylim(0, max(100, max(self.cpu_data) + 10))
                self.canvas.draw()

                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        self.gpu_label.config(text=f"GPU Usage: {gpus[0].load * 100:.2f}%")
                    else:
                        self.gpu_label.config(text="GPU Usage: N/A")
                except:
                    self.gpu_label.config(text="GPU Usage: Error")

                idle = 100 - cpu
                self.idle_label.config(text=f"System Idle: {idle:.2f}%")
                self.cpu_usage_label.config(text=f"CPU Usage: {cpu:.2f}%")

                time.sleep(1)

        threading.Thread(target=monitor, daemon=True).start()

    def update_process_list(self):
        selected_pids = {self.tree.item(i, "values")[0] for i in self.tree.selection()}
        self.tree.delete(*self.tree.get_children())

        search_text = self.search_var.get().lower()
        cpu_filter = self.cpu_filter_var.get()
        memory_filter = self.memory_filter_var.get()

        process_data = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                name = proc.info['name']
                if search_text and search_text not in name.lower():
                    continue

                cpu = proc.info['cpu_percent'] or 0.0
                mem = proc.info['memory_percent'] or 0.0

                if cpu < cpu_filter or mem < memory_filter:
                    continue

                process_data.append((proc.info['pid'], name, cpu, mem))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort by CPU usage descending
        process_data.sort(key=lambda x: (x[2], x[3]), reverse=True)

        for pid, name, cpu, mem in process_data:
            item = self.tree.insert("", tk.END, values=(pid, name, f"{cpu:.2f}", f"{mem:.2f}"))
            if str(pid) in selected_pids:
                self.tree.selection_add(item)

        self.status_var.set(f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.root.after(5000, self.update_process_list)

    def show_process_details(self, event):
        selected_item = self.tree.selection()
        if not selected_item:
            return

        pid = int(self.tree.item(selected_item, "values")[0])
        try:
            p = psutil.Process(pid)
            details = (
                f"PID: {p.pid}\n"
                f"Name: {p.name()}\n"
                f"Status: {p.status()}\n"
                f"CPU Usage: {p.cpu_percent():.2f}%\n"
                f"Memory Usage: {p.memory_percent():.2f}%\n"
                f"Executable Path: {p.exe()}\n"
                f"Parent PID: {p.ppid()}\n"
                f"Threads: {p.num_threads()}\n"
                f"Processor/Core: {p.cpu_num()}"
            )
            messagebox.showinfo("Process Details", details)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            messagebox.showwarning("Warning", "Could not retrieve process details!")

    def kill_process(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a process to kill!")
            return

        pid = int(self.tree.item(selected_item, "values")[0])
        confirm = messagebox.askyesno("Confirm", f"Are you sure you want to terminate process {pid}?")
        if not confirm:
            return

        try:
            p = psutil.Process(pid)
            p.terminate()
            messagebox.showinfo("Success", f"Process {pid} terminated successfully.")
            self.update_process_list()
        except psutil.NoSuchProcess:
            messagebox.showwarning("Warning", "The process no longer exists!")
        except psutil.AccessDenied:
            messagebox.showerror("Error", "Permission denied! Run as Administrator.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to terminate process: {e}")

    def kill_all_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select processes to kill!")
            return

        pids = [int(self.tree.item(item, "values")[0]) for item in selected_items]
        confirm = messagebox.askyesno("Confirm", f"Are you sure you want to terminate {len(pids)} processes?")
        if not confirm:
            return

        failed_pids = []
        for pid in pids:
            try:
                p = psutil.Process(pid)
                p.terminate()
            except Exception:
                failed_pids.append(pid)

        if failed_pids:
            messagebox.showwarning("Warning", f"Failed to terminate processes: {failed_pids}")
        else:
            messagebox.showinfo("Success", "All selected processes terminated successfully.")
        self.update_process_list()

    def save_to_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", 
                                                  filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not file_path:
            return

        with open(file_path, 'w') as file:
            file.write("PID\tName\tCPU %\tMemory %\n")
            for child in self.tree.get_children():
                values = self.tree.item(child, "values")
                file.write("\t".join(values) + "\n")

        messagebox.showinfo("Success", f"Process list saved to {file_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ProcessMonitor(root)
    root.mainloop()