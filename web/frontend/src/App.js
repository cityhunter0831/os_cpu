import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:8000';

// 프로세스 색상
const PROCESS_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
  '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788'
];

// Gantt 차트 컴포넌트
const GanttChart = ({ ganttData, processes }) => {
  if (!ganttData || ganttData.length === 0) {
    return (
      <div className="card p-8 text-center text-gray-400">
        시뮬레이션을 실행하면 Gantt 차트가 표시됩니다.
      </div>
    );
  }

  const maxTime = Math.max(...ganttData.map(g => g.end_time));
  const timeScale = Math.max(800 / maxTime, 15);
  const uniquePids = [...new Set(ganttData.filter(g => g.pid >= 0).map(g => g.pid))].sort((a, b) => a - b);
  
  const getColor = (pid) => {
    if (pid === -1) return '#374151'; // Idle
    if (pid === -2) return '#EF4444'; // Context Switch
    const idx = uniquePids.indexOf(pid);
    return PROCESS_COLORS[idx % PROCESS_COLORS.length];
  };

  return (
    <div className="card overflow-x-auto">
      <h3 className="text-lg font-semibold mb-4 text-purple-300">📊 Gantt Chart</h3>
      
      {/* 시간 축 */}
      <div className="flex items-center mb-2 ml-16">
        {Array.from({ length: Math.ceil(maxTime / 5) + 1 }, (_, i) => i * 5).map(t => (
          <div key={t} style={{ width: `${5 * timeScale}px` }} className="text-xs text-gray-400">
            {t}
          </div>
        ))}
      </div>

      {/* 프로세스별 행 */}
      {uniquePids.map(pid => (
        <div key={pid} className="flex items-center mb-1">
          <div className="w-16 text-sm font-medium" style={{ color: getColor(pid) }}>
            P{pid}
          </div>
          <div className="flex-1 h-8 bg-gray-800 rounded relative">
            {ganttData
              .filter(g => g.pid === pid)
              .map((entry, idx) => (
                <div
                  key={idx}
                  className="absolute h-full rounded gantt-bar flex items-center justify-center text-xs font-bold"
                  style={{
                    left: `${entry.start_time * timeScale}px`,
                    width: `${(entry.end_time - entry.start_time) * timeScale}px`,
                    backgroundColor: getColor(pid),
                    opacity: entry.state === 'Waiting' ? 0.4 : 1
                  }}
                  title={`P${pid}: ${entry.start_time}-${entry.end_time} (${entry.state})`}
                >
                  {(entry.end_time - entry.start_time) * timeScale > 25 && (
                    entry.state === 'Waiting' ? 'I/O' : `P${pid}`
                  )}
                </div>
              ))}
          </div>
        </div>
      ))}

      {/* Context Switch 행 */}
      {ganttData.some(g => g.pid === -2) && (
        <div className="flex items-center mb-1">
          <div className="w-16 text-sm font-medium text-red-400">CS</div>
          <div className="flex-1 h-8 bg-gray-800 rounded relative">
            {ganttData
              .filter(g => g.pid === -2)
              .map((entry, idx) => (
                <div
                  key={idx}
                  className="absolute h-full rounded gantt-bar flex items-center justify-center text-xs font-bold text-white"
                  style={{
                    left: `${entry.start_time * timeScale}px`,
                    width: `${(entry.end_time - entry.start_time) * timeScale}px`,
                    backgroundColor: '#EF4444'
                  }}
                  title={`Context Switch: ${entry.start_time}-${entry.end_time}`}
                >
                  {(entry.end_time - entry.start_time) * timeScale > 20 && 'CS'}
                </div>
              ))}
          </div>
        </div>
      )}

      {/* 범례 */}
      <div className="flex gap-4 mt-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: '#4ECDC4' }}></div>
          <span>Running</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded opacity-40" style={{ backgroundColor: '#4ECDC4' }}></div>
          <span>I/O (Waiting)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: '#EF4444' }}></div>
          <span>Context Switch</span>
        </div>
      </div>
    </div>
  );
};

// 통계 카드 컴포넌트
const StatCard = ({ label, value, unit = '' }) => (
  <div className="stat-card">
    <div className="stat-value">{value}{unit}</div>
    <div className="stat-label">{label}</div>
  </div>
);

// 프로세스 입력 폼 컴포넌트
const ProcessForm = ({ processes, setProcesses }) => {
  const [newProcess, setNewProcess] = useState({
    pid: processes.length + 1,
    arrival_time: 0,
    priority: 1,
    execution_pattern: '5',
    period: 0,
    deadline: 0
  });

  const addProcess = () => {
    const pattern = newProcess.execution_pattern.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n));
    if (pattern.length === 0) {
      alert('실행 패턴을 입력하세요.');
      return;
    }

    setProcesses([...processes, {
      ...newProcess,
      execution_pattern: pattern
    }]);

    setNewProcess({
      pid: processes.length + 2,
      arrival_time: 0,
      priority: 1,
      execution_pattern: '5',
      period: 0,
      deadline: 0
    });
  };

  const removeProcess = (pid) => {
    setProcesses(processes.filter(p => p.pid !== pid));
  };

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4 text-purple-300">📝 프로세스 입력</h3>
      
      {/* 입력 폼 */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-4">
        <div>
          <label className="text-xs text-gray-400 block mb-1">PID</label>
          <input
            type="number"
            className="input-field"
            value={newProcess.pid}
            onChange={e => setNewProcess({ ...newProcess, pid: parseInt(e.target.value) })}
          />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">도착 시간</label>
          <input
            type="number"
            className="input-field"
            value={newProcess.arrival_time}
            onChange={e => setNewProcess({ ...newProcess, arrival_time: parseInt(e.target.value) })}
          />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">우선순위</label>
          <input
            type="number"
            className="input-field"
            value={newProcess.priority}
            onChange={e => setNewProcess({ ...newProcess, priority: parseInt(e.target.value) })}
          />
        </div>
        <div className="col-span-2">
          <label className="text-xs text-gray-400 block mb-1">실행 패턴 (CPU,IO,CPU,...)</label>
          <input
            type="text"
            className="input-field"
            placeholder="예: 5,3,5"
            value={newProcess.execution_pattern}
            onChange={e => setNewProcess({ ...newProcess, execution_pattern: e.target.value })}
          />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">주기 (RM/EDF)</label>
          <input
            type="number"
            className="input-field"
            value={newProcess.period}
            onChange={e => setNewProcess({ ...newProcess, period: parseInt(e.target.value) })}
          />
        </div>
        <div>
          <label className="text-xs text-gray-400 block mb-1">마감시한 (EDF)</label>
          <input
            type="number"
            className="input-field"
            value={newProcess.deadline}
            onChange={e => setNewProcess({ ...newProcess, deadline: parseInt(e.target.value) })}
          />
        </div>
      </div>
      
      <button onClick={addProcess} className="btn-primary mb-4">
        + 프로세스 추가
      </button>

      {/* 프로세스 목록 */}
      {processes.length > 0 && (
        <div className="overflow-x-auto">
          <table className="process-table">
            <thead>
              <tr>
                <th>PID</th>
                <th>도착</th>
                <th>우선순위</th>
                <th>실행 패턴</th>
                <th>주기</th>
                <th>마감</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {processes.map(p => (
                <tr key={p.pid}>
                  <td className="font-bold" style={{ color: PROCESS_COLORS[(p.pid - 1) % PROCESS_COLORS.length] }}>
                    P{p.pid}
                  </td>
                  <td>{p.arrival_time}</td>
                  <td>{p.priority}</td>
                  <td>{p.execution_pattern.join(', ')}</td>
                  <td>{p.period || '-'}</td>
                  <td>{p.deadline || '-'}</td>
                  <td>
                    <button
                      onClick={() => removeProcess(p.pid)}
                      className="text-red-400 hover:text-red-300"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// 알고리즘 선택 컴포넌트
const AlgorithmSelector = ({ algorithms, selectedAlgorithms, setSelectedAlgorithms }) => {
  const toggleAlgorithm = (id) => {
    if (selectedAlgorithms.includes(id)) {
      setSelectedAlgorithms(selectedAlgorithms.filter(a => a !== id));
    } else {
      setSelectedAlgorithms([...selectedAlgorithms, id]);
    }
  };

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4 text-purple-300">⚙️ 알고리즘 선택</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {algorithms.map(algo => (
          <label
            key={algo.id}
            className={`flex items-center gap-2 p-3 rounded-lg cursor-pointer transition-all ${
              selectedAlgorithms.includes(algo.id)
                ? 'bg-purple-600/30 border border-purple-500'
                : 'bg-gray-800/50 border border-gray-700 hover:border-gray-600'
            }`}
          >
            <input
              type="checkbox"
              className="checkbox-custom"
              checked={selectedAlgorithms.includes(algo.id)}
              onChange={() => toggleAlgorithm(algo.id)}
            />
            <div>
              <div className="font-medium text-sm">{algo.id}</div>
              <div className="text-xs text-gray-400">{algo.preemptive ? '선점형' : '비선점형'}</div>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
};

// 결과 표시 컴포넌트
const ResultsView = ({ results }) => {
  const [activeTab, setActiveTab] = useState(0);

  if (!results || results.length === 0) return null;

  const currentResult = results[activeTab];

  return (
    <div className="space-y-4">
      {/* 탭 */}
      {results.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-2">
          {results.map((r, idx) => (
            <button
              key={idx}
              onClick={() => setActiveTab(idx)}
              className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-all ${
                activeTab === idx ? 'tab-active' : 'tab-inactive hover:bg-gray-700'
              }`}
            >
              {r.algorithm}
            </button>
          ))}
        </div>
      )}

      {/* 통계 */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatCard label="평균 대기 시간" value={currentResult.statistics.avg_waiting_time?.toFixed(2) || '0'} />
        <StatCard label="평균 반환 시간" value={currentResult.statistics.avg_turnaround_time?.toFixed(2) || '0'} />
        <StatCard label="평균 응답 시간" value={currentResult.statistics.avg_response_time?.toFixed(2) || '0'} />
        <StatCard label="CPU 이용률" value={currentResult.statistics.cpu_utilization?.toFixed(1) || '0'} unit="%" />
        <StatCard label="문맥교환 횟수" value={currentResult.statistics.context_switches || '0'} unit="회" />
      </div>

      {/* Gantt 차트 */}
      <GanttChart ganttData={currentResult.gantt_chart} processes={currentResult.processes} />

      {/* 프로세스 결과 테이블 */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-purple-300">📋 프로세스 결과</h3>
        <div className="overflow-x-auto">
          <table className="process-table">
            <thead>
              <tr>
                <th>PID</th>
                <th>도착 시간</th>
                <th>버스트 시간</th>
                <th>대기 시간</th>
                <th>반환 시간</th>
                <th>응답 시간</th>
              </tr>
            </thead>
            <tbody>
              {currentResult.processes.map(p => (
                <tr key={p.pid}>
                  <td className="font-bold" style={{ color: PROCESS_COLORS[(p.pid - 1) % PROCESS_COLORS.length] }}>
                    P{p.pid}
                  </td>
                  <td>{p.arrival_time}</td>
                  <td>{p.burst_time}</td>
                  <td>{p.waiting_time}</td>
                  <td>{p.turnaround_time}</td>
                  <td>{p.response_time ?? '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 이벤트 로그 */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-purple-300">📝 이벤트 로그</h3>
        <div className="max-h-60 overflow-y-auto space-y-1">
          {currentResult.event_log.map((log, idx) => {
            let className = 'log-entry log-time';
            if (log.includes('Context Switch')) className = 'log-entry log-cs';
            else if (log.includes('arrived') || log.includes('completed')) className = 'log-entry log-event';
            else if (log.includes('Running') || log.includes('Terminated')) className = 'log-entry log-process';
            
            return (
              <div key={idx} className={className}>{log}</div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

// 실시간 시뮬레이션 컴포넌트
const RealtimeSimulation = ({ processes, algorithm, contextSwitchOverhead, timeSlice }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [stats, setStats] = useState({ current_time: 0, context_switches: 0, completed: 0, total: 0 });
  const [ganttData, setGanttData] = useState([]);
  const [logs, setLogs] = useState([]);
  const [running, setRunning] = useState(null);
  const [readyQueue, setReadyQueue] = useState([]);
  const [waitingQueue, setWaitingQueue] = useState([]);
  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  const connect = useCallback(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/realtime`);
    
    ws.onopen = () => {
      ws.send(JSON.stringify({
        action: 'init',
        processes: processes,
        algorithm: algorithm,
        context_switch_overhead: contextSwitchOverhead,
        time_slice: timeSlice
      }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'initialized') {
        setStats({ current_time: 0, context_switches: 0, completed: 0, total: data.process_count });
        setGanttData([]);
        setLogs([]);
        setIsComplete(false);
      } else if (data.type === 'step_result') {
        if (data.new_gantt) {
          setGanttData(prev => [...prev, ...data.new_gantt]);
        }
        if (data.new_logs) {
          setLogs(prev => [...prev, ...data.new_logs]);
        }
        setStats(data.stats);
        setRunning(data.running);
        setReadyQueue(data.ready_queue || []);
        setWaitingQueue(data.waiting_queue || []);
        
        if (data.complete) {
          setIsComplete(true);
          setIsRunning(false);
          setIsPaused(false);
        }
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;
    return ws;
  }, [processes, algorithm, contextSwitchOverhead, timeSlice]);

  const startSimulation = () => {
    setGanttData([]);
    setLogs([]);
    setIsComplete(false);
    connect();
  };

  const step = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'step' }));
    }
  };

  const play = () => {
    setIsRunning(true);
    setIsPaused(false);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'run', speed: speed }));
    }
  };

  const pause = () => {
    setIsPaused(true);
    setIsRunning(false);
  };

  const reset = () => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    setIsRunning(false);
    setIsPaused(false);
    setIsComplete(false);
    setGanttData([]);
    setLogs([]);
    setStats({ current_time: 0, context_switches: 0, completed: 0, total: 0 });
    setRunning(null);
    setReadyQueue([]);
    setWaitingQueue([]);
  };

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <div className="space-y-4">
      {/* 컨트롤 패널 */}
      <div className="card">
        <div className="flex flex-wrap items-center gap-4">
          <button onClick={startSimulation} className="btn-primary" disabled={isRunning}>
            🔄 초기화
          </button>
          <button onClick={play} className="btn-primary" disabled={isRunning || isComplete || !wsRef.current}>
            ▶️ 재생
          </button>
          <button onClick={pause} className="btn-secondary" disabled={!isRunning}>
            ⏸️ 일시정지
          </button>
          <button onClick={step} className="btn-secondary" disabled={isRunning || isComplete || !wsRef.current}>
            ⏭️ 단계 실행
          </button>
          <button onClick={reset} className="btn-secondary">
            🗑️ 리셋
          </button>
          
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-sm text-gray-400">속도:</span>
            <input
              type="range"
              min="0.5"
              max="5"
              step="0.5"
              value={speed}
              onChange={e => setSpeed(parseFloat(e.target.value))}
              className="w-24"
            />
            <span className="text-sm font-medium">{speed}x</span>
          </div>
        </div>
      </div>

      {/* 상태 표시 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="현재 시간" value={`T = ${stats.current_time}`} />
        <StatCard label="문맥교환" value={stats.context_switches} unit="회" />
        <StatCard label="CPU 이용률" value={stats.cpu_busy_time ? ((stats.cpu_busy_time / stats.current_time) * 100).toFixed(1) : '0'} unit="%" />
        <StatCard label="완료" value={`${stats.completed} / ${stats.total}`} />
      </div>

      {/* 프로세스 상태 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <h4 className="font-semibold text-green-400 mb-2">🏃 Running</h4>
          {running ? (
            <div className="text-sm">
              <div className="font-bold" style={{ color: PROCESS_COLORS[(running.pid - 1) % PROCESS_COLORS.length] }}>
                P{running.pid}
              </div>
              <div className="text-gray-400">남은 시간: {running.remaining}</div>
              <div className="text-gray-400">우선순위: {running.priority}</div>
            </div>
          ) : (
            <div className="text-gray-500">CPU Idle</div>
          )}
        </div>
        
        <div className="card">
          <h4 className="font-semibold text-yellow-400 mb-2">📋 Ready Queue</h4>
          {readyQueue.length > 0 ? (
            <div className="space-y-1">
              {readyQueue.map((p, idx) => (
                <div key={idx} className="text-sm" style={{ color: PROCESS_COLORS[(p.pid - 1) % PROCESS_COLORS.length] }}>
                  P{p.pid} (rem={p.remaining})
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-500">Empty</div>
          )}
        </div>
        
        <div className="card">
          <h4 className="font-semibold text-blue-400 mb-2">⏳ Waiting Queue</h4>
          {waitingQueue.length > 0 ? (
            <div className="space-y-1">
              {waitingQueue.map((p, idx) => (
                <div key={idx} className="text-sm" style={{ color: PROCESS_COLORS[(p.pid - 1) % PROCESS_COLORS.length] }}>
                  P{p.pid} (I/O)
                </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-500">Empty</div>
          )}
        </div>
      </div>

      {/* Gantt 차트 */}
      <GanttChart ganttData={ganttData} processes={processes} />

      {/* 이벤트 로그 */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-purple-300">📝 이벤트 로그</h3>
        <div className="max-h-48 overflow-y-auto space-y-1">
          {logs.map((log, idx) => {
            let className = 'log-entry log-time';
            if (log.includes('Context Switch')) className = 'log-entry log-cs';
            else if (log.includes('arrived') || log.includes('completed')) className = 'log-entry log-event';
            else if (log.includes('Running') || log.includes('Terminated')) className = 'log-entry log-process';
            
            return (
              <div key={idx} className={className}>{log}</div>
            );
          })}
          <div ref={logsEndRef} />
        </div>
      </div>

      {/* 완료 메시지 */}
      {isComplete && stats.final && (
        <div className="card bg-green-900/30 border-green-500">
          <h3 className="text-lg font-semibold text-green-400 mb-4">✅ 시뮬레이션 완료!</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatCard label="평균 대기 시간" value={stats.final.avg_waiting_time?.toFixed(2) || '0'} />
            <StatCard label="평균 반환 시간" value={stats.final.avg_turnaround_time?.toFixed(2) || '0'} />
            <StatCard label="CPU 이용률" value={stats.final.cpu_utilization?.toFixed(1) || '0'} unit="%" />
            <StatCard label="문맥교환" value={stats.final.context_switches || '0'} unit="회" />
          </div>
        </div>
      )}
    </div>
  );
};

// 메인 App 컴포넌트
function App() {
  const [mode, setMode] = useState('batch'); // 'batch' or 'realtime'
  const [processes, setProcesses] = useState([]);
  const [algorithms, setAlgorithms] = useState([]);
  const [selectedAlgorithms, setSelectedAlgorithms] = useState(['FCFS']);
  const [contextSwitchOverhead, setContextSwitchOverhead] = useState(1);
  const [timeSlice, setTimeSlice] = useState(4);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [realtimeAlgorithm, setRealtimeAlgorithm] = useState('FCFS');

  // 알고리즘 목록 로드
  useEffect(() => {
    axios.get(`${API_URL}/algorithms`)
      .then(res => setAlgorithms(res.data.algorithms))
      .catch(err => console.error('Failed to load algorithms:', err));
  }, []);

  // 샘플 데이터 로드
  const loadSample = async (sampleIndex) => {
    try {
      const res = await axios.get(`${API_URL}/sample-processes`);
      const sample = res.data.samples[sampleIndex];
      setProcesses(sample.processes);
    } catch (err) {
      console.error('Failed to load sample:', err);
    }
  };

  // 시뮬레이션 실행
  const runSimulation = async () => {
    if (processes.length === 0) {
      alert('프로세스를 추가하세요.');
      return;
    }
    if (selectedAlgorithms.length === 0) {
      alert('알고리즘을 선택하세요.');
      return;
    }

    setLoading(true);
    try {
      const res = await axios.post(`${API_URL}/simulate`, {
        processes,
        algorithms: selectedAlgorithms,
        context_switch_overhead: contextSwitchOverhead,
        time_slice: timeSlice
      });
      setResults(res.data.results);
    } catch (err) {
      console.error('Simulation failed:', err);
      alert('시뮬레이션 실행 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen p-4 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* 헤더 */}
        <header className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            CPU 스케줄러 시뮬레이터
          </h1>
          <p className="text-gray-400 mt-2">운영체제 스케줄링 알고리즘 시각화 도구</p>
        </header>

        {/* 모드 선택 */}
        <div className="flex justify-center gap-4 mb-6">
          <button
            onClick={() => setMode('batch')}
            className={`px-6 py-3 rounded-lg font-medium transition-all ${
              mode === 'batch' ? 'tab-active' : 'tab-inactive hover:bg-gray-700'
            }`}
          >
            📊 일괄 시뮬레이션
          </button>
          <button
            onClick={() => setMode('realtime')}
            className={`px-6 py-3 rounded-lg font-medium transition-all ${
              mode === 'realtime' ? 'tab-active' : 'tab-inactive hover:bg-gray-700'
            }`}
          >
            ⏱️ 실시간 시뮬레이션
          </button>
        </div>

        {/* 샘플 데이터 버튼 */}
        <div className="flex justify-center gap-2 mb-6">
          <span className="text-gray-400 text-sm">샘플 데이터:</span>
          <button onClick={() => loadSample(0)} className="btn-secondary text-sm">기본 테스트</button>
          <button onClick={() => loadSample(1)} className="btn-secondary text-sm">I/O 포함</button>
          <button onClick={() => loadSample(2)} className="btn-secondary text-sm">실시간 (RM/EDF)</button>
        </div>

        {/* 프로세스 입력 */}
        <div className="mb-6">
          <ProcessForm processes={processes} setProcesses={setProcesses} />
        </div>

        {/* 설정 */}
        <div className="card mb-6">
          <h3 className="text-lg font-semibold mb-4 text-purple-300">⚙️ 설정</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm text-gray-400 block mb-1">문맥교환 오버헤드 (시간 단위)</label>
              <input
                type="number"
                className="input-field"
                min="0"
                max="10"
                value={contextSwitchOverhead}
                onChange={e => setContextSwitchOverhead(parseInt(e.target.value))}
              />
              <p className="text-xs text-gray-500 mt-1">0 = 오버헤드 없음, 1 이상 = Gantt 차트에 CS 표시</p>
            </div>
            <div>
              <label className="text-sm text-gray-400 block mb-1">Round Robin 타임 슬라이스</label>
              <input
                type="number"
                className="input-field"
                min="1"
                max="20"
                value={timeSlice}
                onChange={e => setTimeSlice(parseInt(e.target.value))}
              />
            </div>
          </div>
        </div>

        {mode === 'batch' ? (
          <>
            {/* 알고리즘 선택 */}
            <div className="mb-6">
              <AlgorithmSelector
                algorithms={algorithms}
                selectedAlgorithms={selectedAlgorithms}
                setSelectedAlgorithms={setSelectedAlgorithms}
              />
            </div>

            {/* 실행 버튼 */}
            <div className="text-center mb-6">
              <button
                onClick={runSimulation}
                className="btn-primary text-lg px-8 py-3"
                disabled={loading || processes.length === 0}
              >
                {loading ? '⏳ 실행 중...' : '🚀 시뮬레이션 실행'}
              </button>
            </div>

            {/* 결과 */}
            <ResultsView results={results} />
          </>
        ) : (
          <>
            {/* 실시간 알고리즘 선택 */}
            <div className="card mb-6">
              <h3 className="text-lg font-semibold mb-4 text-purple-300">⚙️ 알고리즘 선택</h3>
              <select
                className="select-field"
                value={realtimeAlgorithm}
                onChange={e => setRealtimeAlgorithm(e.target.value)}
              >
                {algorithms.map(algo => (
                  <option key={algo.id} value={algo.id}>{algo.name}</option>
                ))}
              </select>
            </div>

            {/* 실시간 시뮬레이션 */}
            {processes.length > 0 ? (
              <RealtimeSimulation
                processes={processes}
                algorithm={realtimeAlgorithm}
                contextSwitchOverhead={contextSwitchOverhead}
                timeSlice={timeSlice}
              />
            ) : (
              <div className="card text-center text-gray-400 py-8">
                프로세스를 추가하고 시뮬레이션을 시작하세요.
              </div>
            )}
          </>
        )}

        {/* 푸터 */}
        <footer className="text-center text-gray-500 text-sm mt-8 pb-4">
          운영체제 CPU 스케줄링 시뮬레이터 v1.0
        </footer>
      </div>
    </div>
  );
}

export default App;
