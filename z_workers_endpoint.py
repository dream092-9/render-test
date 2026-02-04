#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare Workers 엔드포인트 호출 스크립트
nvmid 목록을 파일에서 읽어서 병렬로 상품 데이터 추출
사용법: python z_workers_endpoint.py [workers_url] [nvmids_path] [scripts_dir] [output_dir]
"""
import sys
import json
import requests
from pathlib import Path
from datetime import datetime

# 윈도우 환경에서 UTF-8 출력이 가능하도록 설정
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_nvmids_from_file(nvmids_path: Path) -> list:
    """
    nvmids.txt 파일에서 nvmid 목록을 로드합니다.

    Args:
        nvmids_path (Path): nvmids 파일 경로

    Returns:
        list: nvmid 리스트
    """
    try:
        with open(nvmids_path, 'r', encoding='utf-8') as f:
            nvmids = [line.strip() for line in f if line.strip()]
        return nvmids
    except Exception as e:
        print(f"[ERROR] nvmids 파일 로드 실패: {e}")
        return []


def load_cookies_from_file(cookies_path: Path) -> str:
    """
    cookies2.json 파일에서 쿠키 문자열을 로드합니다.

    Args:
        cookies_path (Path): 쿠키 파일 경로

    Returns:
        str: 쿠키 문자열
    """
    try:
        with open(cookies_path, 'r', encoding='utf-8') as f:
            cookies_data = json.load(f)

        # cookies2.json 구조: cookies.string_format 또는 cookies.dict_format
        cookies_info = cookies_data.get('cookies', {})
        if isinstance(cookies_info, dict):
            # string_format 우선
            cookie_string = cookies_info.get('string_format', '')
            if cookie_string:
                return cookie_string
            # dict_format 대안
            dict_format = cookies_info.get('dict_format', {})
            if dict_format:
                return "; ".join([f"{k}={v}" for k, v in dict_format.items()])

        return ""
    except Exception as e:
        print(f"[ERROR] 쿠키 파일 로드 실패: {e}")
        return ""


def load_headers_from_file(cookies_path: Path) -> dict:
    """
    cookies2.json 파일에서 헤더 딕셔너리를 로드합니다.

    Args:
        cookies_path (Path): 쿠키 파일 경로

    Returns:
        dict: 헤더 딕셔너리
    """
    try:
        with open(cookies_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        headers = data.get('headers', {})
        if isinstance(headers, dict) and headers:
            return headers
        else:
            return {}
    except Exception as e:
        print(f"[ERROR] 헤더 로드 실패: {e}")
        return {}


def call_workers_endpoint(
    workers_url: str,
    nvmids_path: str = r"D:\render_test\z_nvmids.txt",
    scripts_dir: str = r"D:\scorebill_V2\scripts",
    output_dir: str = r"D:\render_test",
    concurrency: int = 50
):
    """
    Cloudflare Workers 엔드포인트를 호출합니다.

    Args:
        workers_url (str): Workers URL (예: https://your-worker.your-subdomain.workers.dev)
        nvmids_path (str): nvmids 파일 경로
        scripts_dir (str): 스크립트 디렉토리 경로 (쿠키 파일 위치)
        output_dir (str): 결과 JSON 저장 경로
        concurrency (int): 동시 처리 수
    """
    print(f"[START] Cloudflare Workers 호출 중: {workers_url}")
    print(f"[INFO] nvmids 파일: {nvmids_path}")
    print(f"[INFO] 스크립트 디렉토리: {scripts_dir}")
    print(f"[INFO] 동시 처리 수: {concurrency}\n")

    # nvmids 로드
    print("[INFO] nvmids 로드 중...")
    loaded_nvmids = load_nvmids_from_file(Path(nvmids_path))
    if not loaded_nvmids:
        print(f"[ERROR] nvmids를 로드할 수 없습니다: {nvmids_path}")
        return

    print(f"[OK] nvmids 로드 완료 ({len(loaded_nvmids)}개)\n")

    # 쿠키 로드
    scripts_path = Path(scripts_dir)
    cookies_path = scripts_path / "cookies2.json"

    print("[INFO] 쿠키 로드 중...")
    cookies = load_cookies_from_file(cookies_path)
    if not cookies:
        print(f"[ERROR] 쿠키를 로드할 수 없습니다: {cookies_path}")
        return
    print(f"[OK] 쿠키 로드 완료 ({len(cookies)} bytes)\n")

    # 헤더 로드
    print("[INFO] 헤더 로드 중...")
    headers = load_headers_from_file(cookies_path)
    if not headers:
        print("[WARN] 헤더가 비어있습니다.")
    else:
        print(f"[OK] 헤더 로드 완료 ({len(headers)} items)\n")

    # Workers API 요청
    print(f"[INFO] POST 요청 전송 중... (nvmids: {len(loaded_nvmids)}개)")
    try:
        start_time = datetime.now()

        response = requests.post(
            f"{workers_url}/extract_productdata_batch",
            json={
                "nvmids": loaded_nvmids,
                "cookies": cookies,
                "headers": headers,
                "concurrency": concurrency
            },
            headers={"Content-Type": "application/json"},
            timeout=300  # 5분 타임아웃 (Workers는 더 빠를 수 있음)
        )

        end_time = datetime.now()
        elapsed = (end_time - start_time).total_seconds()

        # 응답 처리
        print(f"\n[INFO] 상태 코드: {response.status_code}")
        print(f"[INFO] 소요 시간: {elapsed:.2f}초")

        if response.status_code == 200:
            result = response.json()

            if result.get("success"):
                print("[OK] 데이터 추출 성공!")
                print(f"[INFO] 전체: {result.get('total')}개")
                print(f"[INFO] 성공: {result.get('success_count')}개")
                print(f"[INFO] 실패: {result.get('fail_count')}개")

                # 결과 저장
                results = result.get("results", [])
                success_results = [r for r in results if r and isinstance(r, dict) and r.get("success")]
                fail_results = []
                for idx, r in enumerate(results):
                    if r is None or (r and isinstance(r, dict) and not r.get("success")):
                        fail_results.append((idx, r, loaded_nvmids[idx] if idx < len(loaded_nvmids) else "N/A"))

                # 성공/실패 카운트 출력
                actual_total = len(loaded_nvmids)
                actual_success_count = len(success_results)
                actual_fail_count = len(fail_results)
                duplicates = result.get('duplicates_removed', 0)

                print(f"\n{'='*50}")
                print(f"[결과 요약]")
                print(f"  총 요청: {actual_total}개")
                print(f"  성공: {actual_success_count}개")
                print(f"  실패: {actual_fail_count}개")
                if duplicates > 0:
                    print(f"  ℹ️  중복 제거: {duplicates}개")
                if actual_total > 0:
                    print(f"  성공률: {actual_success_count / actual_total * 100:.1f}%")
                else:
                    print(f"  성공률: N/A (total이 0)")
                print(f"{'='*50}\n")

                # 성공한 상품 정보 출력 (처음 5개)
                if success_results:
                    print(f"[성공한 상품 예시 (처음 5개)]")
                    for i, r in enumerate(success_results[:5]):
                        nvmid = r.get('nvmid', 'N/A') if r else 'N/A'
                        product = r.get("product") if r else None
                        if product:
                            print(f"  {i+1}. NvMid: {nvmid}")
                            print(f"     상품명: {product.get('productTitle', 'N/A')}")
                            print(f"     몰 이름: {product.get('mallName', 'N/A')}")
                            print()
                        else:
                            print(f"  {i+1}. NvMid: {nvmid}")
                            print(f"     상품 데이터 없음")
                            print()

                # 실패한 경우 에러 출력
                if fail_results:
                    print(f"[실패한 항목 (처음 5개)]")
                    for i, (idx, r, nvmid) in enumerate(fail_results[:5]):
                        if r is None:
                            print(f"  {i+1}. NvMid: {nvmid} (인덱스: {idx})")
                            print(f"     에러: 데이터 없음 (null)")
                            print()
                        elif isinstance(r, dict):
                            error = r.get('error', 'Unknown')
                            print(f"  {i+1}. NvMid: {nvmid} (인덱스: {idx})")
                            print(f"     에러: {error}")
                            print()
                        else:
                            print(f"  {i+1}. NvMid: {nvmid} (인덱스: {idx})")
                            print(f"     알 수 없는 형태: {type(r)}")
                            print()

                # 전체 결과 JSON 저장 (zz.json)
                output_filename = Path(output_dir) / "zz_workers.json"

                with open(output_filename, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

                print(f"[OK] 결과가 저장되었습니다: {output_filename}")
                print(f"\n[통계]")
                print(f"  - 총 상품 수: {len(success_results)}")
                unique_count = result.get('original_unique_nvmids', len(loaded_nvmids))
                if unique_count > 0:
                    print(f"  - 평균 응답 시간: {elapsed / unique_count:.2f}초/개")
            else:
                print(f"[ERROR] 추출 실패: {result.get('error', '알 수 없는 오류')}")
        else:
            try:
                error_data = response.json()
                print(f"[ERROR] API 오류: {error_data.get('error', '알 수 없는 오류')}")
            except:
                print(f"[ERROR] HTTP 오류: {response.text}")

    except requests.exceptions.Timeout:
        print("[ERROR] 요청 시간 초과 (300초)")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] 요청 실패: {e}")
    except Exception as e:
        print(f"[ERROR] 예기치 않은 오류: {e}")

    print("\n" + "=" * 50)
    print("[DONE] 요청 완료!")


if __name__ == "__main__":
    # 인자 파싱
    # 기본 Workers URL
    DEFAULT_WORKERS_URL = "https://naver-product-data.dreamad0929.workers.dev"

    # 인자가 없으면 도움말과 기본값 사용 안내
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        print("사용법: python z_workers_endpoint.py [workers_url] [nvmids_path] [scripts_dir] [output_dir] [concurrency]")
        print("\n인자:")
        print("  workers_url  : Workers URL (기본값: 배포된 URL)")
        print("  nvmids_path  : nvmids 파일 경로 (기본값: D:\\render_test\\z_nvmids.txt)")
        print("  scripts_dir  : 스크립트 디렉토리 (기본값: D:\\scorebill_V2\\scripts)")
        print("  output_dir   : 출력 디렉토리 (기본값: D:\\render_test)")
        print("  concurrency  : 동시 처리 수 (기본값: 50)")
        print("\n예시:")
        print("  python z_workers_endpoint.py")
        print(f"  → 기본 Workers URL 사용: {DEFAULT_WORKERS_URL}")
        print("\n  python z_workers_endpoint.py https://custom-worker.workers.dev")
        print("  → 커스텀 Workers URL 사용")
        print("\n  python z_workers_endpoint.py https://custom-worker.workers.dev D:\\nvmids.txt D:\\scripts D:\\output 20")
        print("  → 모든 인자 커스텀")
        sys.exit(0)

    # 인자 파싱 (기본값 적용)
    workers_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WORKERS_URL
    nvmids_path = sys.argv[2] if len(sys.argv) > 2 else r"D:\render_test\z_nvmids.txt"
    scripts_dir = sys.argv[3] if len(sys.argv) > 3 else r"D:\scorebill_V2\scripts"
    output_dir = sys.argv[4] if len(sys.argv) > 4 else r"D:\render_test"
    concurrency = int(sys.argv[5]) if len(sys.argv) > 5 else 50

    call_workers_endpoint(workers_url, nvmids_path, scripts_dir, output_dir, concurrency)
