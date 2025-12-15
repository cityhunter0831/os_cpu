"""동기화 데모: 생산자-소비자 + 뮤텍스/세마포어 + 교착상태 탐지"""
from typing import List, Optional, Dict
from core.process import Process, ProcessState, create_process_copy
from core.scheduler_base import BaseScheduler
from core.sync import Semaphore, Mutex, SyncManager


class SyncDemoScheduler(BaseScheduler):
    def __init__(self, processes: List[Process], buffer_size: int = 3, rounds: int = 5):
        # 1 producer, 1 consumer로 안정적 완료 보장
        prods = [p for p in processes if p.initial_priority <= 3][:1]
        cons = [p for p in processes if p.initial_priority >= 4][:1]
        if not prods:
            prods = [processes[0]]
        if not cons:
            cons = [processes[1]] if len(processes) >= 2 else [processes[0]]
        selected = []
        for p in (prods + cons):
            np = create_process_copy(p)
            np.arrival_time = 0
            # CPU burst를 rounds*2로 설정 (각 라운드당 임계구역 CPU=2)
            np.execution_pattern = [rounds * 2]
            selected.append(np)
        
        super().__init__(selected, "Sync Demo: Producer-Consumer")
        self.time_slice = 4
        self.time_used = 0
        self.execution_start = None
        # 동기화 원시 및 교착상태 탐지
        self.sync_manager = SyncManager()
        self.sem_empty = self.sync_manager.get_semaphore('empty', buffer_size)
        self.sem_full = self.sync_manager.get_semaphore('full', 0)
        self.mutex = self.sync_manager.get_mutex('mutex')
        self.deadlock_checks = 0
        self.deadlocks_detected = 0
        # 프로세스별 상태
        for i, p in enumerate(self.processes):
            role = 'producer' if i < len(prods) else 'consumer'
            setattr(p, 'sync_role', role)
            setattr(p, 'sync_rounds_done', 0)
            setattr(p, 'sync_rounds_total', rounds)
            setattr(p, 'sync_phase', 'IDLE')  # IDLE|WAIT_SEM|WAIT_MUTEX|CRITICAL|DONE
            setattr(p, 'sync_critical_cpu', 0)
    
    def _is_process_done(self, p: Process) -> bool:
        return getattr(p, 'sync_rounds_done', 0) >= getattr(p, 'sync_rounds_total', 0)
    
    def _process_sync_step(self, p: Process) -> bool:
        """1 CPU틱 실행. True=CPU 사용, False=블락/대기"""
        phase = getattr(p, 'sync_phase')
        role = getattr(p, 'sync_role')
        
        if self._is_process_done(p):
            return False
        
        if phase == 'IDLE':
            # 세마포어 대기 시도
            sem = self.sem_empty if role == 'producer' else self.sem_full
            if sem.wait(p):
                setattr(p, 'sync_phase', 'WAIT_MUTEX')
                self.log_event(f"P{p.pid} ({role}) acquired {sem.name}")
                return False  # 다음 틱에 계속
            else:
                # 블락됨
                p.state = ProcessState.WAITING
                if p not in self.waiting_queue:
                    self.waiting_queue.append(p)
                    self.log_event(f"P{p.pid} → Waiting on {sem.name}")
                self.add_to_gantt_chart(p.pid, self.current_time, self.current_time + 1, ProcessState.WAITING)
                return False
        
        elif phase == 'WAIT_MUTEX':
            # 뮤텍스 획득 시도
            if self.mutex.try_lock(p):
                setattr(p, 'sync_phase', 'CRITICAL')
                setattr(p, 'sync_critical_cpu', 0)
                self.log_event(f"P{p.pid} acquired mutex → CRITICAL")
                return False
            else:
                p.state = ProcessState.WAITING
                if p not in self.waiting_queue:
                    self.waiting_queue.append(p)
                    self.log_event(f"P{p.pid} → Waiting on mutex")
                self.add_to_gantt_chart(p.pid, self.current_time, self.current_time + 1, ProcessState.WAITING)
                return False
        
        elif phase == 'CRITICAL':
            # 임계구역에서 CPU 작업
            cpu_done = getattr(p, 'sync_critical_cpu', 0)
            if cpu_done < 2:  # 2틱 작업
                setattr(p, 'sync_critical_cpu', cpu_done + 1)
                return True  # CPU 사용
            else:
                # 임계구역 완료 → unlock, signal
                unblocked_m = self.mutex.unlock()
                if unblocked_m:
                    unblocked_m.state = ProcessState.READY
                    unblocked_m.last_ready_time = self.current_time
                    setattr(unblocked_m, 'sync_phase', 'WAIT_MUTEX')
                    if unblocked_m in self.waiting_queue:
                        self.waiting_queue.remove(unblocked_m)
                    self.ready_queue.append(unblocked_m)
                    self.log_event(f"P{unblocked_m.pid} unblocked by mutex")
                
                # Signal opposite semaphore
                sem_sig = self.sem_full if role == 'producer' else self.sem_empty
                unblocked_s = sem_sig.signal()
                if unblocked_s:
                    unblocked_s.state = ProcessState.READY
                    unblocked_s.last_ready_time = self.current_time
                    setattr(unblocked_s, 'sync_phase', 'IDLE')
                    if unblocked_s in self.waiting_queue:
                        self.waiting_queue.remove(unblocked_s)
                    self.ready_queue.append(unblocked_s)
                    self.log_event(f"P{unblocked_s.pid} unblocked by {sem_sig.name}")
                
                # 라운드 완료
                done = getattr(p, 'sync_rounds_done', 0) + 1
                setattr(p, 'sync_rounds_done', done)
                if done >= getattr(p, 'sync_rounds_total', 0):
                    setattr(p, 'sync_phase', 'DONE')
                else:
                    setattr(p, 'sync_phase', 'IDLE')
                self.log_event(f"P{p.pid} round {done} done")
                return False
        
        return False
    
    def select_next_process(self) -> Optional[Process]:
        return self.ready_queue[0] if self.ready_queue else None
    
    def execute_one_step(self) -> bool:
        """한 시간 단위 실행 (실시간 뷰어용)"""
        if self.is_simulation_complete():
            return True
        
        # 1. Arrival
        self.handle_process_arrival()
        
        # 2. Select
        if self.running_process is None and self.ready_queue:
            next_p = self.ready_queue.pop(0)
            self.running_process = next_p
            self.running_process.state = ProcessState.RUNNING
            if self.running_process.start_time is None:
                self.running_process.start_time = self.current_time
                self.running_process.response_time = self.current_time - self.running_process.arrival_time
            self.log_event(f"P{next_p.pid} → Running")
            self.execution_start = self.current_time
            self.time_used = 0
        
        # 3. Execute
        if self.running_process:
            p = self.running_process
            
            if self.execution_start is None:
                self.execution_start = self.current_time
            
            cpu_consumed = self._process_sync_step(p)
            
            if cpu_consumed:
                self.stats.cpu_busy_time += 1
                self.time_used += 1
            
            # 완료 체크
            if self._is_process_done(p):
                if self.execution_start is not None:
                    self.add_to_gantt_chart(p.pid, self.execution_start, self.current_time + 1, ProcessState.RUNNING)
                p.finish_time = self.current_time + 1
                self.terminate_process(p)
                self.running_process = None
                self.execution_start = None
                self.time_used = 0
            # 블락 체크
            elif p.state == ProcessState.WAITING:
                if self.execution_start is not None:
                    self.add_to_gantt_chart(p.pid, self.execution_start, self.current_time, ProcessState.RUNNING)
                self.running_process = None
                self.execution_start = None
                self.time_used = 0
            # 타임슬라이스 체크
            elif self.time_used >= self.time_slice:
                if self.execution_start is not None:
                    self.add_to_gantt_chart(p.pid, self.execution_start, self.current_time + 1, ProcessState.RUNNING)
                p.state = ProcessState.READY
                p.last_ready_time = self.current_time + 1
                self.ready_queue.append(p)
                self.log_event(f"P{p.pid} time slice expired")
                self.running_process = None
                self.execution_start = None
                self.time_used = 0
        else:
            self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1, ProcessState.READY)
        
        # 교착상태 탐지 (매 10 틱마다)
        if self.current_time % 10 == 0:
            self.deadlock_checks += 1
            cycle = self.sync_manager.detect_deadlock()
            if cycle:
                self.deadlocks_detected += 1
                self.log_event(f"⚠️ DEADLOCK DETECTED! Cycle: {cycle}")
                # 교착상태 회복: 가장 낮은 PID 프로세스를 강제 종료
                victim_pid = min(cycle)
                for p in self.processes:
                    if p.pid == victim_pid and p.state == ProcessState.WAITING:
                        self.log_event(f"🔧 DEADLOCK RECOVERY: Aborting P{victim_pid}")
                        p.state = ProcessState.TERMINATED
                        p.finish_time = self.current_time
                        self.terminated_processes.append(p)
                        if p in self.waiting_queue:
                            self.waiting_queue.remove(p)
                        break
        
        self.current_time += 1
        
        if self.current_time > 5000:
            self.log_event("Timeout")
            return True
        
        return self.is_simulation_complete()
    
    def run(self, verbose: bool = False) -> Dict:
        self.log_event(f"===== {self.name} Started =====")
        exec_start = None
        
        while len(self.terminated_processes) < len(self.processes):
            # 1. Arrival
            self.handle_process_arrival()
            
            # 2. Select
            if self.running_process is None and self.ready_queue:
                next_p = self.ready_queue.pop(0)
                self.context_switch(next_p)
                exec_start = self.current_time
                self.time_used = 0
            
            # 3. Execute
            if self.running_process:
                p = self.running_process
                cpu_consumed = self._process_sync_step(p)
                
                if cpu_consumed:
                    self.stats.cpu_busy_time += 1
                    self.time_used += 1
                
                # 완료 체크
                if self._is_process_done(p):
                    if exec_start is not None:
                        self.add_to_gantt_chart(p.pid, exec_start, self.current_time + 1, ProcessState.RUNNING)
                    p.finish_time = self.current_time + 1
                    self.terminate_process(p)
                    self.running_process = None
                    exec_start = None
                    self.time_used = 0
                # 블락 체크
                elif p.state == ProcessState.WAITING:
                    if exec_start is not None:
                        self.add_to_gantt_chart(p.pid, exec_start, self.current_time, ProcessState.RUNNING)
                    self.running_process = None
                    exec_start = None
                    self.time_used = 0
                # 타임슬라이스 체크
                elif self.time_used >= self.time_slice:
                    if exec_start is not None:
                        self.add_to_gantt_chart(p.pid, exec_start, self.current_time + 1, ProcessState.RUNNING)
                    p.state = ProcessState.READY
                    p.last_ready_time = self.current_time + 1
                    self.ready_queue.append(p)
                    self.log_event(f"P{p.pid} time slice expired")
                    self.running_process = None
                    exec_start = None
                    self.time_used = 0
            else:
                self.add_to_gantt_chart(-1, self.current_time, self.current_time + 1, ProcessState.READY)
            
            # 교착상태 탐지 (매 10 틱마다)
            if self.current_time % 10 == 0:
                self.deadlock_checks += 1
                cycle = self.sync_manager.detect_deadlock()
                if cycle:
                    self.deadlocks_detected += 1
                    self.log_event(f"⚠️ DEADLOCK DETECTED! Cycle: {cycle}")
                    # 교착상태 회복: 가장 낮은 PID 프로세스를 강제 종료
                    victim_pid = min(cycle)
                    for p in self.processes:
                        if p.pid == victim_pid and p.state == ProcessState.WAITING:
                            self.log_event(f"🔧 DEADLOCK RECOVERY: Aborting P{victim_pid}")
                            p.state = ProcessState.TERMINATED
                            p.finish_time = self.current_time
                            self.terminated_processes.append(p)
                            # waiting_queue에서 제거
                            if p in self.waiting_queue:
                                self.waiting_queue.remove(p)
                            break
            
            self.current_time += 1
            if self.current_time > 5000:
                self.log_event("Timeout")
                break
        
        self.log_event(f"===== {self.name} Completed =====")
        self.log_event(f"📊 Deadlock Checks: {self.deadlock_checks}")
        self.log_event(f"📊 Deadlocks Detected: {self.deadlocks_detected}")
        
        if verbose:
            for log in self.event_log:
                print(log)
        
        result = self.get_results()
        result['deadlock_checks'] = self.deadlock_checks
        result['deadlocks_detected'] = self.deadlocks_detected
        return result
