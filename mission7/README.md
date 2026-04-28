# 계산기 (Calculator)

아이폰 스타일의 GUI 계산기. 연산 로직을 담당하는 `Calculator` 클래스와 PyQt5 기반 UI를 한 파일(`calculator.py`)에 담았다.

## 요구 환경

- Python 3.x
- PyQt5

```bash
pip install PyQt5
```

## 실행

```bash
python3 calculator.py
```

## 파일 구성

```
7/
├── calculator.py   # Calculator 클래스 + CalculatorUI 위젯
└── README.md
```

## 설계

### Calculator 클래스 (연산 코어)

UI와 분리된 순수 로직 클래스. 상태로 `current`(현재 표시 값), `previous`(직전 피연산자), `operator`(대기 중인 연산자), `start_new`(다음 숫자 입력 시 화면을 새로 시작할지 여부)를 들고 있다.

| 메서드 | 역할 |
| --- | --- |
| `reset()` | 모든 상태를 초기화한다 (AC 키). |
| `add(a, b)` / `subtract(a, b)` / `multiply(a, b)` / `divide(a, b)` | 사칙연산. `divide`는 `b == 0`이면 `ZeroDivisionError`를 던진다. |
| `negative_positive()` | 현재 표시 값의 부호를 토글한다 (`+/-` 키). |
| `percent()` | 현재 표시 값을 100으로 나눈다 (`%` 키). |
| `input_digit(digit)` | 숫자 키 입력. 누를 때마다 `current`에 누적한다. |
| `input_dot()` | 소수점 입력. 이미 `'.'`이 있으면 무시한다. |
| `set_operator(op)` | 연산자 키 입력. 직전 입력이 숫자였다면 누적된 연산을 먼저 처리해 연속 계산(`2 + 3 + 4`)을 지원한다. |
| `equal()` | `=` 키. `previous operator current`를 계산해 `current`에 결과를 넣는다. |

> 메서드 이름은 PEP 8에 맞춰 snake_case로 작성했다. 과제 명세의 `negative-positive`는 파이썬 식별자에 하이픈을 쓸 수 없어 `negative_positive`로 표기한다.

### CalculatorUI 클래스 (PyQt5)

검정 배경 / 주황 연산자 / 회색 기능 키 / 어두운 회색 숫자 키로 구성된 5×4 그리드. 모든 버튼의 클릭 핸들러는 `_on_click(text)` 하나로 모이고, 텍스트에 따라 적절한 `Calculator` 메서드로 분기한 뒤 `_update_display()`로 화면을 갱신한다.

## 예외 처리

- **0으로 나누기** — `divide()`가 `ZeroDivisionError`를 던지고, `equal()`이 잡아 화면에 `Error`를 표시한다.
- **오버플로우** — 결과가 `±inf`, `NaN`, 또는 `±1e308` 초과면 `OverflowError`로 처리해 `Overflow`를 표시한다.
- **에러 상태에서 숫자 키 입력** — `Error`/`Overflow` 표시 중 숫자/소수점을 누르면 자동으로 `reset()` 후 입력이 시작된다.
- **소수점 중복 입력** — `'.' not in self.current` 가드로 두 번째 소수점 입력은 무시된다.
- **과도하게 긴 입력** — 한 화면에 표시 가능한 길이(16자리)를 넘으면 더 이상 누적하지 않는다.

## 보너스 과제

- **소수점 6자리 반올림** — `_format_number()`가 결과를 `round(value, 6)`으로 반올림한 뒤, 정수면 정수 표기(`8`), 소수면 끝의 불필요한 `0`을 제거한 표기(`0.333333`)로 변환한다.
- **결과 길이에 따른 폰트 자동 조정** — `_adjust_font_size()`가 표시 문자열의 길이에 따라 `56 → 46 → 36 → 28 → 22pt` 단계로 폰트를 줄여, 긴 결과도 한 줄에 들어오게 한다.

## 사용 예

| 입력 | 결과 |
| --- | --- |
| `12 + 7 =` | `19` |
| `5 - 8 =` | `-3` |
| `6 * 7 =` | `42` |
| `9 / 4 =` | `2.25` |
| `5 / 0 =` | `Error` |
| `2 + 3 + 4 =` (중간 `=` 없이) | `9` |
| `50 %` | `0.5` |
| `1 / 3 =` | `0.333333` |
| `5 +/- +/-` | `5` |

## 코딩 스타일

- PEP 8 준수
- 문자열은 작은따옴표(`'`) 기본
- 대입문 `=` 앞뒤 공백
- 들여쓰기는 공백 4칸
- 외부 라이브러리는 UI용 PyQt5만 사용
