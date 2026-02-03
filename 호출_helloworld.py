#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Render에 배포된 hello world 서비스 호출 스크립트
사용법: python 호출_helloworld.py
"""
import sys
import requests

# 윈도우 환경에서 UTF-8 출력이 가능하도록 설정
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def call_hello_world(base_url="https://hello-world-fo9c.onrender.com"):
    """
    Render에 배포된 hello world 서비스의 엔드포인트들을 호출하고 결과를 출력합니다.

    Args:
        base_url (str): Render 서비스의 기본 URL
    """
    print(f"[START] Render 서비스 호출 중: {base_url}\n")

    # 1. 루트 엔드포인트 호출 (hello, world)
    print("[INFO] GET / 요청 중...")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        response.raise_for_status()
        print(f"[OK] 상태 코드: {response.status_code}")
        print(f"[OK] 응답 내용: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 요청 실패: {e}")

    print("\n" + "-" * 50 + "\n")

    # 2. 헬스체크 엔드포인트 호출
    print("[INFO] GET /health 요청 중...")
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        response.raise_for_status()
        print(f"[OK] 상태 코드: {response.status_code}")
        print(f"[OK] 응답 내용: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 요청 실패: {e}")

    print("\n" + "=" * 50)
    print("[DONE] 모든 요청 완료!")


if __name__ == "__main__":
    call_hello_world()
