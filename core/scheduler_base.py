"""
스케줄러 기본 프레임워크 및 이벤트 관리
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from .process import Process, ProcessState

# 문맥교환 오버헤드 설정 (시간 단위)
CONTEXT_SWITCH_OVERHEAD = 1


class InterruptType(Enum):
    """인터럽트 타입"""
    TIMER = "Timer"  # 타임 슬라이스 종료
    IO_REQUEST = "I/O Request"  # I/O 요청
    IO_COMPLETE = "I/O Complete"  # I/O 완료
    PREEMPTION = "Preemption"  # 선점
    PROCESS_ARRIVAL = "Process Arrival"  # 프로세스 도착


@dataclass
class Event:
    """시뮬레이션 이벤트"""
    time: int
    event_type: InterruptType
    process: Optional[Process] = None
    description: str = ""


@dataclass
class GanttEntry:
    """Gantt Chart 엔트리"""
    pid: int
    start_time: int
    end_time: int
    state: ProcessState  # Running, Waiting 등


class SchedulerStats:
    """스케줄링 통계"""
    
    def __init__(self):
        self.total_waiting_time = 0
        self.total_turnaround_time = 0
        self.total_response_time = 0
        self.context_switches = 0
        self.cpu_busy_time = 0
        self.total_simulation_time = 0
        self.process_count = 0
        
    def calculate_averages(self):
        """평균 계산"""
        if self.process_count == 0:
            return {
                'avg_waiting_time': 0,
                'avg_turnaround_time': 0,
                'avg_response_time': 0,
                'cpu_utilization': 0,
                'context_switches': 0
            }
        
        return {
            'avg_waiting_time': self.total_waiting_time / self.process_count,
            'avg_turnaround_time': self.total_turnaround_time / self.process_count,
            'avg_response_time': self.total_response_time / self.process_count,
            'cpu_utilization': (self.cpu_busy_time / self.total_simulation_time * 100) 
                               if self.total_simulation_time > 0 else 0,
            'context_switches': self.context_switches
        }


class BaseScheduler:
    """
    기본 스케줄러 클래스
    모든 스케줄링 알고리즘의 공통 기능 제공
    """
    
    def __init__(self, processes: List[Process], name: str = "Base Scheduler"):
        self.processes = processes
        self.name = name
        self.current_time = 0
        self.ready_queue: List[Process] = []
        self.waiting_queue: List[Process] = []
        self.running_process: Optional[Process] = None
        self.previous_process: Optional[Process] = None  # 이전 실행 프로세스 추적
        self.terminated_processes: List[Process] = []
        
        # 문맥교환 추적
        self.in_context_switch = False
        self.context_switch_remaining = 0
        self.context_switch_target: Optional[Process] = None
        
        # Gantt Chart 데이터
        self.gantt_chart: List[GanttEntry] = []
        
        # 통계
        self.stats = SchedulerStats()
        
        # 이벤트 로그
        self.event_log: List[str] = []
        
        # I/O 완료 큐 (시간, 프로세스)
        self.io_completion_queue: List[Tuple[int, Process]] = []
        
    def log_event(self, message: str):
        """이벤트 로그 기록"""
        log_entry = f"[T={self.current_time:3d}] {message}"
        self.event_log.append(log_entry)
        
    def add_to_gantt_chart(self, pid: int, start: int, end: int, state: ProcessState):
        """Gantt Chart에 엔트리 추가"""
        if start < end:  # 유효한 시간 구간만 추가
            self.gantt_chart.append(GanttEntry(pid, start, end, state))
    
    def handle_process_arrival(self):
        """프로세스 도착 처리"""
        for process in self.processes:
            if process.arrival_time == self.current_time:
                process.state = ProcessState.READY
                process.last_ready_time = self.current_time
                self.ready_queue.append(process)
                self.log_event(f"P{process.pid} arrived → Ready Queue")
    
    def handle_io_completion(self):
        """I/O 완료 처리"""
        completed_ios = []
        for io_time, process in self.io_completion_queue:
            if io_time <= self.current_time:
                process.complete_current_burst()  # I/O 버스트 완료
                
                if not process.is_completed():
                    process.state = ProcessState.READY
                    process.last_ready_time = self.current_time
                    self.ready_queue.append(process)
                    self.log_event(f"P{process.pid} I/O completed → Ready Queue")
                else:
                    self.terminate_process(process)
                
                completed_ios.append((io_time, process))
        
        # 완료된 I/O 제거
        for io_entry in completed_ios:
            self.io_completion_queue.remove(io_entry)
    
    def start_io_operation(self, process: Process):
        """I/O 작업 시작"""
        if not process.is_io_burst():
            raise ValueError("I/O 버스트가 아닌 상태에서 I/O 작업을 시작할 수 없습니다.")
        
        process.state = ProcessState.WAITING
        io_duration = process.remaining_burst_time
        io_completion_time = self.current_time + io_duration
        self.io_completion_queue.append((io_completion_time, process))
        self.waiting_queue.append(process)
        
        # Gantt Chart에 I/O 기록
        self.add_to_gantt_chart(process.pid, self.current_time, 
                               io_completion_time, ProcessState.WAITING)
        
        self.log_event(f"P{process.pid} → I/O (duration={io_duration}) → Waiting")
    
    def context_switch(self, new_process: Optional[Process]):
        """
        문맥 전환 수행
        
        Args:
            new_process: 새로 실행할 프로세스 (None이면 CPU 유휴 상태)
        """
        # 문맥 전환 카운팅: 실행 중인 프로세스가 변경될 때마다 카운트
        # 단, 같은 프로세스가 계속 실행되는 경우는 제외
        needs_context_switch = False
        
        if self.previous_process is not None and new_process is not None:
            if self.previous_process.pid != new_process.pid:
                needs_context_switch = True
                self.stats.context_switches += 1
                self.log_event(f"Context Switch: P{self.previous_process.pid} → P{new_process.pid}")
                
                # 문맥교환 오버헤드 기록 (Gantt Chart)
                if CONTEXT_SWITCH_OVERHEAD > 0:
                    self.add_to_gantt_chart(
                        -2,  # 특수 PID: 문맥교환
                        self.current_time,
                        self.current_time + CONTEXT_SWITCH_OVERHEAD,
                        ProcessState.CONTEXT_SWITCHING
                    )
                    # 문맥교환 시간만큼 시간 증가
                    self.current_time += CONTEXT_SWITCH_OVERHEAD
        elif self.previous_process is None and new_process is not None:
            # 첫 프로세스 시작 (문맥 전환으로 카운트하지 않음)
            pass
        elif self.previous_process is not None and new_process is None:
            # 프로세스가 I/O로 가거나 종료 (다음에 다른 프로세스 실행 시 카운트)
            pass
        
        # 이전 프로세스 업데이트 (None이 아닌 경우에만)
        if new_process is not None:
            self.previous_process = new_process
        
        self.running_process = new_process
        
        if new_process:
            new_process.state = ProcessState.RUNNING
            if new_process.start_time is None:
                new_process.start_time = self.current_time
                new_process.response_time = self.current_time - new_process.arrival_time
            
            self.log_event(f"P{new_process.pid} → Running")
    
    def terminate_process(self, process: Process):
        """프로세스 종료 처리"""
        process.state = ProcessState.TERMINATED
        # finish_time은 호출 전에 이미 설정되어야 함
        if process.finish_time is None:
            process.finish_time = self.current_time
        process.turnaround_time = process.finish_time - process.arrival_time
        process.waiting_time = process.turnaround_time - process.get_total_burst_time()
        
        self.terminated_processes.append(process)
        self.log_event(f"P{process.pid} → Terminated (WT={process.waiting_time}, TT={process.turnaround_time})")
    
    def update_statistics(self):
        """최종 통계 업데이트"""
        self.stats.total_simulation_time = self.current_time
        self.stats.process_count = len(self.terminated_processes)
        
        for process in self.terminated_processes:
            self.stats.total_waiting_time += process.waiting_time
            self.stats.total_turnaround_time += process.turnaround_time
            if process.response_time is not None:
                self.stats.total_response_time += process.response_time
    
    def select_next_process(self) -> Optional[Process]:
        """
        다음 실행할 프로세스 선택 (하위 클래스에서 구현)
        
        Returns:
            선택된 프로세스 또는 None
        """
        raise NotImplementedError("Subclasses must implement select_next_process()")
    
    def is_simulation_complete(self) -> bool:
        """시뮬레이션 완료 여부 확인"""
        return len(self.terminated_processes) >= len(self.processes)
    
    def get_current_snapshot(self) -> Dict:
        """
        현재 시뮬레이션 상태 스냅샷 반환 (실시간 뷰어용)
        
        Returns:
            현재 상태 딕셔너리
        """
        return {
            'time': self.current_time,
            'running': self.running_process,
            'ready_queue': list(self.ready_queue),
            'waiting_queue': list(self.waiting_queue),
            'terminated': list(self.terminated_processes),
            'context_switches': self.stats.context_switches,
            'cpu_busy_time': self.stats.cpu_busy_time,
            'latest_gantt_entry': self.gantt_chart[-1] if self.gantt_chart else None,
            'latest_log': self.event_log[-1] if self.event_log else ""
        }
    
    def run(self, verbose: bool = False) -> Dict:
        """
        스케줄링 시뮬레이션 실행
        
        Args:
            verbose: 상세 로그 출력 여부
            
        Returns:
            시뮬레이션 결과 딕셔너리
        """
        raise NotImplementedError("Subclasses must implement run()")
    
    def get_results(self) -> Dict:
        """
        시뮬레이션 결과 반환
        
        Returns:
            결과 딕셔너리 (통계, Gantt Chart, 로그 등)
        """
        self.update_statistics()
        
        return {
            'algorithm': self.name,
            'statistics': self.stats.calculate_averages(),
            'gantt_chart': self.gantt_chart,
            'event_log': self.event_log,
            'processes': self.terminated_processes
        }
