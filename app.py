import customtkinter as ctk
import tkinter.messagebox as messagebox
import copy

# --- Core Logic & Data Models ---

class Process:
    def __init__(self, pid, arrival_time, burst_time, priority=0):
        self.pid = pid
        self.arrival_time = arrival_time
        self.burst_time = burst_time
        self.priority = priority
        self.remaining_time = burst_time
        self.start_time = -1
        self.completion_time = 0
        self.waiting_time = 0
        self.turnaround_time = 0

def calculate_fcfs(processes):
    procs = copy.deepcopy(processes)
    procs.sort(key=lambda x: x.arrival_time)
    current_time = 0
    timeline = []
    
    for p in procs:
        if current_time < p.arrival_time:
            timeline.append(("IDLE", current_time, p.arrival_time))
            current_time = p.arrival_time
            
        timeline.append((p.pid, current_time, current_time + p.burst_time))
        p.start_time = current_time
        p.completion_time = current_time + p.burst_time
        p.turnaround_time = p.completion_time - p.arrival_time
        p.waiting_time = p.turnaround_time - p.burst_time
        current_time = p.completion_time
        
    return procs, timeline

def calculate_round_robin(processes, quantum):
    procs = copy.deepcopy(processes)
    procs.sort(key=lambda x: x.arrival_time)
    n = len(procs)
    ready_queue = []
    current_time = 0
    completed = 0
    timeline = []
    i = 0
    
    while i < n and procs[i].arrival_time <= current_time:
        ready_queue.append(procs[i])
        i += 1
        
    while completed < n:
        if not ready_queue:
            if i < n:
                if current_time < procs[i].arrival_time:
                    timeline.append(("IDLE", current_time, procs[i].arrival_time))
                current_time = procs[i].arrival_time
                ready_queue.append(procs[i])
                i += 1
            else:
                current_time += 1
            continue

        p = ready_queue.pop(0)
        if p.start_time == -1:
            p.start_time = current_time
            
        execute_time = min(quantum, p.remaining_time)
        timeline.append((p.pid, current_time, current_time + execute_time))
        
        current_time += execute_time
        p.remaining_time -= execute_time
        
        while i < n and procs[i].arrival_time <= current_time:
            ready_queue.append(procs[i])
            i += 1
            
        if p.remaining_time > 0:
            ready_queue.append(p)
        else:
            completed += 1
            p.completion_time = current_time
            p.turnaround_time = p.completion_time - p.arrival_time
            p.waiting_time = p.turnaround_time - p.burst_time
            
    return procs, timeline

def calculate_spn(processes):
    procs = copy.deepcopy(processes)
    n = len(procs)
    current_time = 0
    completed = 0
    is_completed = [False] * n
    results = []
    timeline = []
    
    while completed < n:
        idx = -1
        min_bt = float('inf')
        for i in range(n):
            if procs[i].arrival_time <= current_time and not is_completed[i]:
                if procs[i].burst_time < min_bt:
                    min_bt = procs[i].burst_time
                    idx = i
                elif procs[i].burst_time == min_bt:
                    if procs[i].arrival_time < procs[idx].arrival_time:
                        idx = i
                        
        if idx != -1:
            p = procs[idx]
            timeline.append((p.pid, current_time, current_time + p.burst_time))
            p.start_time = current_time
            p.completion_time = current_time + p.burst_time
            p.turnaround_time = p.completion_time - p.arrival_time
            p.waiting_time = p.turnaround_time - p.burst_time
            current_time = p.completion_time
            is_completed[idx] = True
            completed += 1
            results.append(p)
        else:
            # Handle idle time
            if timeline and timeline[-1][0] == "IDLE":
                timeline[-1] = ("IDLE", timeline[-1][1], current_time + 1)
            else:
                timeline.append(("IDLE", current_time, current_time + 1))
            current_time += 1
            
    return results, timeline

def calculate_srt(processes):
    procs = copy.deepcopy(processes)
    n = len(procs)
    current_time = 0
    completed = 0
    execution_ticks = []
    
    # Tick-by-tick simulation for preemptive accuracy
    while completed < n:
        shortest = -1
        min_rem_time = float('inf')
        for i in range(n):
            if procs[i].arrival_time <= current_time and procs[i].remaining_time > 0:
                if procs[i].remaining_time < min_rem_time:
                    min_rem_time = procs[i].remaining_time
                    shortest = i
                elif procs[i].remaining_time == min_rem_time:
                    if procs[i].arrival_time < procs[shortest].arrival_time:
                        shortest = i
                        
        if shortest != -1:
            p = procs[shortest]
            if p.start_time == -1:
                p.start_time = current_time
            execution_ticks.append((current_time, p.pid))
            p.remaining_time -= 1
            current_time += 1
            
            if p.remaining_time == 0:
                completed += 1
                p.completion_time = current_time
                p.turnaround_time = p.completion_time - p.arrival_time
                p.waiting_time = p.turnaround_time - p.burst_time
        else:
            execution_ticks.append((current_time, "IDLE"))
            current_time += 1
            
    # Compress ticks into a timeline
    timeline = []
    if execution_ticks:
        curr_pid = execution_ticks[0][1]
        start_t = execution_ticks[0][0]
        for i in range(1, len(execution_ticks)):
            t, pid = execution_ticks[i]
            if pid != curr_pid:
                timeline.append((curr_pid, start_t, t))
                curr_pid = pid
                start_t = t
        timeline.append((curr_pid, start_t, execution_ticks[-1][0] + 1))
        
    return procs, timeline

def calculate_priority(processes):
    procs = copy.deepcopy(processes)
    n = len(procs)
    current_time = 0
    completed = 0
    is_completed = [False] * n
    results = []
    timeline = []
    
    while completed < n:
        idx = -1
        best_prio = float('inf')
        for i in range(n):
            if procs[i].arrival_time <= current_time and not is_completed[i]:
                if procs[i].priority < best_prio:
                    best_prio = procs[i].priority
                    idx = i
                elif procs[i].priority == best_prio:
                    if procs[i].arrival_time < procs[idx].arrival_time:
                        idx = i
                        
        if idx != -1:
            p = procs[idx]
            timeline.append((p.pid, current_time, current_time + p.burst_time))
            p.start_time = current_time
            p.completion_time = current_time + p.burst_time
            p.turnaround_time = p.completion_time - p.arrival_time
            p.waiting_time = p.turnaround_time - p.burst_time
            current_time = p.completion_time
            is_completed[idx] = True
            completed += 1
            results.append(p)
        else:
            if timeline and timeline[-1][0] == "IDLE":
                timeline[-1] = ("IDLE", timeline[-1][1], current_time + 1)
            else:
                timeline.append(("IDLE", current_time, current_time + 1))
            current_time += 1
            
    return results, timeline


# --- GUI Application ---

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class SchedulerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CPU Scheduling Analyzer - OS Project")
        self.geometry("950x700")
        self.processes = []
        self.process_count = 1
        
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.setup_sidebar()
        self.setup_main_area()

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(8, weight=1)
        
        ctk.CTkLabel(self.sidebar, text="Add Process", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.arrival_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Arrival Time (e.g., 0)")
        self.arrival_entry.grid(row=1, column=0, padx=20, pady=10)
        
        self.burst_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Burst Time (e.g., 5)")
        self.burst_entry.grid(row=2, column=0, padx=20, pady=10)
        
        self.priority_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Priority (Lowest = Best)")
        self.priority_entry.grid(row=3, column=0, padx=20, pady=10)
        
        self.add_btn = ctk.CTkButton(self.sidebar, text="Add Process to Queue", command=self.add_process)
        self.add_btn.grid(row=4, column=0, padx=20, pady=20)
        
        self.clear_btn = ctk.CTkButton(self.sidebar, text="Clear All Processes", fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"), command=self.clear_processes)
        self.clear_btn.grid(row=5, column=0, padx=20, pady=10)

        ctk.CTkLabel(self.sidebar, text="Current Queue:", font=ctk.CTkFont(weight="bold")).grid(row=6, column=0, padx=20, pady=(20, 0), sticky="w")
        self.queue_display = ctk.CTkTextbox(self.sidebar, height=150)
        self.queue_display.grid(row=7, column=0, padx=20, pady=10, sticky="nsew")

    def setup_main_area(self):
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)
        
        control_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        control_frame.grid(row=0, column=0, sticky="ew")
        
        ctk.CTkLabel(control_frame, text="Select Algorithm:").grid(row=0, column=0, padx=10, pady=10)
        self.algo_var = ctk.StringVar(value="Compare All (Find Best)")
        self.algo_dropdown = ctk.CTkOptionMenu(control_frame, variable=self.algo_var, 
                                               values=["Compare All (Find Best)", "FCFS", "Round Robin", "SPN", "SRT", "Priority"])
        self.algo_dropdown.grid(row=0, column=1, padx=10, pady=10)
        
        self.quantum_entry = ctk.CTkEntry(control_frame, placeholder_text="Time Quantum", width=120)
        self.quantum_entry.grid(row=0, column=2, padx=10, pady=10)
        
        self.run_btn = ctk.CTkButton(control_frame, text="Run Simulation", command=self.run_simulation, fg_color="#2E8B57", hover_color="#226B43")
        self.run_btn.grid(row=0, column=3, padx=10, pady=10)

        self.output_display = ctk.CTkTextbox(self.main_frame, font=ctk.CTkFont(family="Courier", size=14))
        self.output_display.grid(row=3, column=0, padx=10, pady=10, sticky="nsew")
        self.output_display.insert("0.0", "Welcome to the CPU Scheduling Analyzer.\nAdd processes on the left, then click 'Run Simulation'.\n")

    def add_process(self):
        try:
            at = int(self.arrival_entry.get())
            bt = int(self.burst_entry.get())
            prio = self.priority_entry.get()
            prio = int(prio) if prio else 0
            
            pid = f"P{self.process_count}"
            self.processes.append(Process(pid, at, bt, prio))
            self.process_count += 1
            
            self.queue_display.insert("end", f"{pid}: AT={at}, BT={bt}, Prio={prio}\n")
            self.arrival_entry.delete(0, "end")
            self.burst_entry.delete(0, "end")
            self.priority_entry.delete(0, "end")
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid integer numbers.")

    def clear_processes(self):
        self.processes = []
        self.process_count = 1
        self.queue_display.delete("0.0", "end")
        self.output_display.delete("0.0", "end")
        self.output_display.insert("0.0", "Process queue cleared.\n")

    def generate_gantt_chart(self, timeline):
        if not timeline:
            return "No timeline available.\n"
            
        # Merge adjacent identical PIDs (happens frequently in Round Robin)
        merged_timeline = []
        for item in timeline:
            if merged_timeline and merged_timeline[-1][0] == item[0]:
                merged_timeline[-1] = (merged_timeline[-1][0], merged_timeline[-1][1], item[2])
            else:
                merged_timeline.append(item)
                
        chart = "\n--- Gantt Chart (Execution Timeline) ---\n\n"
        bars = ""
        times = f"{merged_timeline[0][1]:<2}"
        
        for pid, start, end in merged_timeline:
            duration = end - start
            width = max(6, min(duration * 2, 12)) # Scale width for visuals
            
            bars += f"|{str(pid).center(width)}"
            times += f"{end:>{width+1}}"
            
        bars += "|\n"
        chart += bars + times + "\n\n"
        return chart

    def format_results(self, title, results, timeline):
        results.sort(key=lambda x: int(x.pid[1:]))
        out = f"\n{title}\n"
        out += "-"*70 + "\n"
        out += f"{'PID':<6} | {'Arrival':<8} | {'Burst':<6} | {'Finish':<8} | {'Turnaround':<12} | {'Waiting':<8}\n"
        out += "-"*70 + "\n"
        
        t_wt = 0
        t_tat = 0
        for p in results:
            out += f"{p.pid:<6} | {p.arrival_time:<8} | {p.burst_time:<6} | {p.completion_time:<8} | {p.turnaround_time:<12} | {p.waiting_time:<8}\n"
            t_wt += p.waiting_time
            t_tat += p.turnaround_time
            
        avg_wt = t_wt / len(results)
        avg_tat = t_tat / len(results)
        
        out += "-"*70 + "\n"
        out += f"Average Waiting Time:    {avg_wt:.2f}\n"
        out += f"Average Turnaround Time: {avg_tat:.2f}\n"
        
        # Append the new Gantt chart
        out += self.generate_gantt_chart(timeline)
        return out

    def run_simulation(self):
        if not self.processes:
            messagebox.showwarning("Warning", "Please add at least one process to the queue first.")
            return
            
        algo = self.algo_var.get()
        self.output_display.delete("0.0", "end")
        
        if algo == "Compare All (Find Best)":
            q_str = self.quantum_entry.get()
            quantum = int(q_str) if q_str else 2
            
            res_fcfs, _ = calculate_fcfs(self.processes)
            res_rr, _ = calculate_round_robin(self.processes, quantum)
            res_spn, _ = calculate_spn(self.processes)
            res_srt, _ = calculate_srt(self.processes)
            res_prio, _ = calculate_priority(self.processes)
            
            stats = [
                ("FCFS", sum(p.waiting_time for p in res_fcfs) / len(res_fcfs)),
                (f"Round Robin (Q={quantum})", sum(p.waiting_time for p in res_rr) / len(res_rr)),
                ("SPN", sum(p.waiting_time for p in res_spn) / len(res_spn)),
                ("SRT", sum(p.waiting_time for p in res_srt) / len(res_srt)),
                ("Priority", sum(p.waiting_time for p in res_prio) / len(res_prio))
            ]
            
            out = "=== ALGORITHM COMPARISON ===\n"
            out += f"{'Algorithm':<25} | {'Avg Waiting Time':<15}\n"
            out += "-"*45 + "\n"
            
            best_algo = stats[0]
            for name, wt in stats:
                out += f"{name:<25} | {wt:<15.2f}\n"
                if wt < best_algo[1]:
                    best_algo = (name, wt)
                    
            out += "\n" + "="*45 + "\n"
            out += f"🏆 BEST ALGORITHM: {best_algo[0]} \n🏆 LOWEST AVG WAITING TIME: {best_algo[1]:.2f}\n"
            out += "="*45 + "\n"
            out += "\n(Tip: Run a specific algorithm from the dropdown to see its Timeline/Gantt chart.)\n"
            self.output_display.insert("end", out)
            
        else:
            if algo == "FCFS":
                procs, timeline = calculate_fcfs(self.processes)
                out = self.format_results("=== FCFS (First Come First Served) ===", procs, timeline)
            elif algo == "Round Robin":
                try:
                    q = int(self.quantum_entry.get())
                except ValueError:
                    messagebox.showerror("Error", "Please enter a valid integer for Time Quantum.")
                    return
                procs, timeline = calculate_round_robin(self.processes, q)
                out = self.format_results(f"=== Round Robin (Quantum = {q}) ===", procs, timeline)
            elif algo == "SPN":
                procs, timeline = calculate_spn(self.processes)
                out = self.format_results("=== SPN (Shortest Process Next) ===", procs, timeline)
            elif algo == "SRT":
                procs, timeline = calculate_srt(self.processes)
                out = self.format_results("=== SRT (Shortest Remaining Time) ===", procs, timeline)
            elif algo == "Priority":
                procs, timeline = calculate_priority(self.processes)
                out = self.format_results("=== Priority Scheduling ===", procs, timeline)
                
            self.output_display.insert("end", out)

if __name__ == "__main__":
    app = SchedulerApp()
    app.mainloop()