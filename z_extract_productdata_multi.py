#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
z_nvmids.txt의 여러 nvmid에 대해 인기상품(상품 기본 정보)을 동시에 조회.
- 쿠키/헤더는 한 번만 로드 (D:\\scorebill_V2\\scripts\\cookies2.json)
- 각 nvmid 요청은 완전 병렬 처리
- 마지막에 총 소요 시간 출력
"""

import json
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple

import requests

# 쿠키/설정 파일 경로 (절대경로)
SCOREBILL_SCRIPTS = Path(r"D:\scorebill_V2\scripts")
CONFIG_FILE = SCOREBILL_SCRIPTS / "cookies2.json"
API_URL = "https://sell.smartstore.naver.com/api/product/shared/product-search-popular"


def load_config_once() -> Optional[Dict[str, Any]]:
    """쿠키/헤더 설정을 한 번만 로드."""
    try:
        if not CONFIG_FILE.exists():
            print(f"설정 파일을 찾을 수 없습니다: {CONFIG_FILE}")
            return None
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        if not config:
            print("설정 파일이 비어 있습니다.")
            return None
        return config
    except Exception as e:
        print(f"설정 로드 실패: {e}")
        return None


def _session_from_config(config: Dict[str, Any], silent: bool = True) -> Optional[requests.Session]:
    """config로 새 Session 생성 (스레드당 1개 사용)."""
    session = requests.Session()
    headers = config.get("headers", {})
    if headers:
        session.headers.update(headers)
    cookies_data = config.get("cookies", {})
    actual_cookies = cookies_data.get("dict_format", {})
    cookie_string = cookies_data.get("string_format", "")
    if actual_cookies:
        session.cookies.update(actual_cookies)
    elif cookie_string:
        for part in cookie_string.split("; "):
            if "=" in part:
                k, v = part.split("=", 1)
                session.cookies.set(k.strip(), v.strip())
    else:
        return None
    return session


def fetch_one_productdata(nvmid: str, config: Dict[str, Any], silent: bool = True) -> Dict[str, Any]:
    """
    단일 nvmid에 대해 인기상품 API 호출.
    config는 이미 로드된 cookies2.json 내용 (쿠키/헤더 한 번만 로드된 것).
    """
    nvmid = str(nvmid).strip()
    if not nvmid:
        return {"success": False, "error": "nvmid 없음", "nvmid": nvmid}

    session = _session_from_config(config, silent=silent)
    if not session:
        return {"success": False, "error": "세션 생성 실패(쿠키 없음)", "nvmid": nvmid}

    params = {"_action": "productSearchPopularByCategory", "nvMid": nvmid}
    try:
        response = session.get(API_URL, params=params, timeout=30)
    except Exception as e:
        return {"success": False, "error": str(e), "nvmid": nvmid}

    if response.status_code != 200:
        return {
            "success": False,
            "error": f"HTTP {response.status_code}",
            "nvmid": nvmid,
        }

    try:
        json_data = response.json()
    except json.JSONDecodeError:
        return {"success": False, "error": "JSON 파싱 실패", "nvmid": nvmid}

    if not isinstance(json_data, dict) or "result" not in json_data:
        return {"success": False, "error": "결과 형식 오류", "nvmid": nvmid}

    result_inner = json_data.get("result")
    if not isinstance(result_inner, dict):
        return {"success": False, "error": "결과 없음", "nvmid": nvmid}

    product = dict(result_inner)
    od = product.get("openDate")
    if isinstance(od, str) and "T" in od:
        try:
            product["openDateFormatted"] = od.replace("T", " ").split("+")[0]
        except Exception:
            product["openDateFormatted"] = od
    else:
        product["openDateFormatted"] = od if od else ""
    products = [product]

    return {
        "success": True,
        "products": products,
        "nvmid": nvmid,
    }


def load_nvmids(filepath: Path) -> List[str]:
    """파일에서 nvmid 목록 로드 (한 줄 하나, 빈 줄/공백 제거)."""
    if not filepath.exists():
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines


def run_multi(nvmid_file: Optional[Path] = None, silent: bool = False) -> Tuple[List[Dict[str, Any]], float]:
    """
    여러 nvmid에 대해 쿠키/헤더 1회 로드 후 완전 병렬 조회.
    반환: (각 nvmid별 결과 리스트, 총 소요 시간 초).
    """
    script_dir = Path(__file__).resolve().parent
    path = nvmid_file or script_dir / "z_nvmids.txt"
    nvmids = load_nvmids(path)
    if not nvmids:
        print(f"nvmid 없음 또는 파일 없음: {path}")
        return [], 0.0

    config = load_config_once()
    if not config:
        return [], 0.0

    if not silent:
        print(f"쿠키/헤더 1회 로드 완료. nvmid {len(nvmids)}개 병렬 조회 시작.")

    results: List[Dict[str, Any]] = []
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=len(nvmids)) as executor:
        futures = {
            executor.submit(fetch_one_productdata, nvmid, config, silent=True): nvmid
            for nvmid in nvmids
        }
        for future in as_completed(futures):
            nvmid = futures[future]
            try:
                out = future.result()
                results.append(out)
                if not silent:
                    status = "OK" if out.get("success") else out.get("error", "?")
                    print(f"  [{nvmid}] {status}")
            except Exception as e:
                results.append({"success": False, "error": str(e), "nvmid": nvmid})
                if not silent:
                    print(f"  [{nvmid}] 예외: {e}")

    elapsed = time.perf_counter() - start
    return results, elapsed


def save_results_to_json(results: List[Dict[str, Any]], elapsed: float, filepath: Optional[Path] = None) -> Path:
    """멀티 상품 정보를 JSON 파일로 저장. 반환: 저장한 파일 경로."""
    if filepath is None:
        filepath = Path(__file__).resolve().parent / "z.json"
    data = {"results": results, "count": len(results), "elapsed_seconds": round(elapsed, 2)}
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


if __name__ == "__main__":
    silent = "--silent" in sys.argv
    results, elapsed = run_multi(silent=silent)
    out_path = save_results_to_json(results, elapsed)
    success_count = sum(1 for r in results if r.get("success"))
    print(f"완료: 성공 {success_count}/{len(results)}건")
    print(f"저장: {out_path}")
    print(f"총 소요 시간: {elapsed:.2f}초")
