# HEAVYCON 2007 계약서 분석기

스캔한 **BIMCO HEAVYCON 2007 (Standard Heavy Lift Charter Party)** 계약서 PDF를
읽어, PART I 의 **Box 1~30 핵심 항목**을 자동으로 뽑아 화면의 표로 보여 주고
**CSV · XLSX** 파일로 내보내 주는 데스크톱 프로그램입니다.

- 대상 계약서: **BIMCO HEAVYCON 2007 전용** 입니다. (SUPPLYTIME, NYPE, GENCON 등
  다른 양식은 지원하지 않으며, 양식 자동판별 기능도 없습니다.)
- 동작 방식: **완전 오프라인**, **CPU만**으로 동작합니다. 인터넷·GPU가 필요 없습니다.
- 문자 인식(OCR): **Tesseract** 엔진을 사용합니다.
- 특수조항(Box 30, 추가 조항): **원문만 그대로 추출**합니다. AI 요약 기능은 없습니다.

---

## 1. 이 프로그램이 하는 일

1. 스캔된 계약서 PDF(하드카피 스캔본)를 입력받습니다.
2. Tesseract OCR로 텍스트를 인식합니다.
3. HEAVYCON 2007 PART I 의 Box 1~30 항목을 규칙 기반으로 추출합니다. 특히 다음
   핵심 항목이 포함됩니다.

   | Box | 항목(한글) |
   | --- | --- |
   | 2 | 용선주(Out)/선주 |
   | 3 | 용선주(In)/용선자 |
   | 4 | 선박 |
   | 5 | 화물 |
   | 6 | 선적지 |
   | 7 | 양하지 |
   | 8 | 선적방식 |
   | 9 | 양하방식 |
   | 10 | 기간 |
   | 11 | 일정통지(용선주) |
   | 12 | 선적일정(선박) |
   | 13 | 양하일정(선박) |
   | 15 | MWS & 승인 |
   | 16 | 운임 |
   | 17 | 운임수령 / Payment terms |
   | 18 | 프리타임 |
   | 19 | 디머리지 |
   | 20 · 21 | 몹디몹 비용 |
   | 22 | 운하통항비 |
   | 23 | 벙커 연동 |
   | 30 | 특수조항(원문 추출) |

4. 결과를 창(GUI)의 표로 보여 주고, **CSV** 및 **XLSX** 로 내보냅니다.
   (PDF 리포트 기능은 없습니다.)

---

## 2. 시스템 요구사항

- **운영체제:** Windows (오프라인 환경에서 사용 가능)
- **처리 장치:** CPU만 있으면 됩니다. GPU 불필요.
- **인터넷:** 프로그램 실행 시 인터넷이 **필요 없습니다.** (아래 설치 단계에서만
  파일을 내려받습니다.)
- **Python:** 소스에서 직접 실행할 경우 Python 3.11 이상.
- **Tesseract OCR 엔진:** 반드시 별도로 설치해야 합니다(아래 3번 참조).

---

## 3. Tesseract OCR 엔진 설치 (Windows)

이 프로그램은 문자 인식을 위해 Tesseract 엔진이 **컴퓨터에 설치되어 있어야**
합니다. (프로그램 자체에는 포함되어 있지 않습니다.)

1. Windows용 Tesseract 설치 파일을 내려받아 설치합니다. 널리 쓰이는 빌드는
   UB Mannheim 버전입니다: [Tesseract at UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
2. 설치 중 **English (eng) 언어 데이터**가 포함되도록 선택합니다. (계약서가
   영어이므로 영어 데이터가 필요합니다.)
3. 기본 설치 경로는 보통 다음과 같습니다.

   ```
   C:\Program Files\Tesseract-OCR\tesseract.exe
   ```

4. 위 경로를 시스템 `PATH`에 추가하거나, 프로그램에서 Tesseract 실행 파일 경로를
   지정할 수 있습니다. (코드에서 `tesseract_cmd` 값으로 위 경로를 넣으면 됩니다.)

> 참고: PDF 를 이미지로 변환하기 위해 아래 4번의 파이썬 선택 패키지(`PyMuPDF`)도
> 필요합니다. PyMuPDF 는 별도 외부 프로그램 없이 동작합니다.

---

## 4. 소스에서 실행하기

### 4-1. 파이썬 선택 패키지 설치 (OCR/PDF용)

핵심 프로그램은 파이썬 표준 라이브러리만으로 표시·내보내기까지 동작하지만,
실제 OCR/PDF 처리를 하려면 아래 선택 패키지가 필요합니다. 인터넷이 되는 환경에서
한 번만 설치하면 됩니다.

```
py -m pip install .[ocr]
```

위 명령은 다음을 설치합니다.

- `pytesseract` — Tesseract 엔진 파이썬 연결
- `Pillow` — 이미지 처리
- `PyMuPDF` — PDF 를 이미지로 변환(래스터화)

### 4-2. 프로그램 실행

```
python -m heavycon_analyzer
```

(또는 패키지를 설치했다면 `heavycon-analyzer` 명령으로도 실행됩니다.)

---

## 5. 창 사용법

1. **[분석할 PDF 열기]** 버튼을 눌러 스캔한 계약서 PDF를 선택합니다.
2. **[분석 실행]** 버튼을 누릅니다. OCR·추출이 백그라운드에서 진행되며 하단에
   진행 상태가 표시됩니다.
3. 분석이 끝나면 표에 **Box 번호 / 항목(영문) / 항목(한글) / 값** 이 채워집니다.
   내용을 검토합니다.
4. **[CSV 내보내기]** 또는 **[XLSX 내보내기]** 버튼으로 결과를 파일로 저장합니다.
   (CSV 는 Excel 에서 한글이 깨지지 않도록 UTF-8 BOM 으로 저장됩니다.)

> Tesseract 엔진이나 PDF 관련 구성요소가 설치되어 있지 않으면 분석 시 안내
> 메시지 창이 뜹니다. 이 문서(README)의 3~4번 설치 안내를 따라 설치해 주세요.

---

## 6. 독립 실행형 Windows .exe 만들기 (PyInstaller)

프로그래밍을 몰라도 클릭만으로 실행할 수 있는 `.exe` 로 만들 수 있습니다.
이 빌드 작업은 **인터넷이 되는 Windows 컴퓨터**에서 한 번만 하면 됩니다.

```
py -m pip install pyinstaller
py -m pip install .[ocr]
py -m PyInstaller --noconfirm packaging/heavycon_analyzer.spec
```

> **주의:** `pyinstaller` 명령이 "명령을 찾을 수 없습니다" 라고 나오면(PATH 에
> 등록되지 않은 경우), 위처럼 반드시 `py -m PyInstaller` 형태로 실행하세요.
> (`PyInstaller` 의 대소문자도 그대로 맞춰야 합니다.)

- 결과물은 `dist/HeavyconAnalyzer/HeavyconAnalyzer.exe` 에 생성됩니다. 이제
  이 파일을 더블클릭하면 프로그램 창이 정상적으로 열립니다.
- 이 `.exe` 는 파이썬 코드와 파이썬 패키지만 포함합니다. **Tesseract OCR
  엔진은 포함하지 않으므로**, 실행할 대상 컴퓨터에도 3번의 Tesseract 엔진을
  반드시 설치해야 합니다.

> 빌드 없이 소스에서 바로 실행하고 싶다면 아래 명령이 계속 유효합니다.
>
> ```
> py -m heavycon_analyzer
> ```
>
> 예전 버전은 `.exe` 를 실행하면
> `ImportError: attempted relative import with no known parent package`
> 오류로 즉시 종료되었습니다. 이는 PyInstaller 가 패키지 진입 파일
> (`__main__.py`)을 최상위 스크립트로 실행하면서 상대(relative) 임포트가 부모
> 패키지를 찾지 못했기 때문입니다. 이제는 절대(absolute) 임포트를 사용하는
> 전용 진입 스크립트(`packaging/launcher.py`)로 빌드하므로 이 오류가
> 발생하지 않습니다.

---

## 7. 참고 사항

- 본 도구는 **HEAVYCON 2007 전용**이며 **완전 오프라인**으로 동작합니다.
- 다른 양식(SUPPLYTIME, NYPE, GENCON 등)은 동일한 골격으로 추후 별도 구현할 수
  있도록 설계되어 있습니다.
- **빌드/개발 샌드박스 환경에서는 Tesseract 엔진과 인터넷을 사용할 수 없어
  실제 OCR(PDF → Tesseract → 추출)의 엔드투엔드 실행은 수행하지 않았습니다.**
  대신 합성 OCR 픽스처와 단위 테스트로 추출·내보내기·화면 표시 로직의 정확성을
  검증했습니다. 실제 OCR 동작은 위 설치 단계를 마친 실제 Windows 컴퓨터에서
  확인하실 수 있습니다.
