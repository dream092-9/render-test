#!/usr/bin/env python3
"""
Render에 배포되는 Python 엔드포인트: GET / → "hello, world"
로컬 실행: python hello.py [--serve]
배포 후 호출: RENDER_SERVICE_ID, RENDER_SERVICE_URL 설정 후 python hello.py --deploy-and-call
"""
import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import aiohttp
import requests

from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/")
def index():
    return "hello, world"


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/extract_productdata", methods=["POST"])
def extract_productdata():
    """
    nvmid, cookies, headers를 받아서 상품 정보를 추출하는 엔드포인트
    Request Body: { "nvmid": "string", "cookies": "string", "headers": "dict" }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON body가 필요합니다."}), 400

        nvmid = data.get("nvmid")
        cookies = data.get("cookies")
        client_headers = data.get("headers", {})

        if not nvmid:
            return jsonify({"success": False, "error": "nvmid가 필요합니다."}), 400
        if not cookies:
            return jsonify({"success": False, "error": "cookies가 필요합니다."}), 400

        # 스마트스토어 인기상품 API 호출 (z_extract_productdata.py와 동일)
        url = "https://sell.smartstore.naver.com/api/product/shared/product-search-popular"
        params = {
            "_action": "productSearchPopularByCategory",
            "nvMid": nvmid
        }

        # 쿠키 문자열을 딕셔너리로 변환
        cookie_dict = {}
        if isinstance(cookies, str):
            for item in cookies.split(";"):
                if "=" in item:
                    key, value = item.strip().split("=", 1)
                    cookie_dict[key] = value

        # 헤더 설정 (클라이언트에서 받은 헤더 사용, 없으면 기본 헤더)
        headers = client_headers if isinstance(client_headers, dict) and client_headers else {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://sell.smartstore.naver.com/",
        }

        # API 요청
        response = requests.get(url, headers=headers, cookies=cookie_dict, params=params, timeout=10)

        if response.status_code != 200:
            return jsonify({
                "success": False,
                "error": f"API 요청 실패: 상태 코드 {response.status_code}"
            }), 500

        result = response.json()

        # 결과 파싱
        products = []
        if result and isinstance(result, dict) and "result" in result:
            product_data = result["result"]
            if isinstance(product_data, dict):
                # 날짜 포맷팅
                od = product_data.get("openDate")
                if isinstance(od, str) and "T" in od:
                    try:
                        product_data["openDateFormatted"] = od.replace("T", " ").split("+")[0]
                    except Exception:
                        product_data["openDateFormatted"] = od
                else:
                    product_data["openDateFormatted"] = od if od else ""

                products = [product_data]

        if not products:
            return jsonify({
                "success": False,
                "error": "결과를 찾을 수 없습니다."
            }), 404

        return jsonify({
            "success": True,
            "products": products,
            "nvmid": nvmid,
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"서버 오류: {str(e)}"
        }), 500


async def fetch_single_product_async(session: aiohttp.ClientSession, nvmid: str, cookie_string: str, headers: dict) -> dict:
    """
    단일 상품 정보를 가져오는 비동기 함수

    Args:
        session (aiohttp.ClientSession): aiohttp 세션
        nvmid (str): 상품 NVM ID
        cookie_string (str): 쿠키 문자열 (그대로 헤더에 사용)
        headers (dict): 헤더 딕셔너리

    Returns:
        dict: {nvmid: str, success: bool, product: dict or None, error: str or None}
    """
    try:
        url = "https://sell.smartstore.naver.com/api/product/shared/product-search-popular"
        params = {
            "_action": "productSearchPopularByCategory",
            "nvMid": nvmid
        }

        # 쿠키를 Cookie 헤더에 직접 추가 (aiohttp는 이 방식을 선호)
        request_headers = dict(headers)  # 안전하게 딕셔너리 복사
        request_headers["Cookie"] = cookie_string

        # API 요청 (비동기)
        async with session.get(url, headers=request_headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status != 200:
                return {
                    "nvmid": nvmid,
                    "success": False,
                    "product": None,
                    "error": f"API 요청 실패: 상태 코드 {response.status}"
                }

            result = await response.json()

            # 결과 파싱
            if result and isinstance(result, dict) and "result" in result:
                product_data = result["result"]
                if isinstance(product_data, dict):
                    # 날짜 포맷팅
                    od = product_data.get("openDate")
                    if isinstance(od, str) and "T" in od:
                        try:
                            product_data["openDateFormatted"] = od.replace("T", " ").split("+")[0]
                        except Exception:
                            product_data["openDateFormatted"] = od
                    else:
                        product_data["openDateFormatted"] = od if od else ""

                    return {
                        "nvmid": nvmid,
                        "success": True,
                        "product": product_data,
                        "error": None
                    }

            return {
                "nvmid": nvmid,
                "success": False,
                "product": None,
                "error": "결과를 찾을 수 없습니다."
            }

    except Exception as e:
        return {
            "nvmid": nvmid,
            "success": False,
            "product": None,
            "error": f"서버 오류: {str(e)}"
        }


def fetch_single_product_with_dict(nvmid: str, cookie_dict: dict, headers: dict) -> dict:
    """
    단일 상품 정보를 가져오는 함수 (병렬 처리용 - 쿠키 미리 변환)

    Args:
        nvmid (str): 상품 NVM ID
        cookie_dict (dict): 변환된 쿠키 딕셔너리
        headers (dict): 헤더 딕셔너리

    Returns:
        dict: {nvmid: str, success: bool, product: dict or None, error: str or None}
    """
    try:
        url = "https://sell.smartstore.naver.com/api/product/shared/product-search-popular"
        params = {
            "_action": "productSearchPopularByCategory",
            "nvMid": nvmid
        }

        # API 요청
        response = requests.get(url, headers=headers, cookies=cookie_dict, params=params, timeout=10)

        if response.status_code != 200:
            return {
                "nvmid": nvmid,
                "success": False,
                "product": None,
                "error": f"API 요청 실패: 상태 코드 {response.status_code}"
            }

        result = response.json()

        # 결과 파싱
        if result and isinstance(result, dict) and "result" in result:
            product_data = result["result"]
            if isinstance(product_data, dict):
                # 날짜 포맷팅
                od = product_data.get("openDate")
                if isinstance(od, str) and "T" in od:
                    try:
                        product_data["openDateFormatted"] = od.replace("T", " ").split("+")[0]
                    except Exception:
                        product_data["openDateFormatted"] = od
                else:
                    product_data["openDateFormatted"] = od if od else ""

                return {
                    "nvmid": nvmid,
                    "success": True,
                    "product": product_data,
                    "error": None
                }

        return {
            "nvmid": nvmid,
            "success": False,
            "product": None,
            "error": "결과를 찾을 수 없습니다."
        }

    except Exception as e:
        return {
            "nvmid": nvmid,
            "success": False,
            "product": None,
            "error": f"서버 오류: {str(e)}"
        }


def fetch_single_product(nvmid: str, cookies: str, headers: dict) -> dict:
    """
    단일 상품 정보를 가져오는 함수 (병렬 처리용)

    Args:
        nvmid (str): 상품 NVM ID
        cookies (str): 쿠키 문자열
        headers (dict): 헤더 딕셔너리

    Returns:
        dict: {nvmid: str, success: bool, product: dict or None, error: str or None}
    """
    try:
        url = "https://sell.smartstore.naver.com/api/product/shared/product-search-popular"
        params = {
            "_action": "productSearchPopularByCategory",
            "nvMid": nvmid
        }

        # 쿠키 문자열을 딕셔너리로 변환
        cookie_dict = {}
        if isinstance(cookies, str):
            for item in cookies.split(";"):
                if "=" in item:
                    key, value = item.strip().split("=", 1)
                    cookie_dict[key] = value

        # API 요청
        response = requests.get(url, headers=headers, cookies=cookie_dict, params=params, timeout=10)

        if response.status_code != 200:
            return {
                "nvmid": nvmid,
                "success": False,
                "product": None,
                "error": f"API 요청 실패: 상태 코드 {response.status_code}"
            }

        result = response.json()

        # 결과 파싱
        if result and isinstance(result, dict) and "result" in result:
            product_data = result["result"]
            if isinstance(product_data, dict):
                # 날짜 포맷팅
                od = product_data.get("openDate")
                if isinstance(od, str) and "T" in od:
                    try:
                        product_data["openDateFormatted"] = od.replace("T", " ").split("+")[0]
                    except Exception:
                        product_data["openDateFormatted"] = od
                else:
                    product_data["openDateFormatted"] = od if od else ""

                return {
                    "nvmid": nvmid,
                    "success": True,
                    "product": product_data,
                    "error": None
                }

        return {
            "nvmid": nvmid,
            "success": False,
            "product": None,
            "error": "결과를 찾을 수 없습니다."
        }

    except Exception as e:
        return {
            "nvmid": nvmid,
            "success": False,
            "product": None,
            "error": f"서버 오류: {str(e)}"
        }


@app.route("/extract_productdata_multi", methods=["POST"])
def extract_productdata_multi():
    """
    여러 nvmid를 받아서 완전 병렬로 상품 정보를 추출하는 엔드포인트
    Request Body: { "nvmids": ["str", ...], "cookies": "string", "headers": "dict" }

    aiohttp를 사용하여 대규모 병렬 처리 지원 (최대 500개 동시 처리 가능)
    Flask[async] 없이 동기 route에서 내부적으로 asyncio 실행
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "JSON body가 필요합니다."}), 400

        nvmids = data.get("nvmids")
        cookies = data.get("cookies")
        client_headers = data.get("headers", {})

        if not nvmids:
            return jsonify({"success": False, "error": "nvmids가 필요합니다."}), 400
        if not isinstance(nvmids, list):
            return jsonify({"success": False, "error": "nvmids는 리스트여야 합니다."}), 400
        if not cookies:
            return jsonify({"success": False, "error": "cookies가 필요합니다."}), 400

        # 헤더 설정
        headers = client_headers if isinstance(client_headers, dict) and client_headers else {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://sell.smartstore.naver.com/",
        }

        # 상세 없는 "서버 오류:" 만 있는지 여부 (이 경우만 재시도 대상)
        def is_retriable_error(error_str):
            if not error_str or not isinstance(error_str, str):
                return False
            s = error_str.strip()
            if not s.startswith("서버 오류:"):
                return False
            detail = s[len("서버 오류:"):].strip()
            return len(detail) == 0

        # asyncio를 사용하여 완전 비동기 병렬 처리 실행
        async def run_parallel(nvmid_list):
            # Render 서버 환경에 맞춰 연결 제한 동적 조정
            import os
            is_render = os.environ.get("RENDER", "") != "" or os.environ.get("PORT") != "5678"

            # Render 서버: 낮은 CPU 코어 수에 맞춰 병렬 처리 수 최적화
            # 로컬: 높은 병렬 처리 유지
            max_concurrent = 100 if is_render else 500
            max_per_host = 50 if is_render else 250

            connector = aiohttp.TCPConnector(
                limit=max_concurrent,
                limit_per_host=max_per_host,
                ttl_dns_cache=600,  # DNS 캐시 시간 증가
                enable_cleanup_closed=True,  # 닫힌 연결 정리 활성화
                force_close=False,  # 연결 재사용
                keepalive_timeout=30,  # keep-alive 타임아웃
            )
            timeout = aiohttp.ClientTimeout(
                total=30,
                connect=10,  # 연결 타임아웃
                sock_read=10  # 소켓 읽기 타임아웃
            )
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                tasks = [fetch_single_product_async(session, nvmid, cookies, headers) for nvmid in nvmid_list]
                return list(await asyncio.gather(*tasks))

        # 1차 요청
        results = asyncio.run(run_parallel(nvmids))
        nvmid_to_index = {nvmid: i for i, nvmid in enumerate(nvmids)}

        # 상세 없는 "서버 오류:" 만 있는 실패만 모아서 최대 3번 재시도
        retry_nvmids = [r["nvmid"] for r in results if not r["success"] and is_retriable_error(r.get("error") or "")]
        max_retries = 3
        retry_count = 0

        while retry_nvmids and retry_count < max_retries:
            retry_count += 1
            retry_results = asyncio.run(run_parallel(retry_nvmids))
            for retry_result in retry_results:
                idx = nvmid_to_index[retry_result["nvmid"]]
                results[idx] = retry_result
            retry_nvmids = [r["nvmid"] for r in retry_results if not r["success"] and is_retriable_error(r.get("error") or "")]

        success_count = sum(1 for r in results if r["success"])
        fail_count = len(results) - success_count

        return jsonify({
            "success": True,
            "total": len(nvmids),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": results
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"서버 오류: {str(e)}"
        }), 500


def get_service_url_from_cli(service_id: str) -> str | None:
    """Render CLI로 서비스 목록을 조회해 service_id에 해당하는 URL 반환."""
    try:
        out = subprocess.run(
            ["render", "services", "-o", "json", "--confirm"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "CI": "true"},
        )
        if out.returncode != 0:
            return None
        data = json.loads(out.stdout)
        # CLI 응답: 리스트 또는 { services: [...] } 등 구조에 맞게 탐색
        services = data if isinstance(data, list) else data.get("services", data)
        if not isinstance(services, list):
            services = [services]
        for svc in services:
            sid = svc.get("id") or svc.get("serviceId")
            if sid == service_id:
                # serviceDetails 등에 URL이 있을 수 있음
                url = (
                    svc.get("serviceDetails", {}).get("url")
                    or svc.get("url")
                    or svc.get("service", {}).get("serviceDetails", {}).get("url")
                )
                if url:
                    return url
                name = svc.get("name") or svc.get("service", {}).get("name")
                if name:
                    slug = name.lower().replace(" ", "-")
                    return f"https://{slug}.onrender.com"
        return None
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


def main_serve():
    port = int(os.environ.get("PORT", 5678))  # 로컬 테스트용 5678포트
    app.run(host="0.0.0.0", port=port)


def main_deploy_and_call():
    service_id = os.environ.get("RENDER_SERVICE_ID")
    service_url = os.environ.get("RENDER_SERVICE_URL")

    if not service_id and not service_url:
        print(
            "RENDER_SERVICE_ID 또는 RENDER_SERVICE_URL 환경 변수를 설정하세요.",
            file=sys.stderr,
        )
        print(
            "예: RENDER_SERVICE_ID=srv-xxx python hello.py --deploy-and-call",
            file=sys.stderr,
        )
        sys.exit(1)

    if service_url:
        url = service_url.rstrip("/")
    else:
        print("RENDER_SERVICE_URL이 없어 CLI로 서비스 URL 조회 중...")
        url = get_service_url_from_cli(service_id)
        if not url:
            print(
                "서비스 URL을 찾을 수 없습니다. RENDER_SERVICE_URL을 직접 설정하세요.",
                file=sys.stderr,
            )
            sys.exit(1)
        url = url.rstrip("/")

    if service_id:
        print("Render 배포 트리거 중...")
        try:
            subprocess.run(
                [
                    "render", "deploys", "create", service_id,
                    "--wait", "-o", "json", "--confirm",
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=600,
                env={**os.environ, "CI": "true"},
            )
        except subprocess.CalledProcessError as e:
            print(f"배포 실패: {e}", file=sys.stderr)
            sys.exit(1)
        except FileNotFoundError:
            print("render CLI를 찾을 수 없습니다. 설치 후 PATH에 추가하세요.", file=sys.stderr)
            sys.exit(1)
        print("배포 완료.")

    # 호출
    try:
        import urllib.request
        with urllib.request.urlopen(f"{url}/", timeout=30) as resp:
            body = resp.read().decode()
            print("응답:", body)
            if "hello" in body.lower() and "world" in body.lower():
                print("OK: hello, world 수신")
            else:
                print("경고: 예상과 다른 응답입니다.", file=sys.stderr)
    except Exception as e:
        print(f"엔드포인트 호출 실패: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hello World 엔드포인트 (로컬 서버 또는 배포 후 호출)")
    parser.add_argument(
        "--serve",
        action="store_true",
        help="로컬에서 Flask 서버 실행 (기본: 서버 실행)",
    )
    parser.add_argument(
        "--deploy-and-call",
        action="store_true",
        help="Render CLI로 배포 트리거 후 엔드포인트 호출",
    )
    args = parser.parse_args()

    if args.deploy_and_call:
        main_deploy_and_call()
    else:
        main_serve()
