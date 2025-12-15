"""
웹 서버 실행 스크립트
백엔드 API 서버를 시작합니다.
"""

import subprocess
import sys
import os

def main():
    # 현재 디렉토리를 web 폴더로 설정
    web_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(web_dir, 'backend')
    
    print("=" * 60)
    print("  CPU 스케줄러 시뮬레이터 - 웹 서버")
    print("=" * 60)
    print()
    
    # 필요한 패키지 설치 확인
    try:
        import fastapi
        import uvicorn
    except ImportError:
        print("필요한 패키지를 설치합니다...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 
                       'fastapi', 'uvicorn', 'websockets', 'pydantic'])
    
    print("백엔드 서버를 시작합니다...")
    print("API 문서: http://localhost:8000/docs")
    print("프론트엔드: frontend/index.html을 브라우저에서 열거나")
    print("           npm start로 React 개발 서버를 실행하세요.")
    print()
    print("종료하려면 Ctrl+C를 누르세요.")
    print("-" * 60)
    
    # uvicorn 서버 실행
    os.chdir(backend_dir)
    subprocess.run([sys.executable, '-m', 'uvicorn', 'app:app', 
                   '--reload', '--host', '0.0.0.0', '--port', '8000'])

if __name__ == "__main__":
    main()
