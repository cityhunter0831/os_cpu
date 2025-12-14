"""
고급 스케줄링 알고리즘 구현
- Priority Scheduling (정적 및 동적 우선순위 with Aging)
- Multi-Level Queue (MLQ) with Feedback
- Rate Monotonic (RM)
- Earliest Deadline First (EDF)
"""

from typing import List, Optional, Dict
from core.process import Process, ProcessState, create_process_copy
from core.scheduler_base import BaseScheduler


class PriorityScheduler(BaseScheduler):
    """
    우선순위 스케줄러 (정적 우선순위)
    선점형: 낮은 우선순위 값이 높은 우선순위
    """
    
    def __init__(self, processes: List[Process]):
        super().__init__([create_process_copy(p) for p in processes], "Priority (Static)")
        self.execution_start = None
    
    def select_next_process(self) -> Optional[Process]:
        """우선순위가 가장 높은 프로세스 선택"""
        if not self.ready_queue:
            return None
        
        # 우선순위가 가장 높은 프로세스 (숫자가 낮을수록 높은 우선순위)
        return min(self.ready_queue, key=lambda p: (p.priority, p.arrival_time))
    
    def check_preemption(self) -> bool:
        """선점 가능 여부 확인"""
        if not self.running_process or not self.ready_queue:
            return False
        
        highest_priority_process = min(self.ready_queue, 
                                      key=lambda p: (p.priority, p.arrival_time))
        
        # Ready 큐에 더 높은 우선순위 프로세스가 있으면 선점
        if highest_priority_process.priority < self.running_process.priority:
            return True
        
        return False
    
    def execute_one_step(self) -> bool:
        """한 시간 단위 실행 (실시간 뷰어용)"""
        if self.is_simulation_complete():
            return True
        
        if self.in_context_switch:
            self.context_switch_remaining -= 1
            if self.context_switch_remaining == 0:
                self.in_context_switch = False
                self.running_process = self.context_switch_target
                self.context_switch_target = None
                if self.running_process:
                    self.running_process.state = ProcessState.RUNNING
                    self.log_event(f"P{self.running_process.pid} → Running")
                    self.execution_start = self.current_time
            self.current_time += 1
            return False
        
        self.handle_process_arrival()
        self.handle_io_completion()
        
        if self.running_process and self.check_preemption():
            if self.execution_start is not None:
                self.add_to_gantt_chart(self.running_process.pid, self.execution_start,
                                       self.current_time, ProcessState.RUNNING)
                self.execution_start = None
            
            self.running_process.state = ProcessState.READY
            self.running_process.last_ready_time = self.current_time
            self.ready_queue.append(self.running_process)
            self.log_event(f"P{self.running_process.pid} preempted by higher priority → Ready Queue")
            self.running_process = None
        
        if self.running_process is None:
            next_process = self.select_next_process()
            if next_process:
                self.ready_queue.remove(next_process)
                
                from core.scheduler_base import CONTEXT_SWITCH_OVERHEAD
                if self.previous_process is not None and self.previous_process.pid != next_process.pid and CONTEXT_SWITCH_OVERHEAD > 0:
                    self.stats.context_switches += 1
                    self.log_event(f"Context Switch: P{self.previous_process.pid} → P{next_process.pid}")
                    self.add_to_gantt_chart(-2, self.current_time,
                                          self.current_time + CONTEXT_SWITCH_OVERHEAD,
                                          ProcessState.CONTEXT_SWITCHING)
                    self.in_context_switch = True
                    self.context_switch_remaining = CONTEXT_SWITCH_OVERHEAD
                    self.context_switch_target = next_process
                    self.previous_process = next_process
                    self.current_time += 1
                    return False
                else:
                    self.running_process = next_process
                    self.running_process.state = ProcessState.RUNNING
                    if self.previous_process is None:
                        self.log_event(f"P{next_process.pid} → Running")
                    self.previous_process = next_process
                    self.execution_start = self.current_time
        
        if self.running_process:
            process = self.running_process
            
            if self.execution_start is None:
                self.execution_start = self.current_time
            
            burst_completed = process.execute(1)
            self.stats.cpu_busy_time += 1
            
            if burst_completed:
                self.add_to_gantt_chart(process.pid, self.execution_start,
                                       self.current_time + 1, ProcessState.RUNNING)
                self.execution_start = None
                
                process.complete_current_burst()
                
                if process.is_completed():
                    process.finish_time = self.current_time + 1
                    self.terminate_process(process)
                    self.running_process = None
                elif process.is_io_burst():
                    self.start_io_operation(process)
                    self.running_process = None
        else:
            self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1,
                                   ProcessState.READY)
        
        self.current_time += 1
        
        if self.current_time > 10000:
            self.log_event("WARNING: Simulation timeout")
            return True
        
        return self.is_simulation_complete()
    
    def run(self, verbose: bool = False) -> Dict:
        """Priority 스케줄링 실행"""
        self.log_event(f"===== {self.name} Scheduling Started =====")
        
        execution_start = None
        
        while len(self.terminated_processes) < len(self.processes):
            # 1. 프로세스 도착 처리
            self.handle_process_arrival()
            
            # 2. I/O 완료 처리
            self.handle_io_completion()
            
            # 3. 선점 검사
            if self.check_preemption():
                if execution_start is not None:
                    self.add_to_gantt_chart(self.running_process.pid, execution_start,
                                           self.current_time, ProcessState.RUNNING)
                    execution_start = None
                
                self.running_process.state = ProcessState.READY
                self.running_process.last_ready_time = self.current_time
                self.ready_queue.append(self.running_process)
                self.log_event(f"P{self.running_process.pid} preempted by higher priority → Ready Queue")
                self.running_process = None
            
            # 4. 프로세스 선택
            if self.running_process is None:
                next_process = self.select_next_process()
                if next_process:
                    self.ready_queue.remove(next_process)
                    self.context_switch(next_process)
                    execution_start = self.current_time
            
            # 5. CPU 실행
            if self.running_process:
                process = self.running_process
                
                if execution_start is None:
                    execution_start = self.current_time
                
                burst_completed = process.execute(1)
                self.stats.cpu_busy_time += 1
                
                if burst_completed:
                    self.add_to_gantt_chart(process.pid, execution_start,
                                           self.current_time + 1, ProcessState.RUNNING)
                    execution_start = None
                    
                    process.complete_current_burst()
                    
                    if process.is_completed():
                        process.finish_time = self.current_time + 1
                        self.terminate_process(process)
                        self.running_process = None
                    elif process.is_io_burst():
                        self.start_io_operation(process)
                        self.running_process = None
            else:
                self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1,
                                       ProcessState.READY)
            
            self.current_time += 1
            
            if self.current_time > 10000:
                self.log_event("WARNING: Simulation timeout")
                break
        
        self.log_event(f"===== {self.name} Scheduling Completed =====")
        
        if verbose:
            for log in self.event_log:
                print(log)
        
        return self.get_results()


class PriorityAgingScheduler(BaseScheduler):
    """
    우선순위 스케줄러 with Aging (동적 우선순위)
    대기 시간이 길어질수록 우선순위 상승
    """
    
    def __init__(self, processes: List[Process], aging_factor: int = 10):
        super().__init__([create_process_copy(p) for p in processes], 
                        f"Priority with Aging (factor={aging_factor})")
        self.aging_factor = aging_factor
        self.execution_start = None
    
    def apply_aging_to_ready_queue(self):
        """Ready 큐의 모든 프로세스에 Aging 적용"""
        for process in self.ready_queue:
            process.update_waiting_time(self.current_time)
            process.apply_aging(self.aging_factor)
    
    def select_next_process(self) -> Optional[Process]:
        """우선순위가 가장 높은 프로세스 선택"""
        if not self.ready_queue:
            return None
        
        return min(self.ready_queue, key=lambda p: (p.priority, p.arrival_time))
    
    def check_preemption(self) -> bool:
        """선점 가능 여부 확인"""
        if not self.running_process or not self.ready_queue:
            return False
        
        highest_priority_process = min(self.ready_queue, 
                                      key=lambda p: (p.priority, p.arrival_time))
        
        if highest_priority_process.priority < self.running_process.priority:
            return True
        
        return False
    
    def execute_one_step(self) -> bool:
        """한 시간 단위 실행 (실시간 뷰어용)"""
        if self.is_simulation_complete():
            return True
        
        if self.in_context_switch:
            self.context_switch_remaining -= 1
            if self.context_switch_remaining == 0:
                self.in_context_switch = False
                self.running_process = self.context_switch_target
                self.context_switch_target = None
                if self.running_process:
                    self.running_process.state = ProcessState.RUNNING
                    self.log_event(f"P{self.running_process.pid} → Running")
                    self.execution_start = self.current_time
            self.current_time += 1
            return False
        
        self.handle_process_arrival()
        self.handle_io_completion()
        self.apply_aging_to_ready_queue()
        
        if self.running_process and self.check_preemption():
            if self.execution_start is not None:
                self.add_to_gantt_chart(self.running_process.pid, self.execution_start,
                                       self.current_time, ProcessState.RUNNING)
                self.execution_start = None
            
            self.running_process.state = ProcessState.READY
            self.running_process.last_ready_time = self.current_time
            self.ready_queue.append(self.running_process)
            self.log_event(f"P{self.running_process.pid} preempted → Ready Queue")
            self.running_process = None
        
        if self.running_process is None:
            next_process = self.select_next_process()
            if next_process:
                self.ready_queue.remove(next_process)
                next_process.reset_to_initial_priority()
                
                from core.scheduler_base import CONTEXT_SWITCH_OVERHEAD
                if self.previous_process is not None and self.previous_process.pid != next_process.pid and CONTEXT_SWITCH_OVERHEAD > 0:
                    self.stats.context_switches += 1
                    self.log_event(f"Context Switch: P{self.previous_process.pid} → P{next_process.pid}")
                    self.add_to_gantt_chart(-2, self.current_time,
                                          self.current_time + CONTEXT_SWITCH_OVERHEAD,
                                          ProcessState.CONTEXT_SWITCHING)
                    self.in_context_switch = True
                    self.context_switch_remaining = CONTEXT_SWITCH_OVERHEAD
                    self.context_switch_target = next_process
                    self.previous_process = next_process
                    self.current_time += 1
                    return False
                else:
                    self.running_process = next_process
                    self.running_process.state = ProcessState.RUNNING
                    if self.previous_process is None:
                        self.log_event(f"P{next_process.pid} → Running")
                    self.previous_process = next_process
                    self.execution_start = self.current_time
        
        if self.running_process:
            process = self.running_process
            
            if self.execution_start is None:
                self.execution_start = self.current_time
            
            burst_completed = process.execute(1)
            self.stats.cpu_busy_time += 1
            
            if burst_completed:
                self.add_to_gantt_chart(process.pid, self.execution_start,
                                       self.current_time + 1, ProcessState.RUNNING)
                self.execution_start = None
                
                process.complete_current_burst()
                
                if process.is_completed():
                    process.finish_time = self.current_time + 1
                    self.terminate_process(process)
                    self.running_process = None
                elif process.is_io_burst():
                    self.start_io_operation(process)
                    self.running_process = None
        else:
            self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1,
                                   ProcessState.READY)
        
        self.current_time += 1
        
        if self.current_time > 10000:
            self.log_event("WARNING: Simulation timeout")
            return True
        
        return self.is_simulation_complete()
    
    def run(self, verbose: bool = False) -> Dict:
        """Priority with Aging 스케줄링 실행"""
        self.log_event(f"===== {self.name} Scheduling Started =====")
        
        execution_start = None
        
        while len(self.terminated_processes) < len(self.processes):
            # 1. 프로세스 도착 처리
            self.handle_process_arrival()
            
            # 2. I/O 완료 처리
            self.handle_io_completion()
            
            # 3. Aging 적용
            self.apply_aging_to_ready_queue()
            
            # 4. 선점 검사
            if self.check_preemption():
                if execution_start is not None:
                    self.add_to_gantt_chart(self.running_process.pid, execution_start,
                                           self.current_time, ProcessState.RUNNING)
                    execution_start = None
                
                self.running_process.state = ProcessState.READY
                self.running_process.last_ready_time = self.current_time
                self.ready_queue.append(self.running_process)
                self.log_event(f"P{self.running_process.pid} preempted → Ready Queue")
                self.running_process = None
            
            # 5. 프로세스 선택
            if self.running_process is None:
                next_process = self.select_next_process()
                if next_process:
                    self.ready_queue.remove(next_process)
                    # 실행 시 우선순위 초기화
                    next_process.reset_to_initial_priority()
                    self.context_switch(next_process)
                    execution_start = self.current_time
            
            # 6. CPU 실행
            if self.running_process:
                process = self.running_process
                
                if execution_start is None:
                    execution_start = self.current_time
                
                burst_completed = process.execute(1)
                self.stats.cpu_busy_time += 1
                
                if burst_completed:
                    self.add_to_gantt_chart(process.pid, execution_start,
                                           self.current_time + 1, ProcessState.RUNNING)
                    execution_start = None
                    
                    process.complete_current_burst()
                    
                    if process.is_completed():
                        process.finish_time = self.current_time + 1
                        self.terminate_process(process)
                        self.running_process = None
                    elif process.is_io_burst():
                        self.start_io_operation(process)
                        self.running_process = None
            else:
                self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1,
                                       ProcessState.READY)
            
            self.current_time += 1
            
            if self.current_time > 10000:
                self.log_event("WARNING: Simulation timeout")
                break
        
        self.log_event(f"===== {self.name} Scheduling Completed =====")
        
        if verbose:
            for log in self.event_log:
                print(log)
        
        return self.get_results()


class MLQScheduler(BaseScheduler):
    """
    Multi-Level Queue 스케줄러 with Feedback
    - Queue 0 (Highest): RR with time slice 8
    - Queue 1 (Medium): RR with time slice 16
    - Queue 2 (Lowest): FCFS
    """
    
    def __init__(self, processes: List[Process]):
        super().__init__([create_process_copy(p) for p in processes], "Multi-Level Queue")
        
        # 3개의 큐
        self.queues = [[], [], []]  # [highest, medium, lowest]
        self.time_slices = [8, 16, float('inf')]  # Queue별 타임 슬라이스
        self.current_time_slice = 0
        self.execution_start = None
    
    def handle_process_arrival(self):
        """프로세스 도착 처리 - 모두 최상위 큐에 삽입"""
        for process in self.processes:
            if process.arrival_time == self.current_time:
                process.state = ProcessState.READY
                process.last_ready_time = self.current_time
                process.queue_level = 0  # 최상위 큐
                self.queues[0].append(process)
                self.log_event(f"P{process.pid} arrived → Queue 0")
    
    def handle_io_completion(self):
        """I/O 완료 처리 - 원래 큐 레벨로 복귀"""
        completed_ios = []
        for io_time, process in self.io_completion_queue:
            if io_time <= self.current_time:
                process.complete_current_burst()
                
                if not process.is_completed():
                    process.state = ProcessState.READY
                    process.last_ready_time = self.current_time
                    self.queues[process.queue_level].append(process)
                    self.log_event(f"P{process.pid} I/O completed → Queue {process.queue_level}")
                else:
                    self.terminate_process(process)
                
                completed_ios.append((io_time, process))
        
        for io_entry in completed_ios:
            self.io_completion_queue.remove(io_entry)
    
    def select_next_process(self) -> Optional[Process]:
        """우선순위가 높은 큐부터 프로세스 선택"""
        for level in range(3):
            if self.queues[level]:
                return self.queues[level][0]
        return None
    
    def execute_one_step(self) -> bool:
        """한 시간 단위 실행 (실시간 뷰어용)"""
        if self.is_simulation_complete():
            return True
        
        if self.in_context_switch:
            self.context_switch_remaining -= 1
            if self.context_switch_remaining == 0:
                self.in_context_switch = False
                self.running_process = self.context_switch_target
                self.context_switch_target = None
                if self.running_process:
                    self.running_process.state = ProcessState.RUNNING
                    self.log_event(f"P{self.running_process.pid} → Running")
                    self.execution_start = self.current_time
                    self.current_time_slice = 0
            self.current_time += 1
            return False
        
        self.handle_process_arrival()
        self.handle_io_completion()
        
        current_queue_level = 0
        
        # 타임 슬라이스 만료 확인
        if self.running_process:
            current_queue_level = self.running_process.queue_level
            time_limit = self.time_slices[current_queue_level]
            
            if (current_queue_level < 2 and 
                self.current_time_slice >= time_limit):
                if self.execution_start is not None:
                    self.add_to_gantt_chart(self.running_process.pid, self.execution_start,
                                           self.current_time, ProcessState.RUNNING)
                    self.execution_start = None
                
                new_level = min(2, current_queue_level + 1)
                self.running_process.queue_level = new_level
                self.running_process.state = ProcessState.READY
                self.running_process.last_ready_time = self.current_time
                self.queues[new_level].append(self.running_process)
                self.log_event(f"P{self.running_process.pid} demoted → Queue {new_level}")
                self.running_process = None
                self.current_time_slice = 0
        
        # 선점 검사
        if self.running_process:
            for level in range(current_queue_level):
                if self.queues[level]:
                    if self.execution_start is not None:
                        self.add_to_gantt_chart(self.running_process.pid, self.execution_start,
                                               self.current_time, ProcessState.RUNNING)
                        self.execution_start = None
                    
                    self.running_process.state = ProcessState.READY
                    self.running_process.last_ready_time = self.current_time
                    self.queues[current_queue_level].append(self.running_process)
                    self.log_event(f"P{self.running_process.pid} preempted → Queue {current_queue_level}")
                    self.running_process = None
                    self.current_time_slice = 0
                    break
        
        # 프로세스 선택 및 문맥교환
        if self.running_process is None:
            next_process = self.select_next_process()
            if next_process:
                for level in range(3):
                    if next_process in self.queues[level]:
                        self.queues[level].remove(next_process)
                        break
                
                from core.scheduler_base import CONTEXT_SWITCH_OVERHEAD
                if self.previous_process is not None and self.previous_process.pid != next_process.pid and CONTEXT_SWITCH_OVERHEAD > 0:
                    self.stats.context_switches += 1
                    self.log_event(f"Context Switch: P{self.previous_process.pid} → P{next_process.pid}")
                    self.add_to_gantt_chart(-2, self.current_time,
                                          self.current_time + CONTEXT_SWITCH_OVERHEAD,
                                          ProcessState.CONTEXT_SWITCHING)
                    self.in_context_switch = True
                    self.context_switch_remaining = CONTEXT_SWITCH_OVERHEAD
                    self.context_switch_target = next_process
                    self.previous_process = next_process
                    self.current_time_slice = 0
                    self.current_time += 1
                    return False
                else:
                    self.running_process = next_process
                    self.running_process.state = ProcessState.RUNNING
                    if self.previous_process is None:
                        self.log_event(f"P{next_process.pid} → Running")
                    self.previous_process = next_process
                    self.current_time_slice = 0
                    self.execution_start = self.current_time
        
        # CPU 실행
        if self.running_process:
            process = self.running_process
            
            if self.execution_start is None:
                self.execution_start = self.current_time
            
            burst_completed = process.execute(1)
            self.stats.cpu_busy_time += 1
            self.current_time_slice += 1
            
            if burst_completed:
                self.add_to_gantt_chart(process.pid, self.execution_start,
                                       self.current_time + 1, ProcessState.RUNNING)
                self.execution_start = None
                
                process.complete_current_burst()
                self.current_time_slice = 0
                
                if process.is_completed():
                    process.finish_time = self.current_time + 1
                    self.terminate_process(process)
                    self.running_process = None
                elif process.is_io_burst():
                    self.start_io_operation(process)
                    self.running_process = None
        else:
            self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1,
                                   ProcessState.READY)
        
        self.current_time += 1
        
        if self.current_time > 10000:
            self.log_event("WARNING: Simulation timeout")
            return True
        
        return self.is_simulation_complete()
    
    def run(self, verbose: bool = False) -> Dict:
        """MLQ 스케줄링 실행"""
        self.log_event(f"===== {self.name} Scheduling Started =====")
        
        execution_start = None
        current_queue_level = 0
        
        while len(self.terminated_processes) < len(self.processes):
            # 1. 프로세스 도착 처리
            self.handle_process_arrival()
            
            # 2. I/O 완료 처리
            self.handle_io_completion()
            
            # 3. 타임 슬라이스 만료 확인 (Queue 0, 1만 해당)
            if self.running_process:
                current_queue_level = self.running_process.queue_level
                time_limit = self.time_slices[current_queue_level]
                
                if (current_queue_level < 2 and 
                    self.current_time_slice >= time_limit):
                    # 타임 슬라이스 만료 - 하위 큐로 이동
                    if execution_start is not None:
                        self.add_to_gantt_chart(self.running_process.pid, execution_start,
                                               self.current_time, ProcessState.RUNNING)
                        execution_start = None
                    
                    new_level = min(2, current_queue_level + 1)
                    self.running_process.queue_level = new_level
                    self.running_process.state = ProcessState.READY
                    self.running_process.last_ready_time = self.current_time
                    self.queues[new_level].append(self.running_process)
                    self.log_event(f"P{self.running_process.pid} demoted → Queue {new_level}")
                    self.running_process = None
                    self.current_time_slice = 0
            
            # 4. 선점 검사 (더 높은 우선순위 큐에 프로세스가 들어온 경우)
            if self.running_process:
                for level in range(current_queue_level):
                    if self.queues[level]:
                        # 더 높은 우선순위 큐에 프로세스 존재 - 선점
                        if execution_start is not None:
                            self.add_to_gantt_chart(self.running_process.pid, execution_start,
                                                   self.current_time, ProcessState.RUNNING)
                            execution_start = None
                        
                        self.running_process.state = ProcessState.READY
                        self.running_process.last_ready_time = self.current_time
                        self.queues[current_queue_level].append(self.running_process)
                        self.log_event(f"P{self.running_process.pid} preempted → Queue {current_queue_level}")
                        self.running_process = None
                        self.current_time_slice = 0
                        break
            
            # 5. 프로세스 선택
            if self.running_process is None:
                next_process = self.select_next_process()
                if next_process:
                    for level in range(3):
                        if next_process in self.queues[level]:
                            self.queues[level].remove(next_process)
                            break
                    self.context_switch(next_process)
                    self.current_time_slice = 0
                    execution_start = self.current_time
            
            # 6. CPU 실행
            if self.running_process:
                process = self.running_process
                
                if execution_start is None:
                    execution_start = self.current_time
                
                burst_completed = process.execute(1)
                self.stats.cpu_busy_time += 1
                self.current_time_slice += 1
                
                if burst_completed:
                    self.add_to_gantt_chart(process.pid, execution_start,
                                           self.current_time + 1, ProcessState.RUNNING)
                    execution_start = None
                    
                    process.complete_current_burst()
                    self.current_time_slice = 0
                    
                    if process.is_completed():
                        process.finish_time = self.current_time + 1
                        self.terminate_process(process)
                        self.running_process = None
                    elif process.is_io_burst():
                        self.start_io_operation(process)
                        self.running_process = None
            else:
                self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1,
                                       ProcessState.READY)
            
            self.current_time += 1
            
            if self.current_time > 10000:
                self.log_event("WARNING: Simulation timeout")
                break
        
        self.log_event(f"===== {self.name} Scheduling Completed =====")
        
        if verbose:
            for log in self.event_log:
                print(log)
        
        return self.get_results()


class RateMonotonicScheduler(BaseScheduler):
    """
    Rate Monotonic (RM) 스케줄러
    주기가 짧을수록 높은 우선순위 (정적 우선순위)
    """
    
    def __init__(self, processes: List[Process]):
        # 실시간 프로세스만 필터링
        rt_processes = [p for p in processes if p.period > 0]
        super().__init__([create_process_copy(p) for p in rt_processes], "Rate Monotonic (RM)")
        self.execution_start = None
    
    def select_next_process(self) -> Optional[Process]:
        """주기가 가장 짧은 프로세스 선택"""
        if not self.ready_queue:
            return None
        
        # 주기가 짧을수록 높은 우선순위
        return min(self.ready_queue, key=lambda p: (p.period, p.arrival_time))
    
    def check_preemption(self) -> bool:
        """선점 가능 여부 확인"""
        if not self.running_process or not self.ready_queue:
            return False
        
        shortest_period_process = min(self.ready_queue, 
                                     key=lambda p: (p.period, p.arrival_time))
        
        if shortest_period_process.period < self.running_process.period:
            return True
        
        return False
    
    def execute_one_step(self) -> bool:
        """한 시간 단위 실행 (실시간 뷰어용)"""
        if not self.processes:
            return True
        
        if self.is_simulation_complete():
            return True
        
        if self.in_context_switch:
            self.context_switch_remaining -= 1
            if self.context_switch_remaining == 0:
                self.in_context_switch = False
                self.running_process = self.context_switch_target
                self.context_switch_target = None
                if self.running_process:
                    self.running_process.state = ProcessState.RUNNING
                    self.log_event(f"P{self.running_process.pid} → Running")
                    self.execution_start = self.current_time
            self.current_time += 1
            return False
        
        self.handle_process_arrival()
        self.handle_io_completion()
        
        if self.running_process and self.check_preemption():
            if self.execution_start is not None:
                self.add_to_gantt_chart(self.running_process.pid, self.execution_start,
                                       self.current_time, ProcessState.RUNNING)
                self.execution_start = None
            
            self.running_process.state = ProcessState.READY
            self.running_process.last_ready_time = self.current_time
            self.ready_queue.append(self.running_process)
            self.log_event(f"P{self.running_process.pid} preempted by shorter period → Ready Queue")
            self.running_process = None
        
        if self.running_process is None:
            next_process = self.select_next_process()
            if next_process:
                self.ready_queue.remove(next_process)
                
                from core.scheduler_base import CONTEXT_SWITCH_OVERHEAD
                if self.previous_process is not None and self.previous_process.pid != next_process.pid and CONTEXT_SWITCH_OVERHEAD > 0:
                    self.stats.context_switches += 1
                    self.log_event(f"Context Switch: P{self.previous_process.pid} → P{next_process.pid}")
                    self.add_to_gantt_chart(-2, self.current_time,
                                          self.current_time + CONTEXT_SWITCH_OVERHEAD,
                                          ProcessState.CONTEXT_SWITCHING)
                    self.in_context_switch = True
                    self.context_switch_remaining = CONTEXT_SWITCH_OVERHEAD
                    self.context_switch_target = next_process
                    self.previous_process = next_process
                    self.current_time += 1
                    return False
                else:
                    self.running_process = next_process
                    self.running_process.state = ProcessState.RUNNING
                    if self.previous_process is None:
                        self.log_event(f"P{next_process.pid} → Running")
                    self.previous_process = next_process
                    self.execution_start = self.current_time
        
        if self.running_process:
            process = self.running_process
            
            if self.execution_start is None:
                self.execution_start = self.current_time
            
            burst_completed = process.execute(1)
            self.stats.cpu_busy_time += 1
            
            if burst_completed:
                self.add_to_gantt_chart(process.pid, self.execution_start,
                                       self.current_time + 1, ProcessState.RUNNING)
                self.execution_start = None
                
                process.complete_current_burst()
                
                if process.is_completed():
                    process.finish_time = self.current_time + 1
                    self.terminate_process(process)
                    self.running_process = None
                elif process.is_io_burst():
                    self.start_io_operation(process)
                    self.running_process = None
        else:
            self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1,
                                   ProcessState.READY)
        
        self.current_time += 1
        
        if self.current_time > 10000:
            self.log_event("WARNING: Simulation timeout")
            return True
        
        return self.is_simulation_complete()
    
    def run(self, verbose: bool = False) -> Dict:
        """Rate Monotonic 스케줄링 실행"""
        self.log_event(f"===== {self.name} Scheduling Started =====")
        
        if not self.processes:
            self.log_event("No real-time processes found")
            return self.get_results()
        
        execution_start = None
        
        while len(self.terminated_processes) < len(self.processes):
            # 1. 프로세스 도착 처리
            self.handle_process_arrival()
            
            # 2. I/O 완료 처리
            self.handle_io_completion()
            
            # 3. 선점 검사
            if self.check_preemption():
                if execution_start is not None:
                    self.add_to_gantt_chart(self.running_process.pid, execution_start,
                                           self.current_time, ProcessState.RUNNING)
                    execution_start = None
                
                self.running_process.state = ProcessState.READY
                self.running_process.last_ready_time = self.current_time
                self.ready_queue.append(self.running_process)
                self.log_event(f"P{self.running_process.pid} preempted by shorter period → Ready Queue")
                self.running_process = None
            
            # 4. 프로세스 선택
            if self.running_process is None:
                next_process = self.select_next_process()
                if next_process:
                    self.ready_queue.remove(next_process)
                    self.context_switch(next_process)
                    execution_start = self.current_time
            
            # 5. CPU 실행
            if self.running_process:
                process = self.running_process
                
                if execution_start is None:
                    execution_start = self.current_time
                
                burst_completed = process.execute(1)
                self.stats.cpu_busy_time += 1
                
                if burst_completed:
                    self.add_to_gantt_chart(process.pid, execution_start,
                                           self.current_time + 1, ProcessState.RUNNING)
                    execution_start = None
                    
                    process.complete_current_burst()
                    
                    if process.is_completed():
                        process.finish_time = self.current_time + 1
                        self.terminate_process(process)
                        self.running_process = None
                    elif process.is_io_burst():
                        self.start_io_operation(process)
                        self.running_process = None
            else:
                self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1,
                                       ProcessState.READY)
            
            self.current_time += 1
            
            if self.current_time > 10000:
                self.log_event("WARNING: Simulation timeout")
                break
        
        self.log_event(f"===== {self.name} Scheduling Completed =====")
        
        if verbose:
            for log in self.event_log:
                print(log)
        
        return self.get_results()


class EDFScheduler(BaseScheduler):
    """
    Earliest Deadline First (EDF) 스케줄러
    마감시한이 가까울수록 높은 우선순위 (동적 우선순위)
    """
    
    def __init__(self, processes: List[Process]):
        # 실시간 프로세스만 필터링
        rt_processes = [p for p in processes if p.deadline > 0]
        super().__init__([create_process_copy(p) for p in rt_processes], "Earliest Deadline First (EDF)")
        self.execution_start = None
    
    def select_next_process(self) -> Optional[Process]:
        """절대 마감시한이 가장 빠른 프로세스 선택"""
        if not self.ready_queue:
            return None
        
        # 절대 마감시한이 빠를수록 높은 우선순위
        return min(self.ready_queue, key=lambda p: (p.absolute_deadline, p.arrival_time))
    
    def check_preemption(self) -> bool:
        """선점 가능 여부 확인"""
        if not self.running_process or not self.ready_queue:
            return False
        
        earliest_deadline_process = min(self.ready_queue, 
                                       key=lambda p: (p.absolute_deadline, p.arrival_time))
        
        if earliest_deadline_process.absolute_deadline < self.running_process.absolute_deadline:
            return True
        
        return False
    
    def execute_one_step(self) -> bool:
        """한 시간 단위 실행 (실시간 뷰어용)"""
        if not self.processes:
            return True
        
        if self.is_simulation_complete():
            return True
        
        if self.in_context_switch:
            self.context_switch_remaining -= 1
            if self.context_switch_remaining == 0:
                self.in_context_switch = False
                self.running_process = self.context_switch_target
                self.context_switch_target = None
                if self.running_process:
                    self.running_process.state = ProcessState.RUNNING
                    self.log_event(f"P{self.running_process.pid} → Running")
                    self.execution_start = self.current_time
            self.current_time += 1
            return False
        
        self.handle_process_arrival()
        self.handle_io_completion()
        
        if self.running_process and self.check_preemption():
            if self.execution_start is not None:
                self.add_to_gantt_chart(self.running_process.pid, self.execution_start,
                                       self.current_time, ProcessState.RUNNING)
                self.execution_start = None
            
            self.running_process.state = ProcessState.READY
            self.running_process.last_ready_time = self.current_time
            self.ready_queue.append(self.running_process)
            self.log_event(f"P{self.running_process.pid} preempted by earlier deadline → Ready Queue")
            self.running_process = None
        
        if self.running_process is None:
            next_process = self.select_next_process()
            if next_process:
                self.ready_queue.remove(next_process)
                
                from core.scheduler_base import CONTEXT_SWITCH_OVERHEAD
                if self.previous_process is not None and self.previous_process.pid != next_process.pid and CONTEXT_SWITCH_OVERHEAD > 0:
                    self.stats.context_switches += 1
                    self.log_event(f"Context Switch: P{self.previous_process.pid} → P{next_process.pid}")
                    self.add_to_gantt_chart(-2, self.current_time,
                                          self.current_time + CONTEXT_SWITCH_OVERHEAD,
                                          ProcessState.CONTEXT_SWITCHING)
                    self.in_context_switch = True
                    self.context_switch_remaining = CONTEXT_SWITCH_OVERHEAD
                    self.context_switch_target = next_process
                    self.previous_process = next_process
                    self.current_time += 1
                    return False
                else:
                    self.running_process = next_process
                    self.running_process.state = ProcessState.RUNNING
                    if self.previous_process is None:
                        self.log_event(f"P{next_process.pid} → Running")
                    self.previous_process = next_process
                    self.execution_start = self.current_time
        
        if self.running_process:
            process = self.running_process
            
            if self.execution_start is None:
                self.execution_start = self.current_time
            
            burst_completed = process.execute(1)
            self.stats.cpu_busy_time += 1
            
            if burst_completed:
                self.add_to_gantt_chart(process.pid, self.execution_start,
                                       self.current_time + 1, ProcessState.RUNNING)
                self.execution_start = None
                
                process.complete_current_burst()
                
                if process.is_completed():
                    process.finish_time = self.current_time + 1
                    self.terminate_process(process)
                    self.running_process = None
                elif process.is_io_burst():
                    self.start_io_operation(process)
                    self.running_process = None
        else:
            self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1,
                                   ProcessState.READY)
        
        self.current_time += 1
        
        if self.current_time > 10000:
            self.log_event("WARNING: Simulation timeout")
            return True
        
        return self.is_simulation_complete()
    
    def run(self, verbose: bool = False) -> Dict:
        """EDF 스케줄링 실행"""
        self.log_event(f"===== {self.name} Scheduling Started =====")
        
        if not self.processes:
            self.log_event("No real-time processes found")
            return self.get_results()
        
        execution_start = None
        
        while len(self.terminated_processes) < len(self.processes):
            # 1. 프로세스 도착 처리
            self.handle_process_arrival()
            
            # 2. I/O 완료 처리
            self.handle_io_completion()
            
            # 3. 선점 검사
            if self.check_preemption():
                if execution_start is not None:
                    self.add_to_gantt_chart(self.running_process.pid, execution_start,
                                           self.current_time, ProcessState.RUNNING)
                    execution_start = None
                
                self.running_process.state = ProcessState.READY
                self.running_process.last_ready_time = self.current_time
                self.ready_queue.append(self.running_process)
                self.log_event(f"P{self.running_process.pid} preempted by earlier deadline → Ready Queue")
                self.running_process = None
            
            # 4. 프로세스 선택
            if self.running_process is None:
                next_process = self.select_next_process()
                if next_process:
                    self.ready_queue.remove(next_process)
                    self.context_switch(next_process)
                    execution_start = self.current_time
            
            # 5. CPU 실행
            if self.running_process:
                process = self.running_process
                
                if execution_start is None:
                    execution_start = self.current_time
                
                burst_completed = process.execute(1)
                self.stats.cpu_busy_time += 1
                
                if burst_completed:
                    self.add_to_gantt_chart(process.pid, execution_start,
                                           self.current_time + 1, ProcessState.RUNNING)
                    execution_start = None
                    
                    process.complete_current_burst()
                    
                    if process.is_completed():
                        process.finish_time = self.current_time + 1
                        self.terminate_process(process)
                        self.running_process = None
                    elif process.is_io_burst():
                        self.start_io_operation(process)
                        self.running_process = None
            else:
                self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1,
                                       ProcessState.READY)
            
            self.current_time += 1
            
            if self.current_time > 10000:
                self.log_event("WARNING: Simulation timeout")
                break
        
        self.log_event(f"===== {self.name} Scheduling Completed =====")
        
        if verbose:
            for log in self.event_log:
                print(log)
        
        return self.get_results()
