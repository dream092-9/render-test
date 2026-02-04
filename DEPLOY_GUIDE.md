# Cloudflare Workers 배포 가이드

## 📋 사전 준비

### 1. Node.js 설치 확인
```bash
node --version
npm --version
```

설치되어 있지 않으면: https://nodejs.org/

### 2. Wrangler CLI 설치
```bash
npm install -g wrangler
```

### 3. Cloudflare 계정 로그인
```bash
wrangler login
```
브라우저가 열리고 Cloudflare 계정으로 로그인합니다.

---

## 🚀 배포 단계

### 1단계: 필수 파일 확인
다음 파일들이 `d:\render_test\` 디렉토리에 있는지 확인:
- ✅ `z_workers_endpoint.js` (Workers 코드)
- ✅ `wrangler.toml` (설정 파일)
- ✅ `package.json` (NPM 설정)

### 2단계: Workers 배포
```bash
cd d:\render_test
wrangler publish
```

### 3단계: 배포 결과 확인
성공하면 다음과 같은 메시지가 나옵니다:
```
✨ Successfully published your Worker to
  https://naver-product-data.YOUR_SUBDOMAIN.workers.dev
```

---

## 🧪 테스트

### 1. Workers 직접 테스트
```bash
curl -X POST https://naver-product-data.YOUR_SUBDOMAIN.workers.dev/extract_productdata_batch \
  -H "Content-Type: application/json" \
  -d '{
    "nvmids": ["10267318504"],
    "cookies": "your_cookie_string",
    "headers": {}
  }'
```

### 2. Python 스크립트로 테스트
```bash
python z_workers_endpoint.py https://naver-product-data.YOUR_SUBDOMAIN.workers.dev
```

---

## 📊 Workers 대시보드

https://dash.cloudflare.com/ -> Workers & Pages

에서 다음을 확인할 수 있습니다:
- 로그 보기
- 요청 통계
- 배포 내역

---

## 🔧 문제 해결

### 에러: "Wrangler is not authenticated"
```bash
wrangler login
```

### 에러: "Worker script not found"
현재 디렉토리에 `z_workers_endpoint.js` 파일이 있는지 확인

### 에러: "Name already exists"
```bash
# 기존 Worker 삭제 후 재배포
wrangler delete naver-product-data
wrangler publish
```

---

## 📝 배포 후 사용

### Workers URL 확인
배포 완료 후 출력되는 URL을 복사해서 Python 스크립트에 사용:

```bash
python z_workers_endpoint.py https://naver-product-data.YOUR_SUBDOMAIN.workers.dev
```

### 결과 파일
`zz_workers.json`에 결과가 저장됩니다.
