"""
FCFS (First-Come, First-Served) Scheduler
비선점형: 먼저 도착한 프로세스를 먼저 처리
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
    
    def select_next_process(self) -> Optional[Process]:
        """도착 시간이 가장 빠른 프로세스 선택"""
        if not self.ready_queue:
            return None
        
        # Ready 큐의 첫 번째 프로세스 선택 (FIFO)
        return self.ready_queue[0]
    
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
