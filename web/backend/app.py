"""
CPU 스케줄러 시뮬레이터 - FastAPI 백엔드
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import sys
import os

# 상위 디렉토리의 모듈 import를 위한 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.process import Process, ProcessState
from schedulers import (
    FCFSScheduler, SJFScheduler, RoundRobinScheduler,
    PriorityScheduler, PriorityAgingScheduler, MLQScheduler,
    RateMonotonicScheduler, EDFScheduler
)
import core.scheduler_base as scheduler_base

app = FastAPI(
    title="CPU Scheduler Simulator",
    description="운영체제 CPU 스케줄링 알고리즘 시뮬레이터",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 알고리즘 매핑
ALGORITHM_MAP = {
    'FCFS': {'class': FCFSScheduler, 'params': {}},
    'SJF': {'class': SJFScheduler, 'params': {}},
    'RoundRobin': {'class': RoundRobinScheduler, 'params': {'time_slice': 4}},
    'Priority': {'class': PriorityScheduler, 'params': {}},
    'PriorityAging': {'class': PriorityAgingScheduler, 'params': {'aging_factor': 10}},
    'MLQ': {'class': MLQScheduler, 'params': {}},
    'RateMonotonic': {'class': RateMonotonicScheduler, 'params': {}},
    'EDF': {'class': EDFScheduler, 'params': {}},
}


# Pydantic 모델
class ProcessInput(BaseModel):
    pid: int
    arrival_time: int
    priority: int
    execution_pattern: List[int]
    period: int = 0
    deadline: int = 0


class SimulationRequest(BaseModel):
    processes: List[ProcessInput]
    algorithms: List[str]
    context_switch_overhead: int = 1
    time_slice: int = 4


class RealtimeSimulationRequest(BaseModel):
    processes: List[ProcessInput]
    algorithm: str
    context_switch_overhead: int = 1
    time_slice: int = 4


class GanttEntry(BaseModel):
    pid: int
    start_time: int
    end_time: int
    state: str


class ProcessResult(BaseModel):
    pid: int
    arrival_time: int
    burst_time: int
    waiting_time: int
    turnaround_time: int
    response_time: Optional[int]


class SimulationResult(BaseModel):
    algorithm: str
    gantt_chart: List[GanttEntry]
    processes: List[ProcessResult]
    statistics: Dict[str, float]
    event_log: List[str]


def create_process_objects(process_inputs: List[ProcessInput]) -> List[Process]:
    """ProcessInput을 Process 객체로 변환"""
    return [
        Process(
            pid=p.pid,
            arrival_time=p.arrival_time,
            priority=p.priority,
            execution_pattern=p.execution_pattern,
            period=p.period,
            deadline=p.deadline
        )
        for p in process_inputs
    ]


def run_scheduler(processes: List[Process], algorithm: str, 
                  context_switch_overhead: int = 1, time_slice: int = 4) -> Dict:
    """스케줄러 실행 및 결과 반환"""
    if algorithm not in ALGORITHM_MAP:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    
    # 문맥교환 오버헤드 설정
    original_overhead = scheduler_base.CONTEXT_SWITCH_OVERHEAD
    scheduler_base.CONTEXT_SWITCH_OVERHEAD = context_switch_overhead
    
    try:
        algo_info = ALGORITHM_MAP[algorithm]
        params = algo_info['params'].copy()
        
        # Round Robin 타임 슬라이스 설정
        if algorithm == 'RoundRobin':
            params['time_slice'] = time_slice
        
        scheduler = algo_info['class'](processes, **params)
        result = scheduler.run()
        
        # Gantt 차트 변환
        gantt_chart = []
        for entry in result['gantt_chart']:
            gantt_chart.append({
                'pid': entry.pid,
                'start_time': entry.start_time,
                'end_time': entry.end_time,
                'state': entry.state.value if hasattr(entry.state, 'value') else str(entry.state)
            })
        
        # 프로세스 결과 변환
        processes_result = []
        for p in result['processes']:
            processes_result.append({
                'pid': p.pid,
                'arrival_time': p.arrival_time,
                'burst_time': p.get_total_burst_time(),
                'waiting_time': p.waiting_time,
                'turnaround_time': p.turnaround_time,
                'response_time': p.response_time
            })
        
        return {
            'algorithm': result['algorithm'],
            'gantt_chart': gantt_chart,
            'processes': processes_result,
            'statistics': result['statistics'],
            'event_log': result['event_log']
        }
    finally:
        scheduler_base.CONTEXT_SWITCH_OVERHEAD = original_overhead


@app.get("/")
async def root():
    """메인 페이지 - index.html 반환"""
    index_path = os.path.join(os.path.dirname(__file__), '..', 'index.html')
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "CPU Scheduler Simulator API", "version": "1.0.0"}


@app.get("/algorithms")
async def get_algorithms():
    """사용 가능한 알고리즘 목록 반환"""
    return {
        "algorithms": [
            {"id": "FCFS", "name": "FCFS (First-Come, First-Served)", "preemptive": False},
            {"id": "SJF", "name": "SJF (Shortest Job First - Preemptive)", "preemptive": True},
            {"id": "RoundRobin", "name": "Round Robin", "preemptive": True},
            {"id": "Priority", "name": "Priority (Static)", "preemptive": True},
            {"id": "PriorityAging", "name": "Priority with Aging", "preemptive": True},
            {"id": "MLQ", "name": "Multi-Level Queue", "preemptive": True},
            {"id": "RateMonotonic", "name": "Rate Monotonic (RM)", "preemptive": True},
            {"id": "EDF", "name": "Earliest Deadline First (EDF)", "preemptive": True},
        ]
    }


@app.post("/simulate")
async def simulate(request: SimulationRequest):
    """스케줄링 시뮬레이션 실행"""
    try:
        results = []
        
        for algorithm in request.algorithms:
            processes = create_process_objects(request.processes)
            result = run_scheduler(
                processes, 
                algorithm,
                request.context_switch_overhead,
                request.time_slice
            )
            results.append(result)
        
        return {"success": True, "results": results}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/simulate/compare")
async def compare_algorithms(request: SimulationRequest):
    """여러 알고리즘 비교 시뮬레이션"""
    try:
        results = []
        comparison = {
            'algorithms': [],
            'avg_waiting_time': [],
            'avg_turnaround_time': [],
            'avg_response_time': [],
            'cpu_utilization': [],
            'context_switches': []
        }
        
        for algorithm in request.algorithms:
            processes = create_process_objects(request.processes)
            result = run_scheduler(
                processes,
                algorithm,
                request.context_switch_overhead,
                request.time_slice
            )
            results.append(result)
            
            # 비교 데이터 수집
            stats = result['statistics']
            comparison['algorithms'].append(algorithm)
            comparison['avg_waiting_time'].append(stats.get('avg_waiting_time', 0))
            comparison['avg_turnaround_time'].append(stats.get('avg_turnaround_time', 0))
            comparison['avg_response_time'].append(stats.get('avg_response_time', 0))
            comparison['cpu_utilization'].append(stats.get('cpu_utilization', 0))
            comparison['context_switches'].append(stats.get('context_switches', 0))
        
        return {
            "success": True,
            "results": results,
            "comparison": comparison
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# WebSocket을 통한 실시간 시뮬레이션
class RealtimeSimulator:
    def __init__(self, processes: List[Process], algorithm: str, 
                 context_switch_overhead: int = 1, time_slice: int = 4):
        self.algorithm = algorithm
        self.context_switch_overhead = context_switch_overhead
        
        # 문맥교환 오버헤드 설정
        scheduler_base.CONTEXT_SWITCH_OVERHEAD = context_switch_overhead
        
        algo_info = ALGORITHM_MAP[algorithm]
        params = algo_info['params'].copy()
        if algorithm == 'RoundRobin':
            params['time_slice'] = time_slice
        
        self.scheduler = algo_info['class'](processes, **params)
        self.is_complete = False
        self.running = False
        self.last_gantt_index = 0
        self.last_log_index = 0
    
    def step(self) -> Dict:
        """한 스텝 실행 및 상태 반환"""
        if self.is_complete:
            return {'complete': True}
        
        # 스케줄러 한 스텝 실행
        is_complete = self.scheduler.execute_one_step()
        
        # 새로운 Gantt 엔트리
        new_gantt = []
        current_gantt_count = len(self.scheduler.gantt_chart)
        if current_gantt_count > self.last_gantt_index:
            for i in range(self.last_gantt_index, current_gantt_count):
                entry = self.scheduler.gantt_chart[i]
                new_gantt.append({
                    'pid': entry.pid,
                    'start_time': entry.start_time,
                    'end_time': entry.end_time,
                    'state': entry.state.value if hasattr(entry.state, 'value') else str(entry.state)
                })
            self.last_gantt_index = current_gantt_count
        
        # 새로운 로그
        new_logs = []
        current_log_count = len(self.scheduler.event_log)
        if current_log_count > self.last_log_index:
            new_logs = self.scheduler.event_log[self.last_log_index:current_log_count]
            self.last_log_index = current_log_count
        
        # 현재 상태
        running = None
        if self.scheduler.running_process:
            p = self.scheduler.running_process
            running = {
                'pid': p.pid,
                'remaining': p.remaining_burst_time,
                'priority': p.priority
            }
        
        ready_queue = [
            {'pid': p.pid, 'remaining': p.remaining_burst_time}
            for p in self.scheduler.ready_queue
        ]
        
        waiting_queue = [
            {'pid': p.pid}
            for p in self.scheduler.waiting_queue
        ]
        
        # 통계
        stats = {
            'current_time': self.scheduler.current_time,
            'context_switches': self.scheduler.stats.context_switches,
            'cpu_busy_time': self.scheduler.stats.cpu_busy_time,
            'completed': len(self.scheduler.terminated_processes),
            'total': len(self.scheduler.processes)
        }
        
        if is_complete:
            self.is_complete = True
            self.scheduler.update_statistics()
            stats['final'] = self.scheduler.stats.calculate_averages()
        
        return {
            'complete': is_complete,
            'running': running,
            'ready_queue': ready_queue,
            'waiting_queue': waiting_queue,
            'new_gantt': new_gantt,
            'new_logs': new_logs,
            'stats': stats
        }


# 활성 WebSocket 연결 관리
active_simulators: Dict[str, RealtimeSimulator] = {}


@app.websocket("/ws/realtime")
async def websocket_realtime(websocket: WebSocket):
    """실시간 시뮬레이션 WebSocket 엔드포인트"""
    await websocket.accept()
    simulator = None
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            action = message.get('action')
            
            if action == 'init':
                # 시뮬레이터 초기화
                processes = [
                    Process(
                        pid=p['pid'],
                        arrival_time=p['arrival_time'],
                        priority=p['priority'],
                        execution_pattern=p['execution_pattern'],
                        period=p.get('period', 0),
                        deadline=p.get('deadline', 0)
                    )
                    for p in message['processes']
                ]
                
                simulator = RealtimeSimulator(
                    processes,
                    message['algorithm'],
                    message.get('context_switch_overhead', 1),
                    message.get('time_slice', 4)
                )
                
                await websocket.send_json({
                    'type': 'initialized',
                    'algorithm': message['algorithm'],
                    'process_count': len(processes)
                })
            
            elif action == 'step':
                if simulator:
                    result = simulator.step()
                    await websocket.send_json({
                        'type': 'step_result',
                        **result
                    })
            
            elif action == 'run':
                # 자동 실행 (속도 조절 가능)
                if simulator:
                    speed = message.get('speed', 1.0)
                    delay = 1.0 / speed
                    
                    while not simulator.is_complete:
                        result = simulator.step()
                        await websocket.send_json({
                            'type': 'step_result',
                            **result
                        })
                        
                        if result['complete']:
                            break
                        
                        await asyncio.sleep(delay)
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({'type': 'error', 'message': str(e)})


@app.get("/sample-processes")
async def get_sample_processes():
    """샘플 프로세스 데이터 반환"""
    return {
        "samples": [
            {
                "name": "기본 테스트 (3개 프로세스)",
                "processes": [
                    {"pid": 1, "arrival_time": 0, "priority": 1, "execution_pattern": [10], "period": 0, "deadline": 0},
                    {"pid": 2, "arrival_time": 2, "priority": 2, "execution_pattern": [5], "period": 0, "deadline": 0},
                    {"pid": 3, "arrival_time": 5, "priority": 3, "execution_pattern": [15], "period": 0, "deadline": 0}
                ]
            },
            {
                "name": "I/O 포함 (3개 프로세스)",
                "processes": [
                    {"pid": 1, "arrival_time": 0, "priority": 1, "execution_pattern": [5, 3, 5], "period": 0, "deadline": 0},
                    {"pid": 2, "arrival_time": 1, "priority": 2, "execution_pattern": [3, 2, 3], "period": 0, "deadline": 0},
                    {"pid": 3, "arrival_time": 2, "priority": 3, "execution_pattern": [8], "period": 0, "deadline": 0}
                ]
            },
            {
                "name": "실시간 프로세스 (RM/EDF용)",
                "processes": [
                    {"pid": 1, "arrival_time": 0, "priority": 1, "execution_pattern": [2], "period": 5, "deadline": 5},
                    {"pid": 2, "arrival_time": 0, "priority": 2, "execution_pattern": [3], "period": 10, "deadline": 10},
                    {"pid": 3, "arrival_time": 0, "priority": 3, "execution_pattern": [1], "period": 20, "deadline": 20}
                ]
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
