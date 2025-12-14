"""
기본 스케줄링 알고리즘 구현
- FCFS (First-Come, First-Served)
- SJF (Shortest Job First - Preemptive / SRTF)
- Round Robin
"""

from typing import List, Optional, Dict
from core.process import Process, ProcessState, create_process_copy
from core.scheduler_base import BaseScheduler


class FCFSScheduler(BaseScheduler):
    """
    FCFS (First-Come, First-Served) 스케줄러
    비선점형: 먼저 도착한 프로세스를 먼저 처리
    """
    
    def __init__(self, processes: List[Process]):
        super().__init__([create_process_copy(p) for p in processes], "FCFS")
        self.execution_start = None
    
    def select_next_process(self) -> Optional[Process]:
        """도착 시간이 가장 빠른 프로세스 선택"""
        if not self.ready_queue:
            return None
        
        # Ready 큐의 첫 번째 프로세스 선택 (FIFO)
        return self.ready_queue[0]
    
    def execute_one_step(self) -> bool:
        """
        한 시간 단위 실행 (실시간 뷰어용)
        
        Returns:
            시뮬레이션 완료 여부
        """
        if self.is_simulation_complete():
            return True
        
        # 문맥교환 중이면 오버헤드 처리
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
        
        # 1. 프로세스 도착 처리
        self.handle_process_arrival()
        
        # 2. I/O 완료 처리
        self.handle_io_completion()
        
        # 3. 현재 실행 중인 프로세스가 없으면 새 프로세스 선택
        if self.running_process is None:
            next_process = self.select_next_process()
            if next_process:
                self.ready_queue.remove(next_process)
                
                # 문맥교환 시작
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
        
        # 4. CPU 실행
        if self.running_process:
            process = self.running_process
            
            if self.execution_start is None:
                self.execution_start = self.current_time
            
            # CPU 버스트 완료까지 실행
            burst_completed = process.execute(1)
            self.stats.cpu_busy_time += 1
            
            if burst_completed:
                execution_end = self.current_time + 1
                self.add_to_gantt_chart(process.pid, self.execution_start, 
                                       execution_end, ProcessState.RUNNING)
                self.execution_start = None
                
                process.complete_current_burst()
                
                if process.is_completed():
                    # 프로세스 종료
                    process.finish_time = self.current_time + 1
                    self.terminate_process(process)
                    self.running_process = None
                elif process.is_io_burst():
                    # I/O 작업 시작
                    self.start_io_operation(process)
                    self.running_process = None
        else:
            # CPU 유휴 상태
            self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1, 
                                   ProcessState.READY)
        
        self.current_time += 1
        
        # 무한 루프 방지
        if self.current_time > 10000:
            self.log_event("WARNING: Simulation timeout")
            return True
        
        return self.is_simulation_complete()
    
    def run(self, verbose: bool = False) -> Dict:
        """FCFS 스케줄링 실행"""
        self.log_event(f"===== {self.name} Scheduling Started =====")
        
        execution_start = None
        
        while len(self.terminated_processes) < len(self.processes):
            # 1. 프로세스 도착 처리
            self.handle_process_arrival()
            
            # 2. I/O 완료 처리
            self.handle_io_completion()
            
            # 3. 현재 실행 중인 프로세스가 없으면 새 프로세스 선택
            if self.running_process is None:
                next_process = self.select_next_process()
                if next_process:
                    self.ready_queue.remove(next_process)
                    self.context_switch(next_process)
                    execution_start = self.current_time
            
            # 4. CPU 실행
            if self.running_process:
                process = self.running_process
                
                if execution_start is None:
                    execution_start = self.current_time
                
                # CPU 버스트 완료까지 실행
                burst_completed = process.execute(1)
                self.stats.cpu_busy_time += 1
                
                if burst_completed:
                    execution_end = self.current_time + 1
                    self.add_to_gantt_chart(process.pid, execution_start, 
                                           execution_end, ProcessState.RUNNING)
                    execution_start = None
                    
                    process.complete_current_burst()
                    
                    if process.is_completed():
                        # 프로세스 종료 (finish_time은 실행 완료 시점)
                        process.finish_time = self.current_time + 1
                        self.terminate_process(process)
                        self.running_process = None
                    elif process.is_io_burst():
                        # I/O 작업 시작
                        self.start_io_operation(process)
                        self.running_process = None
            else:
                # CPU 유휴 상태
                self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1, 
                                       ProcessState.READY)
            
            self.current_time += 1
            
            # 무한 루프 방지
            if self.current_time > 10000:
                self.log_event("WARNING: Simulation timeout")
                break
        
        self.log_event(f"===== {self.name} Scheduling Completed =====")
        
        if verbose:
            for log in self.event_log:
                print(log)
        
        return self.get_results()


class SJFScheduler(BaseScheduler):
    """
    SJF (Shortest Job First) 스케줄러 - 선점형 (SRTF: Shortest Remaining Time First)
    남은 실행 시간이 가장 짧은 프로세스를 우선 처리
    """
    
    def __init__(self, processes: List[Process]):
        super().__init__([create_process_copy(p) for p in processes], "SJF (Preemptive/SRTF)")
        self.execution_start = None
    
    def select_next_process(self) -> Optional[Process]:
        """남은 CPU 시간이 가장 짧은 프로세스 선택"""
        if not self.ready_queue:
            return None
        
        # 남은 시간이 가장 짧은 프로세스 선택
        return min(self.ready_queue, key=lambda p: (p.get_remaining_time(), p.arrival_time))
    
    def check_preemption(self) -> bool:
        """
        선점 가능 여부 확인
        
        Returns:
            선점이 필요한 경우 True
        """
        if not self.running_process or not self.ready_queue:
            return False
        
        # Ready 큐에서 가장 짧은 남은 시간을 가진 프로세스
        shortest_process = min(self.ready_queue, 
                              key=lambda p: (p.get_remaining_time(), p.arrival_time))
        
        # 현재 실행 중인 프로세스보다 남은 시간이 짧으면 선점
        if shortest_process.get_remaining_time() < self.running_process.get_remaining_time():
            return True
        
        return False
    
    def execute_one_step(self) -> bool:
        """한 시간 단위 실행 (실시간 뷰어용)"""
        if self.is_simulation_complete():
            return True
        
        # 문맥교환 중이면 오버헤드 처리
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
        
        # 1. 프로세스 도착 처리
        self.handle_process_arrival()
        
        # 2. I/O 완료 처리
        self.handle_io_completion()
        
        # 3. 선점 검사 (실행 중인 프로세스가 있을 때만)
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
        
        # 4. 프로세스 선택 및 문맥교환 시작
        if self.running_process is None:
            next_process = self.select_next_process()
            if next_process:
                self.ready_queue.remove(next_process)
                
                # 문맥교환 시작
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
        
        # 5. CPU 실행
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
        """SJF (Preemptive) 스케줄링 실행"""
        self.log_event(f"===== {self.name} Scheduling Started =====")
        
        execution_start = None
        
        while len(self.terminated_processes) < len(self.processes):
            # 1. 프로세스 도착 처리
            self.handle_process_arrival()
            
            # 2. I/O 완료 처리
            self.handle_io_completion()
            
            # 3. 선점 검사
            if self.check_preemption():
                # 현재 프로세스를 Ready 큐로 복귀
                if execution_start is not None:
                    self.add_to_gantt_chart(self.running_process.pid, execution_start,
                                           self.current_time, ProcessState.RUNNING)
                    execution_start = None
                
                self.running_process.state = ProcessState.READY
                self.running_process.last_ready_time = self.current_time
                self.ready_queue.append(self.running_process)
                self.log_event(f"P{self.running_process.pid} preempted → Ready Queue")
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
                # CPU 유휴
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


class RoundRobinScheduler(BaseScheduler):
    """
    Round Robin 스케줄러
    각 프로세스에게 동일한 타임 슬라이스를 할당하고 순환 실행
    """
    
    def __init__(self, processes: List[Process], time_slice: int = 4):
        super().__init__([create_process_copy(p) for p in processes], 
                        f"Round Robin (q={time_slice})")
        self.time_slice = time_slice
        self.current_time_slice = 0
        self.execution_start = None
    
    def select_next_process(self) -> Optional[Process]:
        """Ready 큐의 첫 번째 프로세스 선택 (FIFO)"""
        if not self.ready_queue:
            return None
        return self.ready_queue[0]
    
    def execute_one_step(self) -> bool:
        """한 시간 단위 실행 (실시간 뷰어용)"""
        if self.is_simulation_complete():
            return True
        
        # 문맥교환 중이면 오버헤드 처리
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
        
        # 1. 프로세스 도착 처리
        self.handle_process_arrival()
        
        # 2. I/O 완료 처리
        self.handle_io_completion()
        
        # 3. 타임 슬라이스 만료 확인
        if (self.running_process and 
            self.current_time_slice >= self.time_slice):
            if self.execution_start is not None:
                self.add_to_gantt_chart(self.running_process.pid, self.execution_start,
                                       self.current_time, ProcessState.RUNNING)
                self.execution_start = None
            
            self.log_event(f"P{self.running_process.pid} time slice expired → Ready Queue")
            self.running_process.state = ProcessState.READY
            self.running_process.last_ready_time = self.current_time
            self.ready_queue.append(self.running_process)
            self.running_process = None
            self.current_time_slice = 0
        
        # 4. 프로세스 선택 및 문맥교환 시작
        if self.running_process is None:
            next_process = self.select_next_process()
            if next_process:
                self.ready_queue.remove(next_process)
                
                # 문맥교환 시작
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
                    self.current_time_slice = 0
                    self.execution_start = self.current_time
        
        # 5. CPU 실행
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
        """Round Robin 스케줄링 실행"""
        self.log_event(f"===== {self.name} Scheduling Started =====")
        
        execution_start = None
        
        while len(self.terminated_processes) < len(self.processes):
            # 1. 프로세스 도착 처리
            self.handle_process_arrival()
            
            # 2. I/O 완료 처리
            self.handle_io_completion()
            
            # 3. 타임 슬라이스 만료 확인
            if (self.running_process and 
                self.current_time_slice >= self.time_slice):
                # 타이머 인터럽트 발생
                if execution_start is not None:
                    self.add_to_gantt_chart(self.running_process.pid, execution_start,
                                           self.current_time, ProcessState.RUNNING)
                    execution_start = None
                
                self.log_event(f"P{self.running_process.pid} time slice expired → Ready Queue")
                self.running_process.state = ProcessState.READY
                self.running_process.last_ready_time = self.current_time
                self.ready_queue.append(self.running_process)
                self.running_process = None
                self.current_time_slice = 0
            
            # 4. 프로세스 선택
            if self.running_process is None:
                next_process = self.select_next_process()
                if next_process:
                    self.ready_queue.remove(next_process)
                    self.context_switch(next_process)
                    self.current_time_slice = 0
                    execution_start = self.current_time
            
            # 5. CPU 실행
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
                # CPU 유휴
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
