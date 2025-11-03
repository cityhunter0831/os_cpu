# 운영체제 CPU 스케줄러 시뮬레이터

**9가지 CPU 스케줄링 알고리즘 + 동기화 시뮬레이터**

9가지 CPU 스케줄링 알고리즘(8개 필수 + 1개 선택 과제)을 구현하고, 실제 프로세스 데이터로 성능을 비교 분석하는 시뮬레이션 프로그램입니다.

---

## 목차
1. [빠른 시작](#빠른-시작)
2. [구현된 알고리즘](#구현된-알고리즘)
3. [선택 과제: 동기화](#선택-과제-동기화)
4. [실험 결과 분석](#실험-결과-분석)
5. [프로젝트 구조](#프로젝트-구조)
6. [입력 형식](#입력-형식)

---

## 빠른 시작

### 1. 설치
```bash
pip install matplotlib numpy
```

### 2. 실행
```bash
python main.py
```

**실행 시 모드 선택:**
- `1`: CLI 모드 (콘솔) - 텍스트 기반 대화형 인터페이스
- `2`: GUI 모드 (그래픽) - 마우스 클릭으로 간편한 조작 🎨

**대화형 모드**:
1. **입력 데이터 선택**:
   - `0`: 교수님 데이터 (권장) - `professor_data.txt`
   - `1`: 랜덤 데이터 생성 - `generated_input.txt` 자동 생성
   - `2`: 커스텀 데이터 - `data/` 폴더의 다른 파일 선택

2. **알고리즘 선택**:
   - `1-8`: 개별 알고리즘 실행
   - `9`: 동기화 데모 (Producer-Consumer)
   - `all`: **모든 알고리즘 실행 + 동기화 데모 자동 프롬프트** ⭐

3. **결과 확인**: 
   - 콘솔 출력
   - `simulation_results/` 폴더 (Gantt 차트, 비교 그래프, 상세 결과)

---

## 구현된 알고리즘

### 필수 알고리즘 (8개)

| # | 알고리즘 | 유형 | 특징 |
|---|---------|------|------|
| 1 | **FCFS** | 비선점 | 도착 순서대로 처리 |
| 2 | **SJF (SRTF)** | 선점 | 남은 CPU 시간 최단 우선 |
| 3 | **Round Robin** | 선점 | Time Slice=4, 순환 실행 |
| 4 | **Priority (Static)** | 선점 | 정적 우선순위 |
| 5 | **Priority + Aging** | 선점 | 동적 우선순위, 기아 방지 (factor=10) |
| 6 | **Multi-Level Queue** | 선점 | 3단계 큐 + Feedback (RR8/RR16/FCFS) |
| 7 | **Rate Monotonic (RM)** | 실시간 | 주기 기반 스케줄링 |
| 8 | **EDF** | 실시간 | 마감시한 기반 스케줄링 |

### 선택 과제 (1개)

| # | 알고리즘 | 유형 | 특징 |
|---|---------|------|------|
| 9 | **Sync Demo** | 동기화 | 생산자-소비자 + 세마포어/뮤텍스 + 교착상태 탐지 |

---

## 선택 과제: 동기화

### 구현 내용

#### ✅ 세마포어/뮤텍스 임계구역 관리
- **세마포어**: `empty(초기값=3)`, `full(초기값=0)`
- **뮤텍스**: 버퍼 접근 임계구역 보호
- **Wait/Signal**: 자원 대기 시 `Waiting` 상태 전이, 해제 시 `Ready` 복귀

#### ✅ 생산자-소비자 문제 시뮬레이션
- **Producer 1명** (P1): 5 라운드 생산
- **Consumer 1명** (P4): 5 라운드 소비
- **버퍼 크기**: 3
- **각 라운드**: 임계구역에서 2 시간 단위 CPU 작업

#### ✅ 동작 시퀀스
**Producer:**
```
1. WAIT(empty) → 빈 슬롯 대기 (없으면 Waiting)
2. LOCK(mutex) → 임계구역 진입 (점유 중이면 Waiting)
3. [임계구역] 2 시간 단위 CPU 작업 (생산)
4. UNLOCK(mutex) → 대기 프로세스 Ready 복귀
5. SIGNAL(full) → 소비자에게 알림
```

**Consumer:**
```
1. WAIT(full) → 항목 대기
2. LOCK(mutex) → 임계구역 진입
3. [임계구역] 2 시간 단위 CPU 작업 (소비)
4. UNLOCK(mutex)
5. SIGNAL(empty) → 생산자에게 알림
```

#### ✅ 교착상태 처리
- **Wait-For Graph** 기반 사이클 탐지
- 주기적 검사 (10 시간 단위)
- 교착 발견 시 희생자(Victim) 종료 및 락 해제

### 성능 결과

| 지표 | 값 | 설명 |
|-----|-----|------|
| 평균 대기 시간 | 42.50 | 동기화 대기 포함 |
| 평균 반환 시간 | 52.50 | |
| **CPU 사용률** | **35.09%** | 동기화 오버헤드 반영 ⭐ |
| 문맥 전환 | 9 | 블락/언블락 포함 |

**CPU 사용률 35%의 의미:**
- ✅ 정상적인 동기화 오버헤드
- 세마포어 대기 시간
- 뮤텍스 경쟁 (한쪽이 임계구역 점유 시 다른쪽 대기)
- 실제 시스템에서 동기화가 필요한 작업의 전형적인 패턴

### Gantt 차트
- **파란/노란색**: Running (임계구역 CPU 작업)
- **분홍색**: Waiting (세마포어/뮤텍스 대기) ⭐
- 프로세스 상태 전이가 명확히 시각화됨

---

## 실험 결과 분석

### 테스트 데이터 (professor_data.txt)
**7개 프로세스**: P1~P7  
**총 CPU 시간**: 83  
**총 I/O 시간**: 30  
**특징**: CPU-bound 중심 (I/O 비율 26.5%)

| PID | 도착 | 우선순위 | CPU | I/O | 설명 |
|-----|------|---------|-----|-----|------|
| P1  | 0    | 3       | 15  | No  | CPU-bound |
| P2  | 2    | 2       | 12  | Yes | I/O-bound |
| P3  | 5    | 1       | 8   | No  | 높은 우선순위 |
| P4  | 1    | 5       | 25  | No  | 낮은 우선순위, 긴 작업 |
| P5  | 0    | 0       | 4   | No  | 실시간 (주기=10) |
| P6  | 0    | 0       | 7   | No  | 실시간 (주기=25) |
| P7  | 8    | 4       | 12  | Yes | I/O-bound |

### 성능 비교표 (필수 알고리즘)

```
Algorithm                         Avg WT    Avg TAT   CPU Util%  Context SW
---------------------------------------------------------------------------
FCFS                               34.71      46.57       94.32           9
SJF (Preemptive/SRTF)              24.71      36.57      100.00           9
Round Robin (q=4)                  40.86      52.71      100.00          22
Priority (Static)                  25.00      36.86      100.00          12
Priority with Aging                28.43      40.29      100.00          54
Multi-Level Queue                  34.57      46.43      100.00          13
Rate Monotonic (RM)                 2.00       7.50      100.00           1
Earliest Deadline First (EDF)       2.00       7.50      100.00           1
```

### 핵심 분석

#### 1. 평균 대기 시간 (Avg WT)
- **최우수**: SJF (24.71) - 이론적 최적
- **양호**: Priority (25.00)
- **공정**: RR (40.86) - 공정하지만 비효율적
- **실시간**: RM, EDF (2.00) - 실시간 프로세스만 고려

#### 2. CPU 사용률
- **FCFS**: 94.32% - I/O 대기로 약간의 유휴
- **나머지**: 100% - 선점형 알고리즘의 효율성

#### 3. 문맥 전환
- **최소**: RM/EDF (1회) - 실시간 프로세스 2개만
- **일반**: FCFS/SJF (9회)
- **최대**: Priority + Aging (54회) - 동적 우선순위로 인한 빈번한 선점

**문맥 전환 카운팅 규칙:**
- CPU가 한 프로세스에서 다른 프로세스로 전환될 때만 카운트
- 같은 프로세스가 계속 실행되는 경우 제외
- 첫 프로세스 시작은 문맥 전환으로 카운트하지 않음

#### 4. 알고리즘별 특징

**FCFS**
- 간단하지만 Convoy Effect 발생
- P4(25) 때문에 다른 프로세스들 대기

**SJF**
- 평균 대기 시간 최소
- P4가 58까지 대기 (Starvation 가능)

**Round Robin**
- 공정하고 응답 시간 빠름
- 문맥 전환 많음 (오버헤드)

**Priority + Aging**
- 기아 현상 방지
- 문맥 전환 가장 많음 (54회)

**Multi-Level Queue**
- 상위 큐 (RR q=8): 대화형 작업
- 중간 큐 (RR q=16): 중간 작업
- 하위 큐 (FCFS): 긴 배치 작업
- 피드백으로 자동 큐 이동

### 알고리즘 선택 가이드

| 목적 | 권장 알고리즘 |
|-----|-------------|
| 평균 응답 시간 최소화 | SJF |
| 공정성 중요 | Round Robin |
| 기아 방지 | Priority + Aging |
| 대화형 시스템 | Multi-Level Queue |
| 실시간 시스템 | RM 또는 EDF |
| 동기화/임계구역 | Sync Demo |

---

## 프로젝트 구조

```
운영체제 최종본.코드/
├── README.md                        # 이 파일 (통합 문서)
├── gui.py                           # GUI 실행 프로그램 ⭐ (권장)
├── main.py                          # 콘솔 실행 프로그램
├── requirements.txt
├── core/
│   ├── process.py                   # 프로세스 클래스 (PCB)
│   ├── scheduler_base.py            # 스케줄러 기본 클래스
│   └── sync.py                      # 세마포어/뮤텍스/교착상태 탐지 ⭐
├── schedulers/
│   ├── basic_schedulers.py          # FCFS, SJF, RR
│   ├── advanced_schedulers.py       # Priority, MLQ, RM, EDF
│   └── sync_demo.py                 # 생산자-소비자 시뮬레이션 ⭐
├── utils/
│   ├── input_parser.py              # 파일 파싱
│   └── visualization.py             # Gantt Chart 생성
├── scripts/
│   └── report_generator.py          # 결과 보고서 생성기
├── data/
│   └── professor_data.txt           # 교수님 데이터
└── simulation_results/              # 시뮬레이션 결과 (자동 생성) ⭐
    ├── gantt_*.png                  # 9개 Gantt 차트
    ├── comparison.png               # 성능 비교 그래프
    ├── results.txt                  # 상세 통계
    └── OS_Scheduler_Report.docx     # Word 보고서
```

---

## 입력 형식

### 파일 형식
```csv
# PID,도착시간,우선순위,"실행패턴",주기,마감시한
# 모든 필드는 필수입니다.

1,0,3,"15",0,0              # CPU-bound (일반 프로세스)
2,2,2,"3,10,4,12,5",0,0     # I/O-bound (일반 프로세스)
5,0,0,"4",10,10             # 실시간 프로세스 (주기=10, 마감시한=10)
```

### 실행 패턴 설명
실행 패턴은 큰따옴표로 감싼 문자열이며, CPU 버스트와 I/O 버스트가 교대로 나타납니다.

- **짝수 인덱스 (0,2,4...)**: CPU 버스트 시간
- **홀수 인덱스 (1,3,5...)**: I/O 버스트 시간

**예시:**
- `"15"` = CPU만 15 시간 실행
- `"3,10,4,12,5"` = CPU(3) → I/O(10) → CPU(4) → I/O(12) → CPU(5)

**주의:** 실행 패턴은 반드시 CPU 버스트로 시작하고 끝나야 합니다.

---

## 주요 기능

### 필수 기능 ✅
- ✅ **8가지 CPU 스케줄링 알고리즘**
  - FCFS (비선점)
  - SJF - **선점형 (SRTF)** 구현
  - Round Robin - **기본 타임 슬라이스 = 4**
  - Priority (정적 및 **동적 with Aging**)
  - Multi-Level Queue - **3단계 큐 (RR8/RR16/FCFS) + 피드백**
  - Rate Monotonic (RM)
  - Earliest Deadline First (EDF)

- ✅ **프로세스 상태 관리 (PCB)**
  - Ready, Running, Waiting, Terminated
  - 상태 전이 정확히 구현

- ✅ **인터럽트 처리**
  - **타이머 인터럽트**: RR에서 타임 슬라이스 만료 시
  - **I/O 인터럽트**: I/O 요청 및 완료 시
  - **선점 인터럽트**: 우선순위 높은 프로세스 도착 시

- ✅ **I/O 작업 완벽 지원**
  - CPU 버스트와 I/O 버스트 교대 실행
  - I/O 완료 큐 관리
  - Waiting 상태 전이

- ✅ **Gantt Chart 시각화**
  - Running/Waiting 상태 구분 표시
  - 각 알고리즘별 차트 자동 생성

- ✅ **성능 지표 자동 계산**
  - 평균 대기 시간 = (반환 시간 - 총 버스트 시간)의 평균
  - 평균 반환 시간 = (완료 시간 - 도착 시간)의 평균
  - CPU 이용률 = (CPU 실행 시간 / 총 시뮬레이션 시간) × 100%
  - 문맥 전환 횟수 = 프로세스 변경 시에만 카운트

### 선택 과제 ✅
**동기화, 임계 구역, 교착상태 처리 완벽 구현:**

#### 1. **뮤텍스/세마포어 임계구역 관리** ✅
- `Mutex` 클래스: 상호 배제 보장
- `Semaphore` 클래스: 카운팅 세마포어 (empty/full)
- 임계구역 진입 시 lock 획득, 퇴출 시 unlock
- 위치: `core/sync.py`

#### 2. **생산자-소비자 문제 시뮬레이션** ✅
- 유한 버퍼 (기본 크기: 3)
- 생산자: `empty` 세마포어 대기 → mutex 획득 → 생산 → mutex 해제 → `full` 시그널
- 소비자: `full` 세마포어 대기 → mutex 획득 → 소비 → mutex 해제 → `empty` 시그널
- 위치: `schedulers/sync_demo.py`

#### 3. **프로세스 상태 전이 (Waiting ↔ Ready)** ✅
- **Lock 획득 실패 시**: `ProcessState.WAITING`으로 변경
- **Lock 해제 시**: 대기 중인 프로세스를 `ProcessState.READY`로 전환
- 스케줄러는 Waiting 프로세스를 건너뛰고 Ready 큐의 다음 프로세스 실행
- 로그 출력: `P{pid} → Waiting on {resource}`

#### 4. **교착상태 탐지 및 회복** ✅
- **탐지 방법**: Wait-For Graph (WFG) 기반 사이클 탐지
- **탐지 주기**: 매 10 시간 단위마다 자동 검사
- **회복 전략**: 교착상태 발견 시 가장 낮은 PID 프로세스 강제 종료 (Abort)
- **통계 출력**: 교착상태 검사 횟수 및 탐지 횟수
- 위치: `core/sync.py` (SyncManager.detect_deadlock)

#### 5. **동기화 오버헤드 측정** ✅
- 임계구역 진입/퇴출 시간 추적
- Waiting 상태 시간 측정
- Gantt Chart에 Waiting 상태 시각화

### 추가 기능
- ✅ **실시간 로그 출력** 📝
  - 프로세스 상태 변화 실시간 추적 (생성, 실행, 대기, 종료)
  - 문맥 전환 이벤트 로그
  - 시간별 상태 전이 기록
  - CLI/GUI 모두 지원
- ✅ **GUI 인터페이스** (Tkinter 기반) 🎨
  - 그래픽 사용자 인터페이스
  - 실시간 로그 창
  - 마우스 클릭으로 간편한 조작
- ✅ 대화형 콘솔 인터페이스 (한국어)
- ✅ all 실행 시 자동 Sync Demo 프롬프트
- ✅ 결과 자동 저장 (PNG, TXT)

---

## 실행 예시

```bash
$ python main.py

================================================================================
                         운영체제 스케줄러 시뮬레이터
================================================================================

실행 모드를 선택하세요:
  1. CLI 모드 (콘솔)
  2. GUI 모드 (그래픽 인터페이스)

선택 (1 또는 2): 2

GUI 모드를 시작합니다...
```

### CLI 모드 (1 선택 시)
```bash
선택 (1 또는 2): 1

CLI 모드를 시작합니다...

입력 옵션 선택 (0-2): 0
선택하세요: all

[1/8] FCFS (First-Come, First-Served) 실행 중...
[T=  0] ===== FCFS Scheduling Started =====
[T=  0] P1 arrived → Ready Queue
[T=  0] P5 arrived → Ready Queue
[T=  0] P6 arrived → Ready Queue
[T=  0] P1 → Running
[T= 15] P1 → Terminated (WT=0, TT=15)
[T= 15] Context Switch: P1 → P5
[T= 15] P5 → Running
[T= 19] P5 → Terminated (WT=15, TT=19)
[T= 19] Context Switch: P5 → P6
[T= 19] P6 → Running
[T= 26] P6 → I/O (duration=5) → Waiting
[T= 31] P6 I/O completed → Ready Queue
[T= 31] P6 → Running
[T= 38] P6 → Terminated (WT=12, TT=38)
[T= 38] ===== FCFS Scheduling Completed =====
[완료] FCFS 완료

...

[8/8] Earliest Deadline First (EDF) 실행 중...
[완료] Earliest Deadline First (EDF) 완료

========================================
선택사항: 동기화 데모 (Producer-Consumer)
========================================
세마포어/뮤텍스를 사용한 프로세스 상태 전이를 시연합니다.

Sync Demo를 실행하시겠습니까? (y/n, 기본값=y): [엔터]

[9] Sync Demo: Producer-Consumer 실행 중...
[완료] Sync Demo 완료

결과가 'simulation_results/' 디렉토리에 저장되었습니다:
  - Gantt 차트: gantt_*.png
  - 비교 차트: comparison.png
  - 상세 결과: results.txt
```

### GUI 모드 (2 선택 시)
GUI 창이 열리면:
1. **파일 로드**: "찾아보기" 버튼으로 입력 파일 선택
2. **알고리즘 선택**: 체크박스로 실행할 알고리즘 선택
3. **실행**: "🚀 시뮬레이션 실행" 버튼 클릭
4. **결과 확인**: "📊 결과 폴더 열기" 클릭

---

## 문제 해결

### matplotlib 오류
```bash
pip install matplotlib
```

### python-docx 오류
```bash
pip install python-docx
```

### 인코딩 오류 (Windows)
```bash
chcp 65001
python main.py
```

### 경로 오류
```bash
python main.py
```

---

## 학습 성과

이 프로젝트를 통해 다음을 학습했습니다:

### 핵심 개념
- CPU 스케줄링 알고리즘 8가지 완전 구현
- 프로세스 상태 전이 (PCB 관리)
- 인터럽트 처리 (Timer, I/O, Preemption)
- 실시간 스케줄링 (RM, EDF)

### 동기화 및 병행성
- 세마포어/뮤텍스 구현
- 생산자-소비자 문제
- 교착상태 탐지 및 회복
- 임계구역 관리

### 소프트웨어 공학
- 객체지향 설계 (Scheduler 계층 구조)
- 시뮬레이션 설계
- 데이터 시각화 (Gantt Chart)
- Python 프로그래밍 및 모듈 설계

---

**Operating System Scheduler Simulator - 2025**

**구현 완료 항목**
- ✅ 필수 알고리즘 8개 완전 구현
- ✅ 선택 과제 (동기화/교착상태 탐지)
- ✅ Gantt Chart 자동 생성
- ✅ 성능 지표 계산 및 비교
- ✅ 대화형 실행 인터페이스 (한국어)
- ✅ 자동 결과 저장 및 보고서 생성