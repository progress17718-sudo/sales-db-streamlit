# 영업 DB 자동 수집 웹툴

현재 버전은 **1차 MVP 안정 버전**입니다.

업종을 선택하면 SerpAPI로 브랜드/업체 공식 사이트 후보를 검색하고, 영업금지 Google Sheet와 대조해 금지 업체를 제외한 뒤 결과를 미리보기 및 Excel로 다운로드합니다.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 필수 환경변수

SerpAPI 검색을 사용하므로 아래 환경변수가 필요합니다.

```powershell
$env:SERPAPI_API_KEY="your_key"
streamlit run app.py
```

앱은 `SERPAPI_API_KEY`를 환경변수 또는 Streamlit secrets에서 읽습니다. 실제 API 키는 코드에 넣지 않습니다.

Streamlit Community Cloud에서는 앱 설정의 **Secrets**에 아래처럼 등록합니다.

```toml
SERPAPI_API_KEY = "your_serpapi_key"
```

선택 기능인 AI 판단을 사용할 경우에만 아래 secrets를 추가합니다.

```toml
OPENAI_API_KEY = "your_openai_key"
OPENAI_MODEL = "gpt-4o-mini"
```

`OPENAI_MODEL`은 생략할 수 있으며, 생략 시 `gpt-4o-mini`를 사용합니다.

화면이나 PowerShell 로그에 API 키 전체를 출력하지 않습니다.

## Streamlit Community Cloud 임시 배포

1. 프로젝트를 GitHub 저장소에 올립니다.
2. Streamlit Community Cloud에서 **New app**을 선택합니다.
3. 저장소, 브랜치, 메인 파일 `app.py`를 지정합니다.
4. **Secrets**에 `SERPAPI_API_KEY`를 등록합니다.
5. 배포 후 화면에서 영업금지 Google Sheet URL을 입력하고 `수집 시작`을 누릅니다.

Google Sheet URL은 화면에서 입력하는 구조를 유지합니다. 앱 시작 시에는 외부 API를 호출하지 않고, 버튼을 눌렀을 때만 SerpAPI와 Google Sheet를 호출합니다.

## Google Sheet 형식

영업금지 리스트는 Google Sheet 공유 URL 또는 CSV URL로 입력합니다. 앱은 수집 시작 버튼을 눌렀을 때만 Google Sheet를 읽습니다.

상단에 제목/공지가 있고 실제 헤더가 중간에 있어도, 상위 30행에서 아래 키워드를 기반으로 헤더 행을 자동 인식합니다.

- `광고주 업체명`
- `사이트`
- `연락처`
- `일자`
- `구분`

브랜드명 후보 컬럼:

- `브랜드명`
- `업체명`
- `회사명`
- `상호명`
- `브랜드`
- `금지업체명`
- `광고주 업체명`
- `광고주업체명`

사이트 후보 컬럼:

- `도메인`
- `URL`
- `사이트`
- `사이트주소`
- `홈페이지`
- `공식URL`
- `공식 URL`

CSV 한글 인코딩은 `utf-8`, `utf-8-sig`, `cp949` 순으로 처리합니다.

## 결과

최종 결과에는 영업금지 업체를 제외한 `사용가능`, `확인필요` 항목만 표시됩니다.

Excel 다운로드 컬럼:

- `상태`
- `업종`
- `브랜드명`
- `사이트`
- `이메일`
- `전화번호`
- `연락처 수집 상태`
- `연락처 수집 사유`
- `연락처 출처 URL`
- `수집출처`
- `수집일`

연락처 수집은 속도가 느릴 수 있어 기본값은 OFF입니다. 사이드바에서 `연락처 수집`을 켜면 최종 결과 사이트의 메인 페이지와 주요 문의/회사소개/고객센터 페이지에서 이메일과 전화번호를 순차 수집해 `이메일`, `전화번호` 컬럼에 반영합니다. 수집 중 확인한 URL과 실패 사유는 화면의 `연락처 수집 접근 로그`에서 확인할 수 있습니다. 이메일과 전화번호는 실제 사이트 페이지, `mailto:`, `tel:`에서 확인된 경우에만 표시하며 도메인 기반으로 추정 생성하지 않습니다.

## 보류 기능

아래 기능은 2차 기능으로 보류했습니다.

- 직접 검색어 입력
- 검색 기록 저장
- 이전 검색 결과 중복 제외
- 랜덤 검색
- 검색 기록 초기화
- 결과 부족 시 반복 추가 검색

## 수집 정책

- 사용자가 `수집 시작` 버튼을 눌렀을 때만 SerpAPI와 Google Sheet를 호출합니다.
- 채용, 뉴스, 블로그, 카페, 유튜브, 위키, GitHub 등 기본 품질 필터를 적용합니다.
- 필터링 후 결과가 부족해도 억지로 채우지 않고 실제 남은 결과만 표시합니다.
