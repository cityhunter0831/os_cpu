#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OS 스케줄러 시뮬레이터 - 메인 실행 파일
알고리즘 선택 기능 포함
"""

import sys
import os
import re

# 모듈 임포트
from core.process import Process
from utils.input_parser import InputParser
from schedulers.basic_schedulers import FCFSScheduler, SJFScheduler, RoundRobinScheduler
from schedulers.advanced_schedulers import (PriorityScheduler, PriorityAgingScheduler, 
                                            MLQScheduler, RateMonotonicScheduler, EDFScheduler)
from utils.visualization import Visualizer
from schedulers.sync_demo import SyncDemoScheduler


# 사용 가능한 알고리즘 정의
ALGORITHMS = {
    '1': {
        'name': 'FCFS (First-Come, First-Served)',
        'class': FCFSScheduler,
        'params': {}
    },
    '2': {
        'name': 'SJF (Shortest Job First - Preemptive)',
        'class': SJFScheduler,
        'params': {}
    },
    '3': {
        'name': 'Round Robin',
        'class': RoundRobinScheduler,
        'params': {'time_slice': 4}
    },
    '4': {
        'name': 'Priority Scheduling (Static)',
        'class': PriorityScheduler,
        'params': {}
    },
    '5': {
        'name': 'Priority Scheduling with Aging',
        'class': PriorityAgingScheduler,
        'params': {'aging_factor': 10}
    },
    '6': {
        'name': 'Multi-Level Queue',
        'class': MLQScheduler,
        'params': {}
    },
    '7': {
        'name': 'Rate Monotonic (RM)',
        'class': RateMonotonicScheduler,
        'params': {}
    },
    '8': {
        'name': 'Earliest Deadline First (EDF)',
        'class': EDFScheduler,
        'params': {}
    },
    '9': {
        'name': 'Sync Demo: Producer-Consumer',
        'class': SyncDemoScheduler,
        'params': {'buffer_size': 3, 'rounds': 5}
    },
    'all': {
        'name': 'All Algorithms',
        'class': None,
        'params': {}
    }
}


def print_banner():
    """배너 출력"""
    print("\n" + "="*80)
    print(" "*25 + "운영체제 스케줄러 시뮬레이터")
    print("="*80 + "\n")


def print_algorithm_menu():
    """알고리즘 선택 메뉴 출력"""
    print("\n" + "="*80)
    print("스케줄링 알고리즘 선택")
    print("="*80)
    print("\n[기본 알고리즘]")
    print("  1. FCFS (First-Come, First-Served)")
    print("  2. SJF (Shortest Job First - Preemptive/SRTF)")
    print("  3. Round Robin (Time Slice = 4)")
    print("\n[우선순위 스케줄링]")
    print("  4. Priority Scheduling (정적)")
    print("  5. Priority Scheduling with Aging")
    print("\n[고급 알고리즘]")
    print("  6. Multi-Level Queue (3단계 피드백)")
    print("\n[실시간 스케줄링]")
    print("  7. Rate Monotonic (RM)")
    print("  8. Earliest Deadline First (EDF)")
    print("\n[특수 옵션]")
    print("  9. Sync Demo: Producer-Consumer (세마포어/뮤텍스)")
    print("  all. 모든 알고리즘 실행")
    print("  0. 종료")
    print("="*80)


def get_user_choice():
    """사용자 선택 입력"""
    while True:
        choice = input("\n선택하세요: ").strip()
        
        if choice == '0':
            print("\n프로그램을 종료합니다...")
            sys.exit(0)
        
        if choice in ALGORITHMS:
            return choice
        
        print("[오류] 잘못된 선택입니다. 다시 시도하세요.")


def run_single_algorithm(algorithm_key, processes, verbose=True):
    """단일 알고리즘 실행"""
    algo_info = ALGORITHMS[algorithm_key]
    
    print(f"\n{'='*80}")
    print(f"실행 중: {algo_info['name']}")
    print(f"{'='*80}\n")
    
    try:
        scheduler = algo_info['class'](processes, **algo_info['params'])
        result = scheduler.run(verbose=verbose)
        return result
    except Exception as e:
        print(f"[오류] {algo_info['name']} 실행 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_all_algorithms(processes, verbose=True):
    """모든 알고리즘 실행"""
    results = []
    
    print("\n" + "="*80)
    print("모든 스케줄링 알고리즘 실행")
    print("="*80 + "\n")
    
    for key in ['1', '2', '3', '4', '5', '6', '7', '8']:
        algo_info = ALGORITHMS[key]
        print(f"[{key}/8] {algo_info['name']} 실행 중...")
        
        try:
            scheduler = algo_info['class'](processes, **algo_info['params'])
            result = scheduler.run(verbose=verbose)
            results.append(result)
            print(f"[완료] {algo_info['name']} 완료\n")
        except Exception as e:
            print(f"[오류] {algo_info['name']} 실패: {e}\n")
    
    # 선택 과제: Sync Demo 실행 여부 물어보기
    print("\n" + "="*80)
    print("선택사항: 동기화 데모 (Producer-Consumer)")
    print("="*80)
    print("세마포어/뮤텍스를 사용한 프로세스 상태 전이를 시연합니다.")
    sync_choice = input("\nSync Demo를 실행하시겠습니까? (y/n, 기본값=y): ").strip().lower()
    
    if sync_choice != 'n':  # 엔터(빈 문자열) 또는 'y'면 실행
        print("\n[9] Sync Demo: Producer-Consumer 실행 중...")
        try:
            algo_info = ALGORITHMS['9']
            scheduler = algo_info['class'](processes, **algo_info['params'])
            result = scheduler.run(verbose=verbose)
            results.append(result)
            print(f"[완료] Sync Demo 완료\n")
        except Exception as e:
            print(f"[오류] Sync Demo 실패: {e}\n")
    else:
        print("[건너뜀] Sync Demo 건너뜀\n")
    
    return results


def save_results(results, output_dir="simulation_results"):
    """결과 저장"""
    os.makedirs(output_dir, exist_ok=True)
    
    visualizer = Visualizer()
    
    # 통계 테이블 출력
    print("\n" + "="*80)
    print("결과")
    print("="*80 + "\n")
    visualizer.print_statistics_table(results)
    
    # Gantt Charts 생성
    print("Gantt 차트 생성 중...")
    for result in results:
        # 파일명 안전하게 변환
        algo_name = result['algorithm']
        # 특수문자 제거 및 공백을 언더스코어로
        safe_algo = algo_name.replace(' ', '_').replace('/', '-')
        safe_algo = safe_algo.replace('(', '').replace(')', '')
        safe_algo = safe_algo.replace('=', '_').replace(':', '_')
        # 연속된 언더스코어 제거
        safe_algo = re.sub(r'_+', '_', safe_algo)
        # 마지막 언더스코어 제거
        safe_algo = safe_algo.strip('_')
        
        save_path = os.path.join(output_dir, f"gantt_{safe_algo}.png")
        visualizer.draw_gantt_chart(result['gantt_chart'], result['algorithm'], 
                                    save_path=save_path, show=False)
    print(f"[완료] Gantt 차트가 '{output_dir}/' 디렉토리에 저장되었습니다\n")
    
    # 비교 그래프 (2개 이상일 때만)
    if len(results) > 1:
        print("비교 차트 생성 중...")
        comparison_path = os.path.join(output_dir, "comparison.png")
        visualizer.compare_algorithms(results, save_path=comparison_path, show=False)
        print("[완료] 비교 차트 저장됨\n")
    
    # 상세 결과 저장
    results_file = os.path.join(output_dir, "results.txt")
    save_results_to_file(results, results_file)
    
    print(f"\n{'='*80}")
    print("시뮬레이션 완료")
    print(f"{'='*80}")
    print(f"\n결과가 '{output_dir}/' 디렉토리에 저장되었습니다:")
    print(f"  - Gantt 차트: gantt_*.png")
    if len(results) > 1:
        print(f"  - 비교 차트: comparison.png")
    print(f"  - 상세 결과: results.txt")
    print("="*80 + "\n")


def save_results_to_file(results, filename):
    """결과를 텍스트 파일로 저장"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("="*120 + "\n")
            f.write("OS 스케줄러 시뮬레이션 결과\n")
            f.write("="*120 + "\n\n")
            
            # 통계 비교
            f.write("성능 비교\n")
            f.write("-"*140 + "\n")
            f.write(f"{'알고리즘':<35} {'평균 대기':>12} {'평균 반환':>12} {'평균 응답':>12} {'CPU 이용률(%)':>15} {'문맥 교환':>12}\n")
            f.write("-"*140 + "\n")
            
            for result in results:
                algo = result['algorithm']
                stats = result['statistics']
                f.write(f"{algo:<35} "
                       f"{stats['avg_waiting_time']:>12.2f} "
                       f"{stats['avg_turnaround_time']:>12.2f} "
                       f"{stats['avg_response_time']:>12.2f} "
                       f"{stats['cpu_utilization']:>15.2f} "
                       f"{stats['context_switches']:>12}\n")
            
            f.write("="*120 + "\n\n")
            
            # 상세 결과
            for result in results:
                f.write("\n" + "="*120 + "\n")
                f.write(f"알고리즘: {result['algorithm']}\n")
                f.write("="*120 + "\n\n")
                
                f.write("프로세스 상세 정보:\n")
                f.write("-"*100 + "\n")
                f.write(f"{'PID':<6} {'도착시간':>8} {'우선순위':>10} {'시작':>8} {'완료':>8} "
                       f"{'대기':>8} {'반환':>8} {'응답':>10}\n")
                f.write("-"*100 + "\n")
                
                for process in result['processes']:
                    f.write(f"{process.pid:<6} "
                           f"{process.arrival_time:>8} "
                           f"{process.initial_priority:>10} "
                           f"{process.start_time:>8} "
                           f"{process.finish_time:>8} "
                           f"{process.waiting_time:>8} "
                           f"{process.turnaround_time:>8} "
                           f"{process.response_time if process.response_time is not None else 'N/A':>10}\n")
                
                f.write("\n")
        
        print(f"[완료] 결과가 {filename}에 저장되었습니다")
        
    except Exception as e:
        print(f"[오류] 결과 저장 실패: {e}")


def select_input_file():
    """입력 파일 선택"""
    print("\n" + "="*80)
    print("입력 파일 선택")
    print("="*80)
    
    # 현재 스크립트 파일의 디렉토리를 기준으로 data 폴더 경로 설정
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "data")
    professor_data = os.path.join(data_dir, "professor_data.txt")
    
    print("\n[입력 옵션]")
    print("  0. 교수 데이터 (권장) - professor_data.txt")
    print("  1. 랜덤 데이터 (자동 생성) - generated_input.txt")
    print("  2. 사용자 정의 데이터 (data/ 디렉토리에서 선택)")
    print("="*80)
    
    while True:
        choice = input("\n입력 옵션 선택 (0-2): ").strip()
        
        if choice == '0':
            # 교수 데이터
            if os.path.exists(professor_data):
                return professor_data
            else:
                print(f"[오류] 교수 데이터를 찾을 수 없습니다: {professor_data}")
                continue
        
        elif choice == '1':
            # 랜덤 데이터 생성 신호
            return "GENERATE_RANDOM"
        
        elif choice == '2':
            # 커스텀 데이터 선택
            if os.path.exists(data_dir):
                files = [f for f in os.listdir(data_dir) if f.endswith('.txt')]
                if files:
                    print("\n" + "-"*80)
                    print("data/ 디렉토리의 사용 가능한 파일:")
                    for i, file in enumerate(files, 1):
                        print(f"  {i}. {file}")
                    print("-"*80)
                    
                    file_choice = input("파일 번호 선택: ").strip()
                    try:
                        idx = int(file_choice) - 1
                        if 0 <= idx < len(files):
                            return os.path.join(data_dir, files[idx])
                        else:
                            print("[오류] 잘못된 파일 번호입니다.")
                            continue
                    except:
                        print("[오류] 잘못된 입력입니다.")
                        continue
                else:
                    print("[오류] data/ 디렉토리에 .txt 파일이 없습니다.")
                    continue
            else:
                print("[오류] data/ 디렉토리를 찾을 수 없습니다.")
                continue
        
        else:
            print("[오류] 잘못된 선택입니다. 0, 1, 또는 2를 입력하세요.")


def main():
    """메인 함수"""
    print_banner()
    
    # 입력 파일 선택
    input_file = select_input_file()
    
    # 랜덤 데이터 생성 요청인지 확인
    if input_file == "GENERATE_RANDOM":
        print("\n[정보] 랜덤 프로세스 생성 중...")
        processes = InputParser.generate_random_processes(num_processes=10, seed=None)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        generated_file = os.path.join(script_dir, "data", "generated_input.txt")
        os.makedirs(os.path.dirname(generated_file), exist_ok=True)
        InputParser.save_processes_to_file(processes, generated_file)
        print(f"[완료] 랜덤 프로세스가 {generated_file}에 저장되었습니다")
    else:
        # 파일에서 로드
        print(f"\n'{input_file}'에서 프로세스 로딩 중...")
        processes = InputParser.parse_file(input_file)
        
        if not processes:
            print("\n[오류] 프로세스 로드 실패 또는 파일이 비어있습니다.")
            sys.exit(1)
    
    # 프로세스 요약
    InputParser.print_process_summary(processes)
    
    # 알고리즘 선택 루프
    while True:
        print_algorithm_menu()
        choice = get_user_choice()
        
        if choice == 'all':
            # 모든 알고리즘 실행
            results = run_all_algorithms(processes, verbose=True)
            if results:
                save_results(results)
        else:
            # 단일 알고리즘 실행
            result = run_single_algorithm(choice, processes, verbose=True)
            if result:
                save_results([result])
        
        # 계속 여부 확인
        print("\n" + "="*80)
        continue_choice = input("다른 시뮬레이션을 실행하시겠습니까? (y/n): ").strip().lower()
        if continue_choice != 'y':
            print("\n운영체제 스케줄러 시뮬레이터를 사용해 주셔서 감사합니다!")
            print("="*80 + "\n")
            break


def select_mode():
    """실행 모드 선택 (CLI 또는 GUI)"""
    print("\n" + "="*80)
    print(" "*25 + "운영체제 스케줄러 시뮬레이터")
    print("="*80 + "\n")
    
    print("실행 모드를 선택하세요:")
    print("  1. CLI 모드 (콘솔)")
    print("  2. GUI 모드 (그래픽 인터페이스)")
    print()
    
    while True:
        choice = input("선택 (1 또는 2): ").strip()
        if choice == '1':
            return 'cli'
        elif choice == '2':
            return 'gui'
        else:
            print("[오류] 1 또는 2를 입력하세요.")


if __name__ == "__main__":
    try:
        mode = select_mode()
        
        if mode == 'gui':
            # GUI 모드 실행
            print("\nGUI 모드를 시작합니다...\n")
            from gui import SchedulerGUI
            app = SchedulerGUI()
            app.run()
        else:
            # CLI 모드 실행
            print("\nCLI 모드를 시작합니다...\n")
            main()
            
    except KeyboardInterrupt:
        print("\n\n사용자에 의해 시뮬레이션이 중단되었습니다.")
        print("="*80 + "\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n[오류] 예기치 않은 오류: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
