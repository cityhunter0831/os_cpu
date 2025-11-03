"""
입력 데이터 파서 및 프로세스 생성 모듈
"""

import csv
import random
from typing import List, Tuple
from core.process import Process


class InputParser:
    """입력 파일 파서"""
    
    @staticmethod
    def parse_file(filename: str) -> List[Process]:
        """
        CSV 파일에서 프로세스 정보 읽기
        
        파일 형식: PID,생성시간,우선순위,실행패턴,주기,마감시한
        예: 1,0,3,"15",0,0
        
        Args:
            filename: 입력 파일 경로
            
        Returns:
            프로세스 리스트
        """
        processes = []
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # 주석 및 빈 줄 제거
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        parts = InputParser._parse_line(line)
                        if parts:
                            process = InputParser._create_process_from_parts(parts)
                            processes.append(process)
                    except Exception as e:
                        print(f"경고: 라인 파싱 실패: {line}")
                        print(f"오류: {e}")
                        continue
            
            print(f"{filename}에서 {len(processes)}개의 프로세스를 성공적으로 로드했습니다")
            return processes
            
        except FileNotFoundError:
            print(f"오류: 파일 '{filename}'을 찾을 수 없습니다")
            return []
        except Exception as e:
            print(f"파일 읽기 오류: {e}")
            return []
    
    @staticmethod
    def _parse_line(line: str) -> List:
        """CSV 라인 파싱 (따옴표 처리 포함)"""
        parts = []
        current = ""
        in_quotes = False
        
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                parts.append(current.strip())
                current = ""
            else:
                current += char
        
        if current:
            parts.append(current.strip())
        
        return parts
    
    @staticmethod
    def _create_process_from_parts(parts: List[str]) -> Process:
        """파싱된 부분에서 프로세스 객체 생성"""
        if len(parts) < 6:
            raise ValueError(f"잘못된 형식: 6개 필드가 필요하지만 {len(parts)}개만 있습니다")
        
        # 입력 검증
        try:
            pid = int(parts[0])
            arrival_time = int(parts[1])
            priority = int(parts[2])
            period = int(parts[4])
            deadline = int(parts[5])
        except ValueError as e:
            raise ValueError(f"숫자 필드 변환 오류: {e}")
        
        # 검증: 음수 값 체크
        if pid <= 0:
            raise ValueError(f"PID는 양수여야 합니다: {pid}")
        if arrival_time < 0:
            raise ValueError(f"도착 시간은 0 이상이어야 합니다: {arrival_time}")
        if priority < 0:
            raise ValueError(f"우선순위는 0 이상이어야 합니다: {priority}")
        if period < 0 or deadline < 0:
            raise ValueError(f"주기와 마감시한은 0 이상이어야 합니다")
        
        # 실행 패턴 파싱
        execution_pattern_str = parts[3].strip('"\'')
        if not execution_pattern_str:
            raise ValueError("실행 패턴이 비어있습니다")
        
        try:
            execution_pattern = [int(x.strip()) for x in execution_pattern_str.split(',') if x.strip()]
        except ValueError as e:
            raise ValueError(f"실행 패턴 파싱 오류: {e}")
        
        # 검증: 실행 패턴은 CPU 버스트로 시작하고 끝나야 함
        if len(execution_pattern) == 0:
            raise ValueError("실행 패턴이 비어있습니다")
        
        # 검증: 모든 버스트 시간은 양수여야 함
        if any(t <= 0 for t in execution_pattern):
            raise ValueError("모든 버스트 시간은 양수여야 합니다")
        
        return Process(pid, arrival_time, priority, execution_pattern, period, deadline)
    
    @staticmethod
    def generate_random_processes(num_processes: int = 10, 
                                 max_arrival: int = 20,
                                 max_burst: int = 30,
                                 max_io: int = 20,
                                 seed: int = None) -> List[Process]:
        """
        랜덤 프로세스 생성
        
        Args:
            num_processes: 생성할 프로세스 수
            max_arrival: 최대 도착 시간
            max_burst: 최대 CPU 버스트 시간
            max_io: 최대 I/O 시간
            seed: 랜덤 시드
            
        Returns:
            프로세스 리스트
        """
        if seed is not None:
            random.seed(seed)
        
        processes = []
        
        for i in range(1, num_processes + 1):
            pid = i
            arrival_time = random.randint(0, max_arrival)
            priority = random.randint(1, 10)
            
            # 실행 패턴 생성 (CPU-bound 또는 I/O-bound)
            is_io_bound = random.random() < 0.4  # 40% 확률로 I/O bound
            
            if is_io_bound:
                # I/O bound: 짧은 CPU 버스트와 긴 I/O 버스트
                num_bursts = random.randint(2, 4)
                execution_pattern = []
                for j in range(num_bursts):
                    cpu_burst = random.randint(2, max_burst // 3)
                    execution_pattern.append(cpu_burst)
                    if j < num_bursts - 1:  # 마지막이 아니면 I/O 추가
                        io_burst = random.randint(5, max_io)
                        execution_pattern.append(io_burst)
            else:
                # CPU bound: 긴 CPU 버스트
                num_bursts = random.randint(1, 3)
                execution_pattern = []
                for j in range(num_bursts):
                    cpu_burst = random.randint(max_burst // 2, max_burst)
                    execution_pattern.append(cpu_burst)
                    if j < num_bursts - 1:
                        io_burst = random.randint(2, max_io // 2)
                        execution_pattern.append(io_burst)
            
            # 실시간 프로세스 (20% 확률)
            period = 0
            deadline = 0
            if random.random() < 0.2:
                period = random.choice([10, 15, 20, 25, 30])
                deadline = period
            
            process = Process(pid, arrival_time, priority, execution_pattern, period, deadline)
            processes.append(process)
        
        print(f"{num_processes}개의 랜덤 프로세스를 생성했습니다")
        return processes
    
    @staticmethod
    def save_processes_to_file(processes: List[Process], filename: str):
        """
        프로세스 리스트를 파일로 저장
        
        Args:
            processes: 저장할 프로세스 리스트
            filename: 출력 파일 경로
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("# OS Scheduler Project Input Data\n")
                f.write("# Format: PID,ArrivalTime,Priority,ExecutionPattern,Period,Deadline\n\n")
                
                for process in processes:
                    pattern_str = ','.join(str(x) for x in process.execution_pattern)
                    line = f"{process.pid},{process.arrival_time},{process.initial_priority}," \
                           f'"{pattern_str}",{process.period},{process.deadline}\n'
                    f.write(line)
            
            print(f"{len(processes)}개의 프로세스를 {filename}에 성공적으로 저장했습니다")
            
        except Exception as e:
            print(f"파일 저장 오류: {e}")
    
    @staticmethod
    def print_process_summary(processes: List[Process]):
        """프로세스 요약 정보 출력"""
        print("\n" + "="*100)
        print("프로세스 요약")
        print("="*100)
        print(f"{'PID':<6} {'도착시간':>8} {'우선순위':>10} {'총 CPU':>12} "
              f"{'I/O 유무':>10} {'주기':>8} {'마감시한':>10}")
        print("-"*100)
        
        for p in sorted(processes, key=lambda x: x.pid):
            total_cpu = p.get_total_burst_time()
            has_io = '있음' if len(p.execution_pattern) > 1 else '없음'
            period_str = str(p.period) if p.period > 0 else '-'
            deadline_str = str(p.deadline) if p.deadline > 0 else '-'
            
            print(f"{p.pid:<6} {p.arrival_time:>8} {p.initial_priority:>10} "
                  f"{total_cpu:>12} {has_io:>10} {period_str:>8} {deadline_str:>10}")
        
        print("="*100 + "\n")
        
        # 통계
        cpu_bound = sum(1 for p in processes if len(p.execution_pattern) == 1)
        io_bound = len(processes) - cpu_bound
        rt_processes = sum(1 for p in processes if p.period > 0)
        
        print(f"전체 프로세스: {len(processes)}개")
        print(f"  - CPU 중심: {cpu_bound}개")
        print(f"  - I/O 중심: {io_bound}개")
        print(f"  - 실시간: {rt_processes}개")
        print()
