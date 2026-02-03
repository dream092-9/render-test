#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
상품 기본 정보(인기상품 API) 조회 전용 스크립트.
cookies2.json, 헤더 등 D:\\scorebill_V2\\scripts 기준 절대경로로 참조.
"""

import sys
from pathlib import Path
from typing import Dict, Any

# 기존 프로젝트(scorebill_V2) scripts 경로를 절대경로로 참조
SCOREBILL_SCRIPTS = Path(r"D:\scorebill_V2\scripts")
if str(SCOREBILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCOREBILL_SCRIPTS))
from extract_popular_by_nvmid import SmartStoreNvMidExtractor


def fetch_productdata(nvmid: str, silent: bool = False) -> Dict[str, Any]:
    """
    nvmid로 인기상품(상품 기본 정보)만 조회.
    입력: nvmid (str)
    출력: success, products, nvmid 또는 success=False, error
    """
    nvmid = str(nvmid).strip()
    if not nvmid:
        return {'success': False, 'error': '단일 Mid를 입력해주세요.'}

    extractor = SmartStoreNvMidExtractor(nv_mid=nvmid)
    if not extractor.load_browser_config():
        return {'success': False, 'error': '쿠키 설정 파일(cookies2.json)을 찾을 수 없거나 로드할 수 없습니다.'}
    result = extractor.fetch_popular_by_category()
    if result is None:
        return {'success': False, 'error': '데이터를 추출할 수 없습니다. 쿠키가 만료되었을 수 있습니다.'}

    products = None
    if result and isinstance(result, dict) and 'result' in result and isinstance(result['result'], dict):
        product = dict(result['result'])
        od = product.get('openDate')
        if isinstance(od, str) and 'T' in od:
            try:
                product['openDateFormatted'] = od.replace('T', ' ').split('+')[0]
            except Exception:
                product['openDateFormatted'] = od
        else:
            product['openDateFormatted'] = od if od else ''
        products = [product]
    if not products or len(products) == 0:
        return {'success': False, 'error': '결과를 찾을 수 없습니다.'}

    return {
        'success': True,
        'products': products,
        'nvmid': nvmid,
    }


if __name__ == "__main__":
    nvmid = sys.argv[1] if len(sys.argv) > 1 else "84747291048"
    out = fetch_productdata(nvmid, silent=False)
    if out.get('success'):
        print(f"성공: 상품 {len(out['products'])}개")
    else:
        print("실패:", out.get('error', ''))
