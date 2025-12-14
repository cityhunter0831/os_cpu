#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OS 스케줄러 시뮬레이터 - GUI 버전
Tkinter 기반 그래픽 사용자 인터페이스
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import threading
from typing import List

# 기존 모듈 임포트
from core.process import Process
from utils.input_parser import InputParser
from schedulers.basic_schedulers import FCFSScheduler, SJFScheduler, RoundRobinScheduler
from schedulers.advanced_schedulers import (PriorityScheduler, PriorityAgingScheduler, 
                                            MLQScheduler, RateMonotonicScheduler, EDFScheduler)
from schedulers.sync_demo import SyncDemoScheduler
from utils.visualization import Visualizer
from main import save_results


class SchedulerGUI:
    """OS 스케줄러 시뮬레이터 GUI"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OS 스케줄러 시뮬레이터")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        
        # 변수 초기화
        self.input_file = tk.StringVar(value="data/professor_data.txt")
        self.processes = []
        self.results = []
        
        # 알고리즘 선택 변수
        self.algo_vars = {
            'FCFS': tk.BooleanVar(value=True),
            'SJF': tk.BooleanVar(value=True),
            'Round Robin': tk.BooleanVar(value=True),
            'Priority (Static)': tk.BooleanVar(value=True),
            'Priority with Aging': tk.BooleanVar(value=True),
            'Multi-Level Queue': tk.BooleanVar(value=True),
            'Rate Monotonic': tk.BooleanVar(value=True),
            'EDF': tk.BooleanVar(value=True),
            'Sync Demo': tk.BooleanVar(value=False)
        }
        
        # 알고리즘 매핑
        self.algorithm_map = {
            'FCFS': {'class': FCFSScheduler, 'params': {}},
            'SJF': {'class': SJFScheduler, 'params': {}},
            'Round Robin': {'class': RoundRobinScheduler, 'params': {'time_slice': 4}},
            'Priority (Static)': {'class': PriorityScheduler, 'params': {}},
            'Priority with Aging': {'class': PriorityAgingScheduler, 'params': {'aging_factor': 10}},
            'Multi-Level Queue': {'class': MLQScheduler, 'params': {}},
            'Rate Monotonic': {'class': RateMonotonicScheduler, 'params': {}},
            'EDF': {'class': EDFScheduler, 'params': {}},
            'Sync Demo': {'class': SyncDemoScheduler, 'params': {'buffer_size': 3, 'rounds': 5}}
        }
        
        self.create_widgets()
        
    def create_widgets(self):
        """위젯 생성"""
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # === 1. 입력 파일 선택 영역 ===
        input_frame = ttk.LabelFrame(main_frame, text="📁 입력 파일", padding="10")
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)
        
        ttk.Label(input_frame, text="파일 경로:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        file_entry = ttk.Entry(input_frame, textvariable=self.input_file, width=60)
        file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Button(input_frame, text="찾아보기", command=self.browse_file).grid(row=0, column=2, padx=5)
        ttk.Button(input_frame, text="파일 로드", command=self.load_file).grid(row=0, column=3, padx=5)
        
        # 프로세스 정보 표시
        self.process_label = ttk.Label(input_frame, text="프로세스: 0개", foreground="gray")
        self.process_label.grid(row=1, column=0, columnspan=5, sticky=tk.W, pady=(5, 0))
        
        # === 2. 알고리즘 선택 영역 ===
        algo_frame = ttk.LabelFrame(main_frame, text="⚙️ 알고리즘 선택", padding="10")
        algo_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 기본 알고리즘
        basic_frame = ttk.LabelFrame(algo_frame, text="기본 알고리즘", padding="5")
        basic_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), padx=5)
        
        ttk.Checkbutton(basic_frame, text="FCFS", variable=self.algo_vars['FCFS']).grid(row=0, column=0, sticky=tk.W, padx=10, pady=2)
        ttk.Checkbutton(basic_frame, text="SJF (Preemptive)", variable=self.algo_vars['SJF']).grid(row=1, column=0, sticky=tk.W, padx=10, pady=2)
        ttk.Checkbutton(basic_frame, text="Round Robin (q=4)", variable=self.algo_vars['Round Robin']).grid(row=2, column=0, sticky=tk.W, padx=10, pady=2)
        
        # 우선순위 알고리즘
        priority_frame = ttk.LabelFrame(algo_frame, text="우선순위 스케줄링", padding="5")
        priority_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N), padx=5)
        
        ttk.Checkbutton(priority_frame, text="Priority (정적)", variable=self.algo_vars['Priority (Static)']).grid(row=0, column=0, sticky=tk.W, padx=10, pady=2)
        ttk.Checkbutton(priority_frame, text="Priority + Aging", variable=self.algo_vars['Priority with Aging']).grid(row=1, column=0, sticky=tk.W, padx=10, pady=2)
        ttk.Checkbutton(priority_frame, text="Multi-Level Queue", variable=self.algo_vars['Multi-Level Queue']).grid(row=2, column=0, sticky=tk.W, padx=10, pady=2)
        
        # 실시간 알고리즘
        realtime_frame = ttk.LabelFrame(algo_frame, text="실시간 스케줄링", padding="5")
        realtime_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N), padx=5)
        
        ttk.Checkbutton(realtime_frame, text="Rate Monotonic (RM)", variable=self.algo_vars['Rate Monotonic']).grid(row=0, column=0, sticky=tk.W, padx=10, pady=2)
        ttk.Checkbutton(realtime_frame, text="EDF", variable=self.algo_vars['EDF']).grid(row=1, column=0, sticky=tk.W, padx=10, pady=2)
        
        # 선택 과제
        sync_frame = ttk.LabelFrame(algo_frame, text="선택 과제", padding="5")
        sync_frame.grid(row=0, column=3, sticky=(tk.W, tk.E, tk.N), padx=5)
        
        ttk.Checkbutton(sync_frame, text="Sync Demo\n(Producer-Consumer)", variable=self.algo_vars['Sync Demo']).grid(row=0, column=0, sticky=tk.W, padx=10, pady=2)
        
        # 전체 선택/해제 버튼
        button_frame = ttk.Frame(algo_frame)
        button_frame.grid(row=1, column=0, columnspan=4, pady=(10, 0))
        
        ttk.Button(button_frame, text="전체 선택", command=self.select_all).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="전체 해제", command=self.deselect_all).pack(side=tk.LEFT, padx=5)
        
        # === 3. 실행 버튼 영역 ===
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.run_button = ttk.Button(control_frame, text="🚀 시뮬레이션 실행", 
                                     command=self.run_simulation, style="Accent.TButton")
        self.run_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="🎬 실시간 시뮬레이션", 
                   command=self.open_realtime_viewer).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="📊 결과 폴더 열기", command=self.open_results_folder).pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(control_frame, mode='indeterminate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        # === 4. 로그 출력 영역 ===
        log_frame = ttk.LabelFrame(main_frame, text="📝 실행 로그", padding="10")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, 
                                                  height=20, font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 로그 태그 설정
        self.log_text.tag_config("success", foreground="green")
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("info", foreground="blue")
        self.log_text.tag_config("header", foreground="purple", font=("Consolas", 9, "bold"))
        
        # === 5. 상태바 ===
        self.status_label = ttk.Label(self.root, text="준비", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # 초기 로그
        self.log("OS 스케줄러 시뮬레이터 GUI 시작", "header")
        self.log("기본 입력 파일: data/professor_data.txt", "info")
        
    def browse_file(self):
        """파일 찾아보기"""
        filename = filedialog.askopenfilename(
            title="입력 파일 선택",
            initialdir="data",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.input_file.set(filename)
            self.log(f"파일 선택: {filename}", "info")
            
    def load_file(self):
        """파일 로드"""
        filepath = self.input_file.get()
        if not os.path.exists(filepath):
            messagebox.showerror("오류", f"파일을 찾을 수 없습니다:\n{filepath}")
            return
        
        try:
            self.processes = InputParser.parse_file(filepath)
            if self.processes:
                self.process_label.config(
                    text=f"프로세스: {len(self.processes)}개 로드됨 ✓",
                    foreground="green"
                )
                self.log(f"✓ {len(self.processes)}개 프로세스 로드 성공", "success")
                
                # 프로세스 정보 출력
                self.log("─" * 80)
                for p in self.processes:
                    self.log(f"  P{p.pid}: 도착={p.arrival_time}, 우선순위={p.priority}, "
                           f"패턴={p.execution_pattern}, 주기={p.period}")
                self.log("─" * 80)
            else:
                self.process_label.config(text="프로세스: 로드 실패", foreground="red")
                self.log("✗ 프로세스 로드 실패", "error")
        except Exception as e:
            messagebox.showerror("오류", f"파일 로드 중 오류:\n{str(e)}")
            self.log(f"✗ 오류: {str(e)}", "error")
            
            
    def select_all(self):
        """전체 알고리즘 선택"""
        for var in self.algo_vars.values():
            var.set(True)
        self.log("전체 알고리즘 선택", "info")
        
    def deselect_all(self):
        """전체 알고리즘 해제"""
        for var in self.algo_vars.values():
            var.set(False)
        self.log("전체 알고리즘 선택 해제", "info")
        
    def run_simulation(self):
        """시뮬레이션 실행"""
        if not self.processes:
            messagebox.showwarning("경고", "먼저 프로세스를 로드하세요!")
            return
        
        # 선택된 알고리즘 확인
        selected_algos = [name for name, var in self.algo_vars.items() if var.get()]
        if not selected_algos:
            messagebox.showwarning("경고", "최소 1개 이상의 알고리즘을 선택하세요!")
            return
        
        # 별도 스레드에서 실행 (GUI 블로킹 방지)
        thread = threading.Thread(target=self._run_simulation_thread, args=(selected_algos,))
        thread.daemon = True
        thread.start()
        
    def _run_simulation_thread(self, selected_algos):
        """시뮬레이션 실행 스레드"""
        try:
            self.run_button.config(state='disabled')
            self.progress.start()
            self.status_label.config(text="시뮬레이션 실행 중...")
            
            self.log("\n" + "=" * 80, "header")
            self.log("시뮬레이션 시작", "header")
            self.log("=" * 80, "header")
            
            self.results = []
            
            for i, algo_name in enumerate(selected_algos, 1):
                self.log(f"\n[{i}/{len(selected_algos)}] {algo_name} 실행 중...", "info")
                self.log("─" * 80)
                
                algo_info = self.algorithm_map[algo_name]
                scheduler = algo_info['class'](self.processes, **algo_info['params'])
                result = scheduler.run(verbose=False)
                self.results.append(result)
                
                # 이벤트 로그 출력 (실시간 상태 변화)
                for log_entry in result.get('event_log', []):
                    self.log(f"  {log_entry}")
                
                self.log("─" * 80)
                stats = result['statistics']
                self.log(f"  ✓ 완료 - 평균 대기: {stats['avg_waiting_time']:.2f}, "
                       f"평균 반환: {stats['avg_turnaround_time']:.2f}, "
                       f"CPU 이용률: {stats['cpu_utilization']:.2f}%", "success")
            
            # 결과 저장
            self.log("\n결과 저장 중...", "info")
            save_results(self.results, "simulation_results")
            
            self.log("\n" + "=" * 80, "header")
            self.log("✓ 시뮬레이션 완료!", "success")
            self.log("=" * 80, "header")
            self.log(f"결과 저장 위치: simulation_results/", "info")
            self.log(f"  - Gantt 차트: gantt_*.png", "info")
            self.log(f"  - 비교 그래프: comparison.png", "info")
            self.log(f"  - 상세 결과: results.txt", "info")
            
            self.status_label.config(text="시뮬레이션 완료 ✓")
            
            # 완료 메시지
            self.root.after(0, lambda: messagebox.showinfo(
                "완료", 
                f"시뮬레이션이 완료되었습니다!\n\n"
                f"실행된 알고리즘: {len(selected_algos)}개\n"
                f"결과 저장: simulation_results/ 폴더"
            ))
            
        except Exception as e:
            self.log(f"\n✗ 오류 발생: {str(e)}", "error")
            self.status_label.config(text="오류 발생")
            self.root.after(0, lambda: messagebox.showerror("오류", f"시뮬레이션 중 오류:\n{str(e)}"))
            
        finally:
            self.progress.stop()
            self.run_button.config(state='normal')
            
    def open_realtime_viewer(self):
        """실시간 시뮬레이션 뷰어 열기"""
        if not self.processes:
            messagebox.showwarning("경고", "먼저 프로세스를 로드하세요!")
            return
        
        # 알고리즘 선택 다이얼로그
        algo_dialog = tk.Toplevel(self.root)
        algo_dialog.title("실시간 시뮬레이션 설정")
        algo_dialog.geometry("450x600")
        algo_dialog.transient(self.root)
        algo_dialog.grab_set()
        
        # 알고리즘 선택 섹션
        ttk.Label(algo_dialog, text="알고리즘 선택:", 
                 font=("Arial", 11, "bold")).pack(pady=10)
        
        selected_algo = tk.StringVar()
        
        # 알고리즘 라디오 버튼들
        algos = [
            ('FCFS', 'FCFS'),
            ('SJF', 'SJF (Preemptive)'),
            ('Round Robin', 'Round Robin (q=4)'),
            ('Priority (Static)', 'Priority (정적)'),
            ('Priority with Aging', 'Priority + Aging'),
            ('Multi-Level Queue', 'Multi-Level Queue'),
            ('Rate Monotonic', 'Rate Monotonic (RM)'),
            ('EDF', 'EDF')
        ]
        
        algo_frame = ttk.Frame(algo_dialog)
        algo_frame.pack(pady=5)
        
        for key, display_name in algos:
            ttk.Radiobutton(algo_frame, text=display_name, 
                           variable=selected_algo, value=key).pack(anchor=tk.W, padx=20, pady=3)
        
        # 기본 선택
        selected_algo.set('FCFS')
        
        # 문맥교환 오버헤드 설정
        ttk.Separator(algo_dialog, orient='horizontal').pack(fill='x', pady=15)
        
        ttk.Label(algo_dialog, text="문맥교환 오버헤드 설정:", 
                 font=("Arial", 11, "bold")).pack(pady=5)
        
        cs_frame = ttk.Frame(algo_dialog)
        cs_frame.pack(pady=10)
        
        ttk.Label(cs_frame, text="오버헤드 (시간 단위):").pack(side=tk.LEFT, padx=5)
        
        cs_overhead_var = tk.IntVar(value=1)
        cs_spinbox = ttk.Spinbox(cs_frame, from_=0, to=10, width=10, 
                                 textvariable=cs_overhead_var)
        cs_spinbox.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(cs_frame, text="(0=없음, 1=기본)").pack(side=tk.LEFT, padx=5)
        
        # 설명
        info_text = tk.Text(algo_dialog, height=4, width=50, wrap=tk.WORD)
        info_text.pack(pady=10)
        info_text.insert('1.0', 
            "문맥교환 오버헤드는 프로세스가 전환될 때\n"
            "소요되는 시간입니다.\n"
            "0으로 설정하면 문맥교환이 즉시 발생하며,\n"
            "1 이상으로 설정하면 Gantt 차트에 CS 블록으로 표시됩니다.")
        info_text.config(state='disabled')
        
        def start_realtime():
            algo_key = selected_algo.get()
            cs_overhead = cs_overhead_var.get()
            if algo_key:
                algo_dialog.destroy()
                self._launch_realtime_viewer(algo_key, cs_overhead)
        
        ttk.Button(algo_dialog, text="▶️ 시작", command=start_realtime).pack(pady=15)
        ttk.Button(algo_dialog, text="✖ 취소", command=algo_dialog.destroy).pack()
        
    def _launch_realtime_viewer(self, algo_key: str, cs_overhead: int = 1):
        """실시간 뷰어 시작"""
        try:
            from realtime_viewer import RealtimeSimulationViewer
            import core.scheduler_base as scheduler_base
            
            # 문맥교환 오버헤드 설정
            original_overhead = scheduler_base.CONTEXT_SWITCH_OVERHEAD
            scheduler_base.CONTEXT_SWITCH_OVERHEAD = cs_overhead
            
            # 스케줄러 생성
            algo_info = self.algorithm_map[algo_key]
            scheduler = algo_info['class'](self.processes, **algo_info['params'])
            
            # 실시간 뷰어 생성 및 실행
            viewer = RealtimeSimulationViewer(scheduler, algo_key)
            viewer.run()
            
            # 원래 오버헤드로 복구
            scheduler_base.CONTEXT_SWITCH_OVERHEAD = original_overhead
            
            self.log(f"실시간 시뮬레이션 시작: {algo_key} (CS 오버헤드: {cs_overhead})", "info")
            
        except Exception as e:
            messagebox.showerror("오류", f"실시간 뷰어 실행 중 오류:\n{str(e)}")
            self.log(f"오류: {str(e)}", "error")
            import traceback
            traceback.print_exc()
    
    def open_results_folder(self):
        """결과 폴더 열기"""
        results_dir = "simulation_results"
        if os.path.exists(results_dir):
            os.startfile(results_dir)
            self.log(f"결과 폴더 열기: {results_dir}", "info")
        else:
            messagebox.showwarning("경고", "결과 폴더가 없습니다. 먼저 시뮬레이션을 실행하세요.")
            
            
    def log(self, message, tag=None):
        """로그 출력"""
        self.log_text.insert(tk.END, message + "\n", tag)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def run(self):
        """GUI 실행"""
        self.root.mainloop()


def main():
    """메인 함수"""
    app = SchedulerGUI()
    app.run()


if __name__ == "__main__":
    main()
