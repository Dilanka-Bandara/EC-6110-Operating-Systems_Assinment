import copy

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

def get_input():
    processes = []
    try:
        n = int(input("Enter number of processes: "))
        for i in range(n):
            print(f"\n--- Process {i+1} ---")
            pid = f"P{i+1}"
            at = int(input(f"Enter Arrival Time for {pid}: "))
            bt = int(input(f"Enter Burst Time for {pid}: "))
            prio = int(input(f"Enter Priority for {pid} (Lower # = Higher Priority, or 0 if none): "))
            processes.append(Process(pid, at, bt, prio))
    except ValueError:
        print("Invalid input! Please enter integers.")
        return []
    return processes

def print_table(processes, algorithm_name):
    print(f"\n--- Results: {algorithm_name} ---")
    print(f"{'PID':<6} {'Arrival':<8} {'Burst':<6} {'Prio':<6} {'Finish':<8} {'Turnaround':<12} {'Waiting':<8}")
    
    total_wt = 0
    total_tat = 0
    
    # Sort by PID for display consistency
    processes.sort(key=lambda x: int(x.pid[1:]))
    
    for p in processes:
        print(f"{p.pid:<6} {p.arrival_time:<8} {p.burst_time:<6} {p.priority:<6} {p.completion_time:<8} {p.turnaround_time:<12} {p.waiting_time:<8}")
        total_wt += p.waiting_time
        total_tat += p.turnaround_time
        
    avg_wt = total_wt / len(processes)
    avg_tat = total_tat / len(processes)
    
    print(f"\nAverage Waiting Time: {avg_wt:.2f}")
    print(f"Average Turnaround Time: {avg_tat:.2f}")
    return avg_wt, avg_tat

# --- Algorithms ---

def fcfs(processes):
    # Sort by arrival time
    processes.sort(key=lambda x: x.arrival_time)
    current_time = 0
    
    for p in processes:
        if current_time < p.arrival_time:
            current_time = p.arrival_time
        p.start_time = current_time
        p.completion_time = current_time + p.burst_time
        p.turnaround_time = p.completion_time - p.arrival_time
        p.waiting_time = p.turnaround_time - p.burst_time
        current_time = p.completion_time
    return processes

def round_robin(processes, quantum):
    # Sort by arrival time initially
    processes.sort(key=lambda x: x.arrival_time)
    n = len(processes)
    ready_queue = []
    current_time = 0
    completed = 0
    
    # Deep copy to protect original objects during simulation
    proc_list = copy.deepcopy(processes)
    # Map to track index easily
    p_map = {p.pid: p for p in proc_list}
    
    # Push initial processes to queue
    i = 0
    while i < n and proc_list[i].arrival_time <= current_time:
        ready_queue.append(proc_list[i])
        i += 1
        
    while completed < n:
        if not ready_queue:
            # If queue is empty, jump to next arrival
            if i < n:
                current_time = proc_list[i].arrival_time
                ready_queue.append(proc_list[i])
                i += 1
            else:
                current_time += 1 # Should not happen if logic correct
            continue

        p = ready_queue.pop(0)
        
        if p.start_time == -1:
            p.start_time = current_time
            
        execute_time = min(quantum, p.remaining_time)
        current_time += execute_time
        p.remaining_time -= execute_time
        
        # Add newly arrived processes during this execution
        while i < n and proc_list[i].arrival_time <= current_time:
            ready_queue.append(proc_list[i])
            i += 1
            
        if p.remaining_time > 0:
            ready_queue.append(p)
        else:
            completed += 1
            p.completion_time = current_time
            p.turnaround_time = p.completion_time - p.arrival_time
            p.waiting_time = p.turnaround_time - p.burst_time

    return proc_list

def spn(processes):
    # Shortest Process Next (Non-Preemptive)
    n = len(processes)
    current_time = 0
    completed = 0
    proc_list = copy.deepcopy(processes)
    # Mark all as not completed
    is_completed = [False] * n
    results = []
    
    while completed < n:
        # Find process with min burst time among those arrived
        idx = -1
        min_bt = float('inf')
        
        for i in range(n):
            if proc_list[i].arrival_time <= current_time and not is_completed[i]:
                if proc_list[i].burst_time < min_bt:
                    min_bt = proc_list[i].burst_time
                    idx = i
                elif proc_list[i].burst_time == min_bt:
                    if proc_list[i].arrival_time < proc_list[idx].arrival_time:
                        idx = i
                        
        if idx != -1:
            p = proc_list[idx]
            p.start_time = current_time
            p.completion_time = current_time + p.burst_time
            p.turnaround_time = p.completion_time - p.arrival_time
            p.waiting_time = p.turnaround_time - p.burst_time
            
            current_time = p.completion_time
            is_completed[idx] = True
            completed += 1
            results.append(p)
        else:
            current_time += 1
            
    return results

def srt(processes):
    # Shortest Remaining Time (Preemptive)
    n = len(processes)
    current_time = 0
    completed = 0
    proc_list = copy.deepcopy(processes)
    min_rem_time = float('inf')
    shortest = -1
    check = False
    
    # Use a large max time loop or event driven. 
    # For simplicity in assignment, we step through time.
    # To optimize, we find max time, but here standard simulation:
    
    # We need to track processed count
    while completed < n:
        # Find process with min remaining time among arrived
        shortest = -1
        min_rem_time = float('inf')
        
        for i in range(n):
            if proc_list[i].arrival_time <= current_time and proc_list[i].remaining_time > 0:
                if proc_list[i].remaining_time < min_rem_time:
                    min_rem_time = proc_list[i].remaining_time
                    shortest = i
                elif proc_list[i].remaining_time == min_rem_time:
                    if proc_list[i].arrival_time < proc_list[shortest].arrival_time:
                        shortest = i
                        
        if shortest != -1:
            p = proc_list[shortest]
            if p.start_time == -1:
                p.start_time = current_time
            
            p.remaining_time -= 1
            current_time += 1
            
            if p.remaining_time == 0:
                completed += 1
                p.completion_time = current_time
                p.turnaround_time = p.completion_time - p.arrival_time
                p.waiting_time = p.turnaround_time - p.burst_time
        else:
            current_time += 1
            
    return proc_list

def priority_scheduling(processes):
    # Non-Preemptive Priority (Lower number = Higher priority)
    n = len(processes)
    current_time = 0
    completed = 0
    proc_list = copy.deepcopy(processes)
    is_completed = [False] * n
    results = []
    
    while completed < n:
        idx = -1
        best_prio = float('inf')
        
        for i in range(n):
            if proc_list[i].arrival_time <= current_time and not is_completed[i]:
                if proc_list[i].priority < best_prio:
                    best_prio = proc_list[i].priority
                    idx = i
                elif proc_list[i].priority == best_prio:
                    # FCFS tie-breaking
                    if proc_list[i].arrival_time < proc_list[idx].arrival_time:
                        idx = i
                        
        if idx != -1:
            p = proc_list[idx]
            p.start_time = current_time
            p.completion_time = current_time + p.burst_time
            p.turnaround_time = p.completion_time - p.arrival_time
            p.waiting_time = p.turnaround_time - p.burst_time
            
            current_time = p.completion_time
            is_completed[idx] = True
            completed += 1
            results.append(p)
        else:
            current_time += 1
            
    return results

# --- Main Logic ---

def main():
    print("=== OS Assignment Task 01: CPU Scheduling ===")
    processes = get_input()
    if not processes:
        return

    while True:
        print("\n=== MENU ===")
        print("1. Find Best Algorithm (Compare All)")
        print("2. Analyze Specific Algorithm")
        print("3. Exit")
        
        choice = input("Enter choice: ")
        
        if choice == '1':
            quantum = int(input("Enter Time Quantum for Round Robin: "))
            
            print("\nCalculating metrics for all algorithms...")
            
            # Run all
            res_fcfs = fcfs(copy.deepcopy(processes))
            res_rr = round_robin(copy.deepcopy(processes), quantum)
            res_spn = spn(copy.deepcopy(processes))
            res_srt = srt(copy.deepcopy(processes))
            res_prio = priority_scheduling(copy.deepcopy(processes))
            
            # Collect Stats
            stats = []
            
            # Helper to calc and store
            def add_stat(name, result_list):
                wt = sum(p.waiting_time for p in result_list) / len(result_list)
                tat = sum(p.turnaround_time for p in result_list) / len(result_list)
                stats.append((name, wt, tat))

            add_stat("FCFS", res_fcfs)
            add_stat("Round Robin", res_rr)
            add_stat("SPN", res_spn)
            add_stat("SRT", res_srt)
            add_stat("Priority", res_prio)
            
            print(f"\n{'Algorithm':<20} {'Avg Waiting':<15} {'Avg Turnaround':<15}")
            print("-" * 50)
            best_algo = stats[0]
            
            for name, wt, tat in stats:
                print(f"{name:<20} {wt:<15.2f} {tat:<15.2f}")
                # Simple logic for 'best': lowest waiting time
                if wt < best_algo[1]:
                    best_algo = (name, wt, tat)
                    
            print(f"\n[BEST ALGORITHM]: {best_algo[0]} with Avg Waiting Time: {best_algo[1]:.2f}")
            
        elif choice == '2':
            print("\nSelect Algorithm:")
            print("1. FCFS")
            print("2. Round Robin")
            print("3. Shortest Process Next (SPN)")
            print("4. Shortest Remaining Time (SRT)")
            print("5. Priority")
            
            algo = input("Enter selection: ")
            results = []
            name = ""
            
            if algo == '1':
                name = "FCFS"
                results = fcfs(copy.deepcopy(processes))
            elif algo == '2':
                name = "Round Robin"
                q = int(input("Enter Time Quantum: "))
                results = round_robin(copy.deepcopy(processes), q)
            elif algo == '3':
                name = "SPN"
                results = spn(copy.deepcopy(processes))
            elif algo == '4':
                name = "SRT"
                results = srt(copy.deepcopy(processes))
            elif algo == '5':
                name = "Priority"
                results = priority_scheduling(copy.deepcopy(processes))
            else:
                print("Invalid Selection")
                continue
                
            print_table(results, name)
            
        elif choice == '3':
            print("Exiting...")
            break
        else:
            print("Invalid choice, try again.")

if __name__ == "__main__":
    main()