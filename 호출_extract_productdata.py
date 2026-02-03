#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Render에 배포된 /extract_productdata 엔드포인트 호출 스크립트
nvmid는 커맨드 라인 인자로 입력, 쿠키는 로컬 파일에서 로드
사용법: python 호출_extract_productdata.py <nvmid>
"""
import sys
import json
import requests
from pathlib import Path

# 윈도우 환경에서 UTF-8 출력이 가능하도록 설정
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_cookies_from_file(cookies_path: Path) -> str:
    """
    cookies2.json 파일에서 쿠키 문자열을 로드합니다.

    Args:
        cookies_path (Path): 쿠키 파일 경로

    Returns:
        str: 쿠키 문자열 (예: "key1=value1; key2=value2")
    """
    try:
        with open(cookies_path, 'r', encoding='utf-8') as f:
            cookies_data = json.load(f)

        # JSON 형식에 따라 처리
        if isinstance(cookies_data, list):
            # 리스트 형식: [{"name": "key", "value": "val"}, ...]
            cookie_items = [f"{item['name']}={item['value']}" for item in cookies_data]
            return "; ".join(cookie_items)
        elif isinstance(cookies_data, dict):
            # 딕셔너리 형식: {"key": "value", ...}
            return "; ".join([f"{k}={v}" for k, v in cookies_data.items()])
        else:
            return ""
    except Exception as e:
        print(f"[ERROR] 쿠키 파일 로드 실패: {e}")
        return ""


def call_extract_productdata(
    nvmid: str,
    service_url: str = "https://hello-world-fo9c.onrender.com",
    scripts_dir: str = r"D:\scorebill_V2\scripts"
):
    """
    Render 서비스의 /extract_productdata 엔드포인트를 호출합니다.

    Args:
        nvmid (str): 상품 NVM ID
        service_url (str): Render 서비스 URL
        scripts_dir (str): 스크립트 디렉토리 경로 (쿠키 파일 위치)
    """
    print(f"[START] Render 서비스 호출 중: {service_url}/extract_productdata")
    print(f"[INFO] nvmid: {nvmid}")
    print(f"[INFO] 스크립트 디렉토리: {scripts_dir}\n")

    # 경로 설정
    scripts_path = Path(scripts_dir)
    cookies_path = scripts_path / "cookies2.json"

    # 쿠키 로드
    print("[INFO] 쿠키 로드 중...")
    cookies = load_cookies_from_file(cookies_path)
    if not cookies:
        print(f"[ERROR] 쿠키를 로드할 수 없습니다: {cookies_path}")
        return
    print(f"[OK] 쿠키 로드 완료 ({len(cookies)} bytes)\n")

    # API 요청
    print("[INFO] POST 요청 전송 중...")
    try:
        response = requests.post(
            f"{service_url}/extract_productdata",
            json={
                "nvmid": nvmid,
                "cookies": cookies
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        # 응답 처리
        print(f"\n[INFO] 상태 코드: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("[OK] 데이터 추출 성공!")
                print(f"[INFO] nvmid: {result.get('nvmid')}")
                print(f"[INFO] 추출된 상품 수: {len(result.get('products', []))}")

                # 첫 번째 상품 정보 출력
                products = result.get("products", [])
                if products:
                    product = products[0]
                    print(f"\n[상품 정보]")
                    print(f"  - 상품명: {product.get('productName', 'N/A')}")
                    print(f"  - 브랜드: {product.get('brandName', 'N/A')}")
                    print(f"  - 카테고리: {product.get('category1Name', 'N/A')}")
                    print(f"  - 등록일: {product.get('openDateFormatted', 'N/A')}")
                    print(f"  - 가격: {product.get('price', 'N/A')}")
            else:
                print(f"[ERROR] 추출 실패: {result.get('error', '알 수 없는 오류')}")
        else:
            try:
                error_data = response.json()
                print(f"[ERROR] API 오류: {error_data.get('error', '알 수 없는 오류')}")
            except:
                print(f"[ERROR] HTTP 오류: {response.text}")

    except requests.exceptions.Timeout:
        print("[ERROR] 요청 시간 초과 (30초)")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 요청 실패: {e}")
    except Exception as e:
        print(f"[ERROR] 예기치 않은 오류: {e}")

    print("\n" + "=" * 50)
    print("[DONE] 요청 완료!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python 호출_extract_productdata.py <nvmid> [service_url] [scripts_dir]")
        print("예시: python 호출_extract_productdata.py 84747291048")
        print("예시: python 호출_extract_productdata.py 84747291048 https://hello-world-fo9c.onrender.com")
        sys.exit(1)

    nvmid = sys.argv[1]
    service_url = sys.argv[2] if len(sys.argv) > 2 else "https://hello-world-fo9c.onrender.com"
    scripts_dir = sys.argv[3] if len(sys.argv) > 3 else r"D:\scorebill_V2\scripts"

    call_extract_productdata(nvmid, service_url, scripts_dir)
