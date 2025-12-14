#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
실시간 시뮬레이션 뷰어
시간의 흐름에 따라 스케줄링 과정을 시각화
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from typing import Optional, Dict, List
from core.process import Process, ProcessState


class RealtimeSimulationViewer:
    """실시간 스케줄링 시뮬레이션 뷰어"""
    
    def __init__(self, scheduler, algorithm_name: str):
        """
        Args:
            scheduler: 스케줄러 인스턴스
            algorithm_name: 알고리즘 이름
        """
        self.scheduler = scheduler
        self.algorithm_name = algorithm_name
        
        # 시뮬레이션 상태
        self.is_running = False
        self.is_paused = False
        self.is_complete = False
        self.speed = 1.0  # 재생 속도 (1.0 = 1초당 1 시간 단위)
        self.current_time = 0
        
        # 색상 설정
        self.process_colors = {}
        self.colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', 
                      '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788']
        
        # GUI 생성
        self.create_window()
        
    def create_window(self):
        """메인 윈도우 생성"""
        self.window = tk.Toplevel()
        self.window.title(f"실시간 시뮬레이션 - {self.algorithm_name}")
        self.window.geometry("1400x900")
        self.window.resizable(True, True)
        
        # 메인 프레임
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. 헤더 (시간 및 통계)
        self.create_header(main_frame)
        
        # 2. 컨트롤 패널 (재생/일시정지/속도)
        self.create_control_panel(main_frame)
        
        # 3. Gantt 차트 영역
        self.create_gantt_area(main_frame)
        
        # 4. 상태 패널 (Ready/Running/Waiting 큐)
        self.create_status_panel(main_frame)
        
        # 5. 이벤트 로그
        self.create_event_log(main_frame)
        
        # 윈도우 닫기 이벤트
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_header(self, parent):
        """헤더 영역 생성"""
        header_frame = ttk.LabelFrame(parent, text="📊 시뮬레이션 정보", padding="10")
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 시간 표시
        time_frame = ttk.Frame(header_frame)
        time_frame.pack(side=tk.LEFT, padx=20)
        
        ttk.Label(time_frame, text="⏱️ 현재 시간:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.time_label = ttk.Label(time_frame, text="T = 0", 
                                    font=("Arial", 14, "bold"), foreground="#2C3E50")
        self.time_label.pack(side=tk.LEFT, padx=5)
        
        # 문맥교환 횟수
        cs_frame = ttk.Frame(header_frame)
        cs_frame.pack(side=tk.LEFT, padx=20)
        
        ttk.Label(cs_frame, text="🔄 문맥교환:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.cs_label = ttk.Label(cs_frame, text="0 회", 
                                  font=("Arial", 12, "bold"), foreground="#E74C3C")
        self.cs_label.pack(side=tk.LEFT, padx=5)
        
        # CPU 이용률
        cpu_frame = ttk.Frame(header_frame)
        cpu_frame.pack(side=tk.LEFT, padx=20)
        
        ttk.Label(cpu_frame, text="💻 CPU 이용률:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.cpu_label = ttk.Label(cpu_frame, text="0.0%", 
                                   font=("Arial", 12, "bold"), foreground="#27AE60")
        self.cpu_label.pack(side=tk.LEFT, padx=5)
        
        # 완료된 프로세스
        completed_frame = ttk.Frame(header_frame)
        completed_frame.pack(side=tk.LEFT, padx=20)
        
        ttk.Label(completed_frame, text="✅ 완료:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        self.completed_label = ttk.Label(completed_frame, text="0 / 0", 
                                        font=("Arial", 12, "bold"), foreground="#8E44AD")
        self.completed_label.pack(side=tk.LEFT, padx=5)
        
    def create_control_panel(self, parent):
        """컨트롤 패널 생성"""
        control_frame = ttk.LabelFrame(parent, text="🎮 재생 컨트롤", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 재생 버튼들
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=tk.LEFT)
        
        self.play_button = ttk.Button(button_frame, text="▶️ 재생", 
                                      command=self.play, width=10)
        self.play_button.pack(side=tk.LEFT, padx=5)
        
        self.pause_button = ttk.Button(button_frame, text="⏸️ 일시정지", 
                                       command=self.pause, width=10, state='disabled')
        self.pause_button.pack(side=tk.LEFT, padx=5)
        
        self.step_button = ttk.Button(button_frame, text="⏭️ 단계 실행", 
                                      command=self.step_forward, width=10)
        self.step_button.pack(side=tk.LEFT, padx=5)
        
        self.reset_button = ttk.Button(button_frame, text="🔄 재시작", 
                                       command=self.reset_simulation, width=10)
        self.reset_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="💾 Gantt 저장", 
                   command=self.save_gantt_chart, width=12).pack(side=tk.LEFT, padx=5)
        
        # 속도 조절
        speed_frame = ttk.Frame(control_frame)
        speed_frame.pack(side=tk.LEFT, padx=50)
        
        ttk.Label(speed_frame, text="⚡ 속도:", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        self.speed_var = tk.DoubleVar(value=1.0)
        self.speed_scale = ttk.Scale(speed_frame, from_=0.1, to=5.0, 
                                     orient=tk.HORIZONTAL, length=200,
                                     variable=self.speed_var, 
                                     command=self.on_speed_change)
        self.speed_scale.pack(side=tk.LEFT, padx=5)
        
        self.speed_label = ttk.Label(speed_frame, text="1.0x", 
                                     font=("Arial", 10, "bold"))
        self.speed_label.pack(side=tk.LEFT, padx=5)
        
    def create_gantt_area(self, parent):
        """Gantt 차트 영역 생성"""
        gantt_frame = ttk.LabelFrame(parent, text="📈 Gantt Chart (실시간)", padding="10")
        gantt_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 스크롤바 추가
        scroll_x = ttk.Scrollbar(gantt_frame, orient=tk.HORIZONTAL)
        scroll_y = ttk.Scrollbar(gantt_frame, orient=tk.VERTICAL)
        
        self.gantt_canvas = tk.Canvas(gantt_frame, 
                                      bg='white',
                                      xscrollcommand=scroll_x.set,
                                      yscrollcommand=scroll_y.set,
                                      height=300)
        
        scroll_x.config(command=self.gantt_canvas.xview)
        scroll_y.config(command=self.gantt_canvas.yview)
        
        scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.gantt_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Gantt 차트 초기화
        self.gantt_y_offset = 40
        self.gantt_x_offset = 60
        self.gantt_time_scale = 20  # 1 시간 단위당 픽셀
        self.gantt_row_height = 40
        
    def create_status_panel(self, parent):
        """상태 패널 생성"""
        status_frame = ttk.LabelFrame(parent, text="📋 프로세스 상태", padding="10")
        status_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 3개 컬럼으로 분할
        columns_frame = ttk.Frame(status_frame)
        columns_frame.pack(fill=tk.BOTH, expand=True)
        
        # Running
        running_frame = ttk.LabelFrame(columns_frame, text="🏃 Running", padding="5")
        running_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.running_text = tk.Text(running_frame, height=4, width=25, 
                                    font=("Consolas", 10))
        self.running_text.pack(fill=tk.BOTH, expand=True)
        self.running_text.config(state='disabled')
        
        # Ready Queue
        ready_frame = ttk.LabelFrame(columns_frame, text="📋 Ready Queue", padding="5")
        ready_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.ready_text = tk.Text(ready_frame, height=4, width=25, 
                                  font=("Consolas", 10))
        self.ready_text.pack(fill=tk.BOTH, expand=True)
        self.ready_text.config(state='disabled')
        
        # Waiting Queue
        waiting_frame = ttk.LabelFrame(columns_frame, text="⏳ Waiting Queue", padding="5")
        waiting_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.waiting_text = tk.Text(waiting_frame, height=4, width=25, 
                                    font=("Consolas", 10))
        self.waiting_text.pack(fill=tk.BOTH, expand=True)
        self.waiting_text.config(state='disabled')
        
    def create_event_log(self, parent):
        """이벤트 로그 영역 생성"""
        log_frame = ttk.LabelFrame(parent, text="📝 이벤트 로그", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 스크롤바
        scroll = ttk.Scrollbar(log_frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame, height=8, 
                               font=("Consolas", 9),
                               yscrollcommand=scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.config(command=self.log_text.yview)
        
        # 태그 설정
        self.log_text.tag_config("time", foreground="#2980B9", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("cs", foreground="#E74C3C", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("event", foreground="#27AE60")
        self.log_text.tag_config("process", foreground="#8E44AD", font=("Consolas", 9, "bold"))
        
    def initialize_gantt_chart(self):
        """Gantt 차트 초기화"""
        self.gantt_canvas.delete("all")
        
        # 프로세스 목록 가져오기
        processes = self.scheduler.processes
        
        # 프로세스별 색상 할당
        for i, process in enumerate(processes):
            self.process_colors[process.pid] = self.colors[i % len(self.colors)]
        
        # Y축 (프로세스 레이블)
        for i, process in enumerate(processes):
            y_pos = self.gantt_y_offset + i * self.gantt_row_height
            
            # 프로세스 레이블
            self.gantt_canvas.create_text(
                30, y_pos + self.gantt_row_height // 2,
                text=f"P{process.pid}",
                font=("Arial", 10, "bold"),
                fill=self.process_colors[process.pid]
            )
            
            # 수평선
            self.gantt_canvas.create_line(
                self.gantt_x_offset, y_pos + self.gantt_row_height,
                self.gantt_x_offset + 2000, y_pos + self.gantt_row_height,
                fill="#E0E0E0", width=1
            )
        
        # 문맥교환 행 추가
        cs_y_pos = self.gantt_y_offset + len(processes) * self.gantt_row_height
        self.gantt_canvas.create_text(
            30, cs_y_pos + self.gantt_row_height // 2,
            text="CS",
            font=("Arial", 10, "bold"),
            fill="#E74C3C"
        )
        
        # X축 (시간)
        for t in range(0, 200, 10):
            x_pos = self.gantt_x_offset + t * self.gantt_time_scale
            self.gantt_canvas.create_line(
                x_pos, self.gantt_y_offset - 20,
                x_pos, cs_y_pos + self.gantt_row_height,
                fill="#E0E0E0", width=1, dash=(2, 2)
            )
            self.gantt_canvas.create_text(
                x_pos, self.gantt_y_offset - 10,
                text=str(t),
                font=("Arial", 8)
            )
        
    def update_gantt_chart(self, gantt_entry):
        """Gantt 차트에 새 엔트리 추가"""
        if gantt_entry.pid == -1:  # CPU 유휴
            return
        
        # 문맥교환 구간
        if gantt_entry.pid == -2:
            cs_y_pos = self.gantt_y_offset + len(self.scheduler.processes) * self.gantt_row_height
            y_pos = cs_y_pos
            color = "#E74C3C"
            text = "CS"
        else:
            # 일반 프로세스
            process_index = next(i for i, p in enumerate(self.scheduler.processes) 
                               if p.pid == gantt_entry.pid)
            y_pos = self.gantt_y_offset + process_index * self.gantt_row_height
            
            if gantt_entry.state == ProcessState.RUNNING:
                color = self.process_colors[gantt_entry.pid]
                text = f"P{gantt_entry.pid}"
            elif gantt_entry.state == ProcessState.WAITING:
                color = "#FFE5E5"
                text = "I/O"
            else:
                color = self.process_colors[gantt_entry.pid]
                text = f"P{gantt_entry.pid}"
        
        # 사각형 그리기
        x1 = self.gantt_x_offset + gantt_entry.start_time * self.gantt_time_scale
        x2 = self.gantt_x_offset + gantt_entry.end_time * self.gantt_time_scale
        y1 = y_pos + 5
        y2 = y_pos + self.gantt_row_height - 5
        
        self.gantt_canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=color,
            outline="black",
            width=1
        )
        
        # 텍스트 표시 (충분한 공간이 있을 때만)
        if (x2 - x1) > 20:
            self.gantt_canvas.create_text(
                (x1 + x2) // 2, (y1 + y2) // 2,
                text=text,
                font=("Arial", 8, "bold"),
                fill="white" if gantt_entry.pid == -2 else "black"
            )
        
        # 스크롤 영역 업데이트
        self.gantt_canvas.config(scrollregion=self.gantt_canvas.bbox("all"))
        
    def update_status_panel(self):
        """상태 패널 업데이트"""
        # Running
        self.running_text.config(state='normal')
        self.running_text.delete(1.0, tk.END)
        if self.scheduler.running_process:
            p = self.scheduler.running_process
            self.running_text.insert(tk.END, 
                f"P{p.pid}\n"
                f"Remaining: {p.remaining_burst_time}\n"
                f"Priority: {p.priority}")
        else:
            self.running_text.insert(tk.END, "CPU Idle")
        self.running_text.config(state='disabled')
        
        # Ready Queue
        self.ready_text.config(state='normal')
        self.ready_text.delete(1.0, tk.END)
        if self.scheduler.ready_queue:
            for p in self.scheduler.ready_queue:
                self.ready_text.insert(tk.END, f"P{p.pid} (rem={p.remaining_burst_time})\n")
        else:
            self.ready_text.insert(tk.END, "Empty")
        self.ready_text.config(state='disabled')
        
        # Waiting Queue
        self.waiting_text.config(state='normal')
        self.waiting_text.delete(1.0, tk.END)
        if self.scheduler.waiting_queue:
            for p in self.scheduler.waiting_queue:
                self.waiting_text.insert(tk.END, f"P{p.pid} (I/O)\n")
        else:
            self.waiting_text.insert(tk.END, "Empty")
        self.waiting_text.config(state='disabled')
        
    def update_header_stats(self):
        """헤더 통계 업데이트"""
        self.time_label.config(text=f"T = {self.scheduler.current_time}")
        self.cs_label.config(text=f"{self.scheduler.stats.context_switches} 회")
        
        # CPU 이용률 계산
        if self.scheduler.current_time > 0:
            cpu_util = (self.scheduler.stats.cpu_busy_time / self.scheduler.current_time) * 100
            self.cpu_label.config(text=f"{cpu_util:.1f}%")
        
        # 완료된 프로세스
        completed = len(self.scheduler.terminated_processes)
        total = len(self.scheduler.processes)
        self.completed_label.config(text=f"{completed} / {total}")
        
    def log_event(self, message: str, tag: str = None):
        """이벤트 로그 추가"""
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        
    def play(self):
        """재생 시작"""
        if self.is_complete:
            messagebox.showinfo("알림", "시뮬레이션이 이미 완료되었습니다.\n'재시작' 버튼을 눌러주세요.")
            return
        
        self.is_running = True
        self.is_paused = False
        self.play_button.config(state='disabled')
        self.pause_button.config(state='normal')
        self.step_button.config(state='disabled')
        
        # 별도 스레드에서 시뮬레이션 실행
        thread = threading.Thread(target=self.run_simulation_loop, daemon=True)
        thread.start()
        
    def pause(self):
        """일시정지"""
        self.is_paused = True
        self.play_button.config(state='normal')
        self.pause_button.config(state='disabled')
        self.step_button.config(state='normal')
        
    def step_forward(self):
        """한 단계씩 실행"""
        if not self.is_complete:
            self.execute_one_step()
            
    def reset_simulation(self):
        """시뮬레이션 재시작"""
        # 재시작 확인
        if messagebox.askyesno("확인", "시뮬레이션을 재시작하시겠습니까?"):
            self.is_running = False
            self.is_paused = False
            self.is_complete = False
            
            # 스케줄러 재초기화 필요
            messagebox.showinfo("알림", "창을 닫고 다시 실행해주세요.")
            self.window.destroy()
        
    def on_speed_change(self, value):
        """속도 변경"""
        self.speed = float(value)
        self.speed_label.config(text=f"{self.speed:.1f}x")
        
    def run_simulation_loop(self):
        """시뮬레이션 루프 (별도 스레드)"""
        while self.is_running and not self.is_complete:
            if not self.is_paused:
                self.execute_one_step()
                time.sleep(1.0 / self.speed)  # 속도 조절
            else:
                time.sleep(0.1)  # 일시정지 중에는 대기
                
    def execute_one_step(self):
        """한 시간 단위 실행"""
        if self.is_complete:
            return
        
        # 이전 Gantt 차트 엔트리 수 저장
        prev_gantt_count = len(self.scheduler.gantt_chart)
        
        # 스케줄러의 단계별 실행 메서드 호출
        is_complete = self.scheduler.execute_one_step()
        
        # 새로운 Gantt 엔트리가 추가되었으면 업데이트
        if len(self.scheduler.gantt_chart) > prev_gantt_count:
            new_entry = self.scheduler.gantt_chart[-1]
            self.update_gantt_chart(new_entry)
        
        # 상태 패널 업데이트
        self.update_status_panel()
        
        # 헤더 통계 업데이트
        self.update_header_stats()
        
        # 최신 로그 표시
        if self.scheduler.event_log:
            latest_log = self.scheduler.event_log[-1]
            
            # 로그 타입 판별
            if "Context Switch" in latest_log:
                self.log_event(latest_log, "cs")
            elif "arrived" in latest_log or "completed" in latest_log:
                self.log_event(latest_log, "event")
            elif "Running" in latest_log or "Terminated" in latest_log:
                self.log_event(latest_log, "process")
            else:
                self.log_event(latest_log, "time")
        
        # 시뮬레이션 완료 확인
        if is_complete:
            self.is_complete = True
            self.is_running = False
            self.is_paused = True
            self.play_button.config(state='disabled')
            self.pause_button.config(state='disabled')
            self.step_button.config(state='disabled')
            
            self.log_event("\n=== 시뮬레이션 완료! ===", "cs")
            self.log_event(f"총 시간: {self.scheduler.current_time}", "event")
            self.log_event(f"문맥교환 횟수: {self.scheduler.stats.context_switches}", "cs")
            
            # 최종 통계 계산
            self.scheduler.update_statistics()
            stats = self.scheduler.stats.calculate_averages()
            self.log_event(f"평균 대기 시간: {stats['avg_waiting_time']:.2f}", "event")
            self.log_event(f"평균 반환 시간: {stats['avg_turnaround_time']:.2f}", "event")
            self.log_event(f"CPU 이용률: {stats['cpu_utilization']:.2f}%", "event")
        
    def save_gantt_chart(self):
        """Gantt 차트를 이미지로 저장 - matplotlib 사용"""
        import tkinter.messagebox as messagebox
        
        try:
            from tkinter import filedialog
            from datetime import datetime
            import matplotlib
            matplotlib.use('Agg')  # GUI 백엔드 사용 안 함
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
            from core.process import ProcessState
            
            # 기본 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"gantt_realtime_{self.algorithm_name}_{timestamp}.png"
            
            # 저장 위치 선택
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG 파일", "*.png"), ("모든 파일", "*.*")],
                initialfile=default_filename,
                initialdir="simulation_results"
            )
            
            if not filename:
                return
            
            # 프로세스 PID 정렬 (기존 시뮬레이터와 동일하게)
            sorted_pids = sorted(self.process_colors.keys())
            pid_to_y = {pid: i for i, pid in enumerate(sorted_pids)}
            
            # matplotlib으로 Gantt 차트 생성
            num_processes = len(sorted_pids)
            fig, ax = plt.subplots(figsize=(14, max(6, num_processes * 0.7 + 1)))
            
            # Gantt 차트 데이터로부터 그리기
            gantt_data = self.scheduler.gantt_chart
            
            if not gantt_data:
                messagebox.showwarning("경고", "저장할 Gantt 차트 데이터가 없습니다.")
                return
            
            # 프로세스별로 그리기
            for entry in gantt_data:
                pid = entry.pid
                start = entry.start_time
                duration = entry.end_time - entry.start_time
                
                if duration <= 0:
                    continue
                
                if pid == -2:  # Context Switch
                    color = '#FF6B6B'
                    label = 'CS'
                    y_pos = num_processes  # CS는 맨 아래
                    alpha = 0.8
                    edgecolor = 'darkred'
                elif pid == -1:  # Idle
                    continue
                else:
                    if pid not in pid_to_y:
                        continue
                    color = self.process_colors.get(pid, '#CCCCCC')
                    label = f'P{pid}'
                    y_pos = pid_to_y[pid]
                    
                    # 상태에 따른 스타일
                    if entry.state == ProcessState.RUNNING:
                        alpha = 0.9
                        edgecolor = 'black'
                    elif entry.state == ProcessState.WAITING:
                        alpha = 0.3
                        edgecolor = 'gray'
                    else:
                        alpha = 0.7
                        edgecolor = 'black'
                
                ax.barh(y_pos, duration, left=start, height=0.7,
                       color=color, alpha=alpha, edgecolor=edgecolor, linewidth=0.8)
                
                # 레이블 추가 (충분히 넓으면)
                if duration >= 3:
                    ax.text(start + duration/2, y_pos, label,
                           ha='center', va='center', fontsize=9, fontweight='bold',
                           color='white' if alpha > 0.5 else 'black')
            
            # Y축 설정 (PID 순서대로 - 기존 시뮬레이터와 동일)
            y_labels = [f'P{pid}' for pid in sorted_pids] + ['CS']
            ax.set_yticks(range(len(y_labels)))
            ax.set_yticklabels(y_labels)
            ax.set_ylabel('Process', fontsize=12, fontweight='bold')
            # matplotlib 기본: y=0이 아래, y=max가 위 (P1 아래, P7 위)
            
            # X축 설정
            ax.set_xlabel('Time', fontsize=12, fontweight='bold')
            max_time = max(entry.end_time for entry in gantt_data if entry.end_time is not None)
            ax.set_xlim(0, max_time)
            
            # 제목
            ax.set_title(f'Gantt Chart - {self.algorithm_name}', 
                       fontsize=14, fontweight='bold', pad=15)
            
            # 범례
            legend_elements = [
                mpatches.Patch(color='#90EE90', alpha=0.9, label='Running'),
                mpatches.Patch(color='#FFB6C1', alpha=0.3, label='I/O (Waiting)'),
                mpatches.Patch(color='#FF6B6B', alpha=0.8, label='Context Switch')
            ]
            ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
            
            # 그리드
            ax.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
            
            plt.tight_layout()
            plt.savefig(filename, dpi=150, bbox_inches='tight', format='png')
            plt.close(fig)
            
            messagebox.showinfo("저장 완료", f"Gantt 차트가 저장되었습니다:\n{filename}")
            print(f"[SUCCESS] Gantt 차트 저장: {filename}")
                
        except Exception as e:
            messagebox.showerror("저장 실패", f"Gantt 차트 저장 중 오류:\n{str(e)}")
            print(f"[ERROR] Gantt 저장 실패: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def on_closing(self):
        """윈도우 닫기"""
        self.is_running = False
        self.window.destroy()
        
    def run(self):
        """뷰어 실행"""
        # Gantt 차트 초기화
        self.initialize_gantt_chart()
        
        # 초기 상태 표시
        self.update_status_panel()
        self.update_header_stats()
        
        self.log_event(f"=== {self.algorithm_name} 시뮬레이션 시작 ===", "cs")
        self.log_event(f"프로세스 수: {len(self.scheduler.processes)}", "event")
        self.log_event("재생 버튼을 눌러 시작하세요.", "event")
