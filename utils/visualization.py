"""
시각화 모듈: Gantt Chart 및 통계 그래프 생성
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import List, Dict
from core.scheduler_base import GanttEntry
from core.process import ProcessState


class Visualizer:
    """스케줄링 결과 시각화"""
    
    def __init__(self):
        # 프로세스별 색상 설정
        self.colors = plt.cm.Set3.colors
        self.idle_color = '#CCCCCC'
        self.waiting_color = '#FFE5E5'
    
    def draw_gantt_chart(self, gantt_data: List[GanttEntry], algorithm_name: str, 
                        save_path: str = None, show: bool = True):
        """
        Gantt Chart 그리기
        
        Args:
            gantt_data: Gantt Chart 데이터
            algorithm_name: 알고리즘 이름
            save_path: 저장 경로 (None이면 저장 안 함)
            show: 화면에 표시할지 여부
        """
        if not gantt_data:
            print(f"{algorithm_name}에 대한 Gantt 차트 데이터가 없습니다")
            return
        
        fig, ax = plt.subplots(figsize=(16, 6))
        
        # 프로세스 ID 추출 (유일한 값만)
        unique_pids = sorted(set(entry.pid for entry in gantt_data if entry.pid != -1))
        pid_to_y = {pid: idx for idx, pid in enumerate(unique_pids)}
        
        # Gantt Chart 그리기
        for entry in gantt_data:
            if entry.pid == -1:
                # CPU 유휴 시간
                continue
            
            duration = entry.end_time - entry.start_time
            y_pos = pid_to_y[entry.pid]
            
            if entry.state == ProcessState.RUNNING:
                color = self.colors[entry.pid % len(self.colors)]
                alpha = 1.0
            elif entry.state == ProcessState.WAITING:
                color = self.waiting_color
                alpha = 0.7
            else:
                color = self.colors[entry.pid % len(self.colors)]
                alpha = 0.5
            
            ax.barh(y_pos, duration, left=entry.start_time, height=0.8, 
                   color=color, alpha=alpha, edgecolor='black', linewidth=0.5)
            
            # 프로세스 ID 표시
            if duration > 1:  # 충분히 긴 경우만 텍스트 표시
                ax.text(entry.start_time + duration/2, y_pos, f'P{entry.pid}', 
                       ha='center', va='center', fontsize=8, fontweight='bold')
        
        # 축 설정
        ax.set_yticks(range(len(unique_pids)))
        ax.set_yticklabels([f'P{pid}' for pid in unique_pids])
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Process', fontsize=12)
        ax.set_title(f'Gantt Chart - {algorithm_name}', fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        # 범례 추가
        legend_elements = [
            mpatches.Patch(color=self.colors[0], label='Running'),
            mpatches.Patch(color=self.waiting_color, alpha=0.7, label='I/O (Waiting)')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Gantt 차트가 {save_path}에 저장되었습니다")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def compare_algorithms(self, results: List[Dict], save_path: str = None, show: bool = True):
        """
        여러 알고리즘의 성능 비교 그래프
        
        Args:
            results: 각 알고리즘의 결과 리스트
            save_path: 저장 경로
            show: 화면에 표시할지 여부
        """
        if not results:
            print("비교할 결과가 없습니다")
            return
        
        algorithms = [r['algorithm'] for r in results]
        
        # 통계 데이터 추출
        avg_waiting_times = [r['statistics']['avg_waiting_time'] for r in results]
        avg_turnaround_times = [r['statistics']['avg_turnaround_time'] for r in results]
        cpu_utilizations = [r['statistics']['cpu_utilization'] for r in results]
        context_switches = [r['statistics']['context_switches'] for r in results]
        
        # 2x2 서브플롯 생성
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Scheduling Algorithms Performance Comparison', 
                    fontsize=16, fontweight='bold')
        
        # 1. 평균 대기 시간
        ax1 = axes[0, 0]
        bars1 = ax1.bar(range(len(algorithms)), avg_waiting_times, color='skyblue', edgecolor='black')
        ax1.set_xticks(range(len(algorithms)))
        ax1.set_xticklabels(algorithms, rotation=45, ha='right', fontsize=9)
        ax1.set_ylabel('Average Waiting Time', fontsize=11)
        ax1.set_title('Average Waiting Time Comparison', fontsize=12, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        
        # 값 표시
        for bar, value in zip(bars1, avg_waiting_times):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value:.2f}', ha='center', va='bottom', fontsize=9)
        
        # 2. 평균 반환 시간
        ax2 = axes[0, 1]
        bars2 = ax2.bar(range(len(algorithms)), avg_turnaround_times, color='lightcoral', edgecolor='black')
        ax2.set_xticks(range(len(algorithms)))
        ax2.set_xticklabels(algorithms, rotation=45, ha='right', fontsize=9)
        ax2.set_ylabel('Average Turnaround Time', fontsize=11)
        ax2.set_title('Average Turnaround Time Comparison', fontsize=12, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        
        for bar, value in zip(bars2, avg_turnaround_times):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value:.2f}', ha='center', va='bottom', fontsize=9)
        
        # 3. CPU 사용률
        ax3 = axes[1, 0]
        bars3 = ax3.bar(range(len(algorithms)), cpu_utilizations, color='lightgreen', edgecolor='black')
        ax3.set_xticks(range(len(algorithms)))
        ax3.set_xticklabels(algorithms, rotation=45, ha='right', fontsize=9)
        ax3.set_ylabel('CPU Utilization (%)', fontsize=11)
        ax3.set_title('CPU Utilization Comparison', fontsize=12, fontweight='bold')
        ax3.set_ylim(0, 100)
        ax3.grid(axis='y', alpha=0.3)
        
        for bar, value in zip(bars3, cpu_utilizations):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{value:.1f}%', ha='center', va='bottom', fontsize=9)
        
        # 4. 문맥 전환 횟수
        ax4 = axes[1, 1]
        bars4 = ax4.bar(range(len(algorithms)), context_switches, color='plum', edgecolor='black')
        ax4.set_xticks(range(len(algorithms)))
        ax4.set_xticklabels(algorithms, rotation=45, ha='right', fontsize=9)
        ax4.set_ylabel('Context Switches', fontsize=11)
        ax4.set_title('Context Switches Comparison', fontsize=12, fontweight='bold')
        ax4.grid(axis='y', alpha=0.3)
        
        for bar, value in zip(bars4, context_switches):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(value)}', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"비교 차트가 {save_path}에 저장되었습니다")
        
        if show:
            plt.show()
        else:
            plt.close()
    
    def print_statistics_table(self, results: List[Dict]):
        """
        통계를 표 형식으로 출력
        
        Args:
            results: 각 알고리즘의 결과 리스트
        """
        print("\n" + "="*140)
        print("스케줄링 알고리즘 성능 비교")
        print("="*140)
        print(f"{'알고리즘':<30} {'평균 대기':>12} {'평균 반환':>12} {'평균 응답':>12} {'CPU 이용률(%)':>15} {'문맥전환':>12}")
        print("-"*140)
        
        for result in results:
            algo = result['algorithm']
            stats = result['statistics']
            print(f"{algo:<30} "
                  f"{stats['avg_waiting_time']:>12.2f} "
                  f"{stats['avg_turnaround_time']:>12.2f} "
                  f"{stats['avg_response_time']:>12.2f} "
                  f"{stats['cpu_utilization']:>15.2f} "
                  f"{stats['context_switches']:>12}")
        
        print("="*140 + "\n")
    
    def print_process_details(self, results: Dict):
        """
        개별 프로세스의 상세 정보 출력
        
        Args:
            results: 알고리즘 실행 결과
        """
        print(f"\n{'='*80}")
        print(f"프로세스 상세 - {results['algorithm']}")
        print(f"{'='*80}")
        print(f"{'PID':<6} {'도착':>8} {'우선순위':>10} {'시작':>8} {'종료':>8} "
              f"{'대기':>8} {'반환':>8} {'응답':>10}")
        print(f"{'-'*80}")
        
        for process in results['processes']:
            print(f"{process.pid:<6} "
                  f"{process.arrival_time:>8} "
                  f"{process.initial_priority:>10} "
                  f"{process.start_time:>8} "
                  f"{process.finish_time:>8} "
                  f"{process.waiting_time:>8} "
                  f"{process.turnaround_time:>8} "
                  f"{process.response_time if process.response_time is not None else 'N/A':>10}")
        
        print(f"{'='*80}\n")
