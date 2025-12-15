# CPU 스케줄러 시뮬레이터 - 웹 버전

운영체제 CPU 스케줄링 알고리즘을 시각화하는 웹 애플리케이션입니다.

## 기능

### 일괄 시뮬레이션
- 여러 알고리즘을 동시에 실행하고 비교
- Gantt 차트 시각화
- 프로세스별 통계 (대기 시간, 반환 시간, 응답 시간)
- 알고리즘별 성능 비교

### 실시간 시뮬레이션
- 시간의 흐름에 따른 스케줄링 과정 시각화
- 재생/일시정지/단계 실행 컨트롤
- 속도 조절 (0.5x ~ 5x)
- Ready Queue, Waiting Queue 실시간 표시
- 이벤트 로그 실시간 업데이트

### 지원 알고리즘
- **FCFS** (First-Come, First-Served) - 비선점형
- **SJF** (Shortest Job First) - 선점형 (SRTF)
- **Round Robin** - 선점형, 타임 슬라이스 설정 가능
- **Priority** (정적 우선순위) - 선점형
- **Priority with Aging** (동적 우선순위) - 선점형
- **Multi-Level Queue** - 선점형, 피드백 포함
- **Rate Monotonic** - 실시간 스케줄링
- **EDF** (Earliest Deadline First) - 실시간 스케줄링

### 설정 옵션
- **문맥교환 오버헤드**: 0~10 시간 단위 설정 가능
- **타임 슬라이스**: Round Robin 알고리즘용

## 실행 방법

### 1. 백엔드 서버 실행

```bash
cd web
python run_server.py
```

또는 직접 uvicorn 실행:
```bash
cd web/backend
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

API 문서: http://localhost:8000/docs

### 2. 프론트엔드 실행

#### 방법 A: 정적 HTML (간단)
`frontend/index.html`을 브라우저에서 직접 열기
(CORS 문제로 일부 기능 제한될 수 있음)

#### 방법 B: React 개발 서버 (권장)
```bash
cd web/frontend
npm install
npm start
```

브라우저에서 http://localhost:3000 접속

## 프로젝트 구조

```
web/
├── backend/
│   ├── app.py              # FastAPI 백엔드 서버
│   └── requirements.txt    # Python 의존성
├── frontend/
│   ├── public/
│   │   └── index.html      # HTML 템플릿
│   ├── src/
│   │   ├── App.js          # 메인 React 컴포넌트
│   │   ├── index.js        # React 엔트리 포인트
│   │   └── index.css       # 스타일시트
│   └── package.json        # npm 의존성
├── run_server.py           # 서버 실행 스크립트
└── README.md               # 이 파일
```

## API 엔드포인트

### REST API
- `GET /` - API 정보
- `GET /algorithms` - 사용 가능한 알고리즘 목록
- `GET /sample-processes` - 샘플 프로세스 데이터
- `POST /simulate` - 시뮬레이션 실행
- `POST /simulate/compare` - 알고리즘 비교 시뮬레이션

### WebSocket
- `WS /ws/realtime` - 실시간 시뮬레이션

## 프로세스 입력 형식

```json
{
  "pid": 1,
  "arrival_time": 0,
  "priority": 1,
  "execution_pattern": [5, 3, 5],  // CPU, I/O, CPU, ...
  "period": 0,      // 실시간 프로세스용 (RM)
  "deadline": 0     // 실시간 프로세스용 (EDF)
}
```

## 기술 스택

### 백엔드
- Python 3.8+
- FastAPI
- Uvicorn
- WebSockets

### 프론트엔드
- React 18
- Axios
- Tailwind CSS (CDN)
- Recharts (차트)

## 라이선스

교육 목적으로 제작되었습니다.
