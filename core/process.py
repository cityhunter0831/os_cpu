"""
프로세스 및 PCB (Process Control Block) 관리 모듈
"""

from enum import Enum
from typing import List, Optional
from copy import deepcopy


class ProcessState(Enum):
    """프로세스 상태"""
    READY = "Ready"
    RUNNING = "Running"
    WAITING = "Waiting"
    TERMINATED = "Terminated"
    CONTEXT_SWITCHING = "Context Switching"


class Process:
    """
    프로세스 제어 블록 (PCB)
    각 프로세스의 정보와 상태를 관리
    """
    
    def __init__(self, pid: int, arrival_time: int, priority: int, 
                 execution_pattern: List[int], period: int = 0, deadline: int = 0):
        """
        프로세스 초기화
        
        Args:
            pid: 프로세스 ID
            arrival_time: 도착 시간
            priority: 우선순위 (낮을수록 높은 우선순위)
            execution_pattern: 실행 패턴 [CPU_burst1, IO_burst1, CPU_burst2, ...]
            period: 주기 (실시간 프로세스용)
            deadline: 마감시한 (실시간 프로세스용)
        """
        self.pid = pid
        self.arrival_time = arrival_time
        self.initial_priority = priority  # 초기 우선순위 저장
        self.priority = priority
        self.execution_pattern = execution_pattern
        self.period = period
        self.deadline = deadline
        self.absolute_deadline = arrival_time + deadline if deadline > 0 else float('inf')
        
        # 실행 상태 추적
        self.state = ProcessState.READY
        self.current_burst_index = 0  # 현재 처리 중인 버스트 인덱스
        self.remaining_burst_time = execution_pattern[0] if execution_pattern else 0
        
        # 통계 정보
        self.start_time: Optional[int] = None  # 첫 실행 시간
        self.finish_time: Optional[int] = None  # 완료 시간
        self.waiting_time = 0  # 대기 시간
        self.turnaround_time = 0  # 반환 시간
        self.response_time: Optional[int] = None  # 응답 시간
        
        # 대기 시간 추적 (Aging용)
        self.time_in_ready_queue = 0  # 현재 Ready 구간에서 대기한 시간
        self.last_ready_time = arrival_time  # 마지막으로 Ready 상태가 된 시간
        self.total_waiting_time_for_aging = 0  # 누적 대기 시간 (Aging 계산용)
        
        # MLQ용 큐 레벨
        self.queue_level = 0  # 0: 최상위, 1: 중간, 2: 최하위
        self.time_slice_used = 0  # 현재 큐에서 사용한 타임 슬라이스
        
    def get_total_burst_time(self) -> int:
        """총 CPU 버스트 시간 계산 (I/O 제외)"""
        return sum(self.execution_pattern[i] for i in range(0, len(self.execution_pattern), 2))
    
    def get_remaining_time(self) -> int:
        """
        남은 CPU 시간 계산 - SJF/SRTF용
        
        SRTF with I/O: 현재 CPU 버스트의 남은 시간만 반환
        (I/O 이후의 CPU 버스트는 고려하지 않음)
        """
        # 현재 CPU 버스트의 남은 시간만 반환
        if self.is_cpu_burst():
            return self.remaining_burst_time
        else:
            # I/O 버스트 중이면 0 반환
            return 0
    
    def is_cpu_burst(self) -> bool:
        """현재 버스트가 CPU 버스트인지 확인"""
        return self.current_burst_index % 2 == 0
    
    def is_io_burst(self) -> bool:
        """현재 버스트가 I/O 버스트인지 확인"""
        return self.current_burst_index % 2 == 1
    
    def execute(self, time_units: int = 1) -> bool:
        """
        프로세스 실행 (CPU 버스트 시간 감소)
        
        Args:
            time_units: 실행할 시간 단위
            
        Returns:
            버스트가 완료되었는지 여부
        """
        if not self.is_cpu_burst():
            raise ValueError("CPU 버스트가 아닌 상태에서는 실행할 수 없습니다.")
        
        self.remaining_burst_time -= time_units
        
        if self.remaining_burst_time <= 0:
            # 현재 버스트 완료
            return True
        return False
    
    def complete_current_burst(self):
        """현재 버스트 완료 처리 및 다음 버스트로 이동"""
        self.current_burst_index += 1
        
        if self.current_burst_index < len(self.execution_pattern):
            self.remaining_burst_time = self.execution_pattern[self.current_burst_index]
        else:
            # 모든 버스트 완료
            self.state = ProcessState.TERMINATED
            self.remaining_burst_time = 0
    
    def is_completed(self) -> bool:
        """프로세스가 완료되었는지 확인"""
        return self.current_burst_index >= len(self.execution_pattern)
    
    def update_waiting_time(self, current_time: int):
        """대기 시간 업데이트 (Aging용)"""
        if self.state == ProcessState.READY:
            self.time_in_ready_queue = current_time - self.last_ready_time
            self.total_waiting_time_for_aging += 1  # 누적 대기 시간 증가
    
    def apply_aging(self, aging_factor: int = 10):
        """
        에이징 기법 적용: 누적 대기 시간에 따라 우선순위 상승
        공식: 새 우선순위 = 기존 우선순위 - (누적 대기 시간 / aging_factor)
        
        Args:
            aging_factor: 에이징 인수 (기본값 10)
        """
        if self.total_waiting_time_for_aging > 0:
            priority_boost = self.total_waiting_time_for_aging // aging_factor
            self.priority = max(0, self.initial_priority - priority_boost)
    
    def reset_to_initial_priority(self):
        """우선순위를 초기값으로 리셋 (Aging도 리셋)"""
        self.priority = self.initial_priority
        self.total_waiting_time_for_aging = 0
    
    def __repr__(self):
        return f"P{self.pid}[{self.state.value}]"
    
    def __str__(self):
        return f"Process {self.pid}: State={self.state.value}, Priority={self.priority}, " \
               f"Remaining={self.get_remaining_time()}"


def create_process_copy(process: Process) -> Process:
    """
    프로세스의 깊은 복사본 생성
    각 스케줄링 알고리즘 시뮬레이션을 독립적으로 수행하기 위함
    """
    return deepcopy(process)
