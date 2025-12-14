"""
모든 advanced_schedulers.py의 execute_one_step을 자동 수정
"""
import re

filepath = "schedulers/advanced_schedulers.py"

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# PriorityAging 수정
old_priority_aging = '''    def execute_one_step(self) -> bool:
        """한 시간 단위 실행 (실시간 뷰어용)"""
        if self.is_simulation_complete():
            return True
        
        self.handle_process_arrival()
        self.handle_io_completion()
        self.apply_aging_to_ready_queue()
        
        if self.check_preemption():'''

new_priority_aging = '''    def execute_one_step(self) -> bool:
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
        
        if self.running_process and self.check_preemption():'''

content = content.replace(old_priority_aging, new_priority_aging)

# context_switch() 호출을 수동 처리로 변경 (PriorityAging)
old_cs = '''                next_process.reset_to_initial_priority()
                self.context_switch(next_process)
                self.execution_start = self.current_time'''

new_cs = '''                next_process.reset_to_initial_priority()
                
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
                    self.execution_start = self.current_time'''

content = content.replace(old_cs, new_cs)

# MLQ, RM, EDF도 동일하게 처리
# context_switch() 패턴 찾기 (다른 스케줄러용)
patterns = [
    # MLQ용
    ('''                self.ready_queue.remove(next_process)
                self.context_switch(next_process)
                self.current_time_slice = 0
                self.execution_start = self.current_time''',
     '''                self.ready_queue.remove(next_process)
                
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
                    self.execution_start = self.current_time'''),
]

for old, new in patterns:
    content = content.replace(old, new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✓ {filepath} 수정 완료")
print("주의: MLQ, RM, EDF는 수동으로 확인 필요")
