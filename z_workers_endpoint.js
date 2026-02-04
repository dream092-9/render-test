// Cloudflare Workers용 네이버 상품 데이터 추출 엔드포인트
// 중복 제거, 병렬 처리, 중복 복원 기능 포함

/**
 * 네이버 쇼핑 상품 데이터 추출
 * @param {string} nvmid - 네이버 상품 ID
 * @param {string} cookies - 쿠키 문자열
 * @param {object} headers - 요청 헤더
 * @returns {object} 추출 결과
 */
async function extractProductData(nvmid, cookies, headers) {
  const url = `https://smartstore.naver.com/main/products/${nvmid}`;

  const requestHeaders = {
    'User-Agent': headers['user-agent'] || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Cookie': cookies,
    'Accept': 'application/json',
    'Referer': 'https://smartstore.naver.com/',
  };

  // 추가 헤더가 있으면 포함
  if (headers['accept-language']) requestHeaders['Accept-Language'] = headers['accept-language'];
  if (headers['accept-encoding']) requestHeaders['Accept-Encoding'] = headers['accept-encoding'];

  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: requestHeaders,
    });

    if (!response.ok) {
      return {
        success: false,
        nvmid: nvmid,
        error: `HTTP ${response.status}: ${response.statusText}`,
        product: null
      };
    }

    const html = await response.text();

    // HTML에서 상품 데이터 추출 (JSON 데이터 파싱)
    const productDataMatch = html.match(/window\.__APOLLO_STATE__\s*=\s*({.*?});/);
    if (!productDataMatch) {
      return {
        success: false,
        nvmid: nvmid,
        error: '상품 데이터를 찾을 수 없음',
        product: null
      };
    }

    try {
      const jsonStr = productDataMatch[1];
      const productData = JSON.parse(jsonStr);

      // 상품 정보 추출 로직 (필요에 따라 수정)
      const productInfo = extractProductInfo(productData, nvmid);

      return {
        success: true,
        nvmid: nvmid,
        error: null,
        product: productInfo
      };
    } catch (parseError) {
      return {
        success: false,
        nvmid: nvmid,
        error: `JSON 파싱 오류: ${parseError.message}`,
        product: null
      };
    }
  } catch (error) {
    return {
      success: false,
      nvmid: nvmid,
      error: error.message || '알 수 없는 오류',
      product: null
    };
  }
}

/**
 * 상품 정보 추출 (Apollo State에서 데이터 파싱)
 * @param {object} productData - Apollo State 데이터
 * @param {string} nvmid - 상품 ID
 * @returns {object} 상품 정보
 */
function extractProductInfo(productData, nvmid) {
  // Apollo State에서 상품 정보 찾기
  // 구조에 따라 적절히 수정 필요
  const defaultProduct = {
    nvmid: parseInt(nvmid),
    productTitle: 'N/A',
    mallName: 'N/A',
    category: 'N/A',
    price: 0,
    imageUrl: '',
    // 필요한 필드 추가
  };

  try {
    // Apollo State의 키 중에서 nvmid와 관련된 데이터 찾기
    const keys = Object.keys(productData);
    const productKey = keys.find(key => key.includes(`Product:${nvmid}`) || key.includes(nvmid));

    if (productKey && productData[productKey]) {
      const data = productData[productKey];
      return {
        nvmid: parseInt(nvmid),
        productTitle: data.productTitle || data.name || defaultProduct.productTitle,
        mallName: data.mallName || data.mall?.name || defaultProduct.mallName,
        category: data.category || data.categoryName || defaultProduct.category,
        lowPrice: data.lowPrice || data.price || defaultProduct.price,
        imageUrl: data.imageUrl || data.thumbnailUrl || defaultProduct.imageUrl,
        description: data.description || '',
        // 필요한 필드 더 추가
      };
    }
  } catch (error) {
    console.error('상품 정보 추출 오류:', error);
  }

  return defaultProduct;
}

/**
 * 배치 처리: nvmid 목록에서 중복 제거 후 순차 처리 (Workers 제한 대응)
 * @param {array} nvmids - nvmid 목록 (원래 순서 유지)
 * @param {string} cookies - 쿠키 문자열
 * @param {object} headers - 요청 헤더
 * @param {number} concurrency - 동시 처리 수 (기본값: 20, Workers 제한으로 인해 순차 처리)
 * @returns {object} 처리 결과 (중복 복원됨)
 */
async function extractProductDataBatch(nvmids, cookies, headers, concurrency = 20) {
  // 중복 제거하면서 원래 인덱스 매핑 정보 저장
  const nvmidToIndices = {};
  for (let idx = 0; idx < nvmids.length; idx++) {
    const nvmid = nvmids[idx];
    if (!nvmidToIndices[nvmid]) {
      nvmidToIndices[nvmid] = [idx];
    } else {
      nvmidToIndices[nvmid].push(idx);
    }
  }

  // 중복 제거 (순서 유지)
  const uniqueNvmids = [...new Set(nvmids)];
  const duplicates = nvmids.length - uniqueNvmids.length;

  // Workers 하위 요청 제한으로 인해 순차 처리
  const results = [];
  let successCount = 0;
  let failCount = 0;

  // 순차 처리 (Workers 제한 대응)
  for (const nvmid of uniqueNvmids) {
    try {
      const result = await extractProductData(nvmid, cookies, headers);
      results.push(result);

      if (result.success) {
        successCount++;
      } else {
        failCount++;
      }

      // 너무 빠른 요청 방지 (약간의 지연)
      await new Promise(resolve => setTimeout(resolve, 10));
    } catch (error) {
      results.push({
        success: false,
        nvmid: nvmid,
        error: error.message || '알 수 없는 오류',
        product: null
      });
      failCount++;
    }
  }

  // 중복 복원: 원래 순서대로 결과 배치
  const restoredResults = new Array(nvmids.length);
  for (let uniqueIdx = 0; uniqueIdx < results.length; uniqueIdx++) {
    const nvmid = uniqueNvmids[uniqueIdx];
    const result = results[uniqueIdx];
    // 해당 nvmid의 모든 인덱스 위치에 같은 결과 복사
    for (const originalIdx of nvmidToIndices[nvmid]) {
      restoredResults[originalIdx] = result;
    }
  }

  return {
    success: true,
    total: nvmids.length,
    success_count: successCount,
    fail_count: failCount,
    original_unique_nvmids: uniqueNvmids.length,
    duplicates_removed: duplicates,
    results: restoredResults
  };
}

/**
 * Cloudflare Workers 메인 핸들러
 */
export default {
  async fetch(request, env, ctx) {
    // CORS 헤더 설정
    const corsHeaders = {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Max-Age': '86400',
    };

    // OPTIONS 요청 처리 (CORS preflight)
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders,
      });
    }

    // POST 요청만 처리
    if (request.method !== 'POST') {
      return new Response(JSON.stringify({
        success: false,
        error: 'Method not allowed. Use POST.'
      }), {
        status: 405,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
        },
      });
    }

    try {
      // 요청 파싱
      const requestBody = await request.json();
      const { nvmids, cookies, headers, concurrency = 50 } = requestBody;

      // 필수 파라미터 검증
      if (!nvmids || !Array.isArray(nvmids) || nvmids.length === 0) {
        return new Response(JSON.stringify({
          success: false,
          error: 'nvmids 배열이 비어있습니다.'
        }), {
          status: 400,
          headers: {
            ...corsHeaders,
            'Content-Type': 'application/json',
          },
        });
      }

      if (!cookies || typeof cookies !== 'string') {
        return new Response(JSON.stringify({
          success: false,
          error: 'cookies가 필요합니다.'
        }), {
          status: 400,
          headers: {
            ...corsHeaders,
            'Content-Type': 'application/json',
          },
        });
      }

      // 배치 처리 실행
      const result = await extractProductDataBatch(
        nvmids,
        cookies,
        headers || {},
        concurrency
      );

      // 응답 반환
      return new Response(JSON.stringify(result, null, 2), {
        status: 200,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
        },
      });

    } catch (error) {
      // 에러 처리
      return new Response(JSON.stringify({
        success: false,
        error: error.message || 'Internal server error',
        results: []
      }), {
        status: 500,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
        },
      });
    }
  },
};
