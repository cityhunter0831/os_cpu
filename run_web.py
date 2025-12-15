#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
웹 버전 CPU 스케줄러 시뮬레이터 실행 파일
F5로 실행하면 서버 시작 후 브라우저가 자동으로 열립니다.
"""

import subprocess
import sys
import os
import time
import webbrowser
import socket

def is_port_in_use(port):
    """포트가 사용 중인지 확인"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port):
    """해당 포트를 사용하는 프로세스 종료 (Windows)"""
    try:
        result = subprocess.run(
            f'netstat -ano | findstr :{port}',
            shell=True, capture_output=True, text=True
        )
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    try:
                        subprocess.run(f'taskkill /PID {pid} /F', shell=True, capture_output=True)
                    except:
                        pass
    except:
        pass

def main():
    port = 8000
    url = f"http://localhost:{port}"
    
    # 현재 스크립트 위치 기준으로 backend 경로 설정
    script_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(script_dir, "web", "backend")
    
    print("=" * 60)
    print("       CPU 스케줄러 시뮬레이터 - 웹 버전")
    print("=" * 60)
    
    # 포트가 이미 사용 중인지 확인
    if is_port_in_use(port):
        print(f"\n⚠️  포트 {port}이 이미 사용 중입니다.")
        print("   기존 서버를 종료하고 새로 시작합니다...")
        kill_process_on_port(port)
        time.sleep(2)
    
    print(f"\n🚀 서버 시작 중... (포트: {port})")
    print(f"📂 백엔드 경로: {backend_dir}")
    
    # 서버 시작 (백그라운드)
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", str(port)],
        cwd=backend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # 서버가 시작될 때까지 대기
    print("\n⏳ 서버 준비 중...")
    for i in range(10):
        time.sleep(0.5)
        if is_port_in_use(port):
            break
    
    if is_port_in_use(port):
        print(f"\n✅ 서버가 시작되었습니다!")
        print(f"🌐 브라우저에서 열기: {url}")
        print("\n" + "-" * 60)
        print("종료하려면 Ctrl+C를 누르세요.")
        print("-" * 60 + "\n")
        
        # 브라우저 자동 열기
        webbrowser.open(url)
        
        # 서버 출력 표시
        try:
            while True:
                output = process.stdout.readline()
                if output:
                    print(output.strip())
                elif process.poll() is not None:
                    break
        except KeyboardInterrupt:
            print("\n\n🛑 서버를 종료합니다...")
            process.terminate()
            process.wait()
            print("👋 종료되었습니다.")
    else:
        print("\n❌ 서버 시작에 실패했습니다.")
        print("   uvicorn이 설치되어 있는지 확인하세요: pip install uvicorn")

if __name__ == "__main__":
    main()
