"""
advanced_schedulers.py의 모든 execute_one_step 메서드에
문맥교환 오버헤드 처리를 추가하는 스크립트
"""

template = '''        # 문맥교환 중이면 오버헤드 처리
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
        '''

context_switch_code = '''                # 문맥교환 시작
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

print("이 스크립트의 템플릿을 참고하여 수동으로 수정하세요.")
print("\n1. 각 execute_one_step 시작 부분에 문맥교환 오버헤드 체크 추가")
print("2. self.context_switch() 호출을 위의 context_switch_code로 교체")
print("3. 선점 검사는 self.running_process가 있을 때만 수행")
