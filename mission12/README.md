# 화성 날씨 데이터 저장 시스템 코드 설명

> **파일 구성**
> - `mars_weather_ddl.sql` — 데이터베이스 및 테이블 생성
> - `mars_weather_summary.py` — CSV 읽기 → MySQL 저장

---

## 1. SQL 코드 (`mars_weather_ddl.sql`)

### 1-1. 데이터베이스 생성

```sql
CREATE DATABASE IF NOT EXISTS mars_mission
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;
```

| 옵션 | 설명 |
|---|---|
| `IF NOT EXISTS` | 이미 존재하면 오류 없이 건너뜀 |
| `CHARACTER SET utf8mb4` | 한글·이모지 등 4바이트 문자 완전 지원 |
| `COLLATE utf8mb4_unicode_ci` | 대소문자 구분 없이 유니코드 기준 정렬 |

---

### 1-2. 테이블 생성

```sql
CREATE TABLE IF NOT EXISTS mars_weather (
    weather_id  INT         NOT NULL AUTO_INCREMENT   COMMENT '날씨 데이터 고유 ID',
    mars_date   DATETIME    NOT NULL                  COMMENT '화성 날짜 및 시간',
    temp        INT         NULL                      COMMENT '기온 (°C)',
    storm       INT         NULL                      COMMENT '모래 폭풍 강도 (0~100)',
    PRIMARY KEY (weather_id)
)
ENGINE  = InnoDB
DEFAULT CHARSET  = utf8mb4
COLLATE = utf8mb4_unicode_ci;
```

#### 컬럼 상세

| 컬럼 | 타입 | 제약 | 설명 |
|---|---|---|---|
| `weather_id` | `INT` | `NOT NULL`, `AUTO_INCREMENT`, `PK` | 행마다 자동으로 1씩 증가하는 고유 번호 |
| `mars_date` | `DATETIME` | `NOT NULL` | 날짜 필수 입력. `YYYY-MM-DD HH:MM:SS` 형식 |
| `temp` | `INT` | `NULL` 허용 | 기온. CSV의 소수점 값은 Python에서 정수로 변환 후 저장 |
| `storm` | `INT` | `NULL` 허용 | 모래 폭풍 강도. 0(없음) ~ 100(최강) |

#### 테이블 옵션

| 옵션 | 설명 |
|---|---|
| `ENGINE = InnoDB` | 트랜잭션(커밋/롤백) 및 외래키 지원 엔진 |
| `PRIMARY KEY (weather_id)` | `weather_id` 를 기본키로 지정 → 중복 불가, 빠른 검색 |

---

## 2. Python 코드 (`mars_weather_summary.py`)

### 2-1. 전체 구조

```
mars_weather_summary.py
│
├── [상수] DB 접속 정보 / CSV 경로
│
├── [클래스] MySQLHelper          ← 보너스 과제
│   ├── connect() / disconnect()
│   ├── __enter__ / __exit__      ← with 문 지원
│   ├── create_table_if_not_exists()
│   ├── execute_query()
│   ├── execute_many()
│   ├── fetch_all() / fetch_one()
│   └── commit() / rollback()
│
├── [상수] CREATE_TABLE_QUERY / INSERT_QUERY
│
├── [함수] read_csv()             ← CSV 파일 읽기
├── [함수] preview_csv()          ← 미리보기 출력
├── [함수] build_insert_data()    ← INSERT 튜플 변환
│
└── [함수] main()                 ← 전체 흐름 실행
```

---

### 2-2. 접속 정보 상수

```python
DB_HOST     = 'localhost'
DB_PORT     = 3306
DB_USER     = 'root'
DB_PASSWORD = 'your_password'
DB_NAME     = 'mars_mission'

CSV_FILE_PATH = 'mars_weathers_data.csv'
```

실행 환경에 맞게 `DB_PASSWORD`와 `CSV_FILE_PATH`를 수정한다.  
`CSV_FILE_PATH`는 절대 경로 권장 (예: `/Users/sebin/Desktop/src/mars_weathers_data.csv`).

---

### 2-3. MySQLHelper 클래스

#### `__init__` — 초기화

```python
def __init__(self, host, port, user, password, database):
    self._host       = host
    self._port       = port
    self._user       = user
    self._password   = password
    self._database   = database
    self._connection = None   # 연결 객체 (아직 연결 안 함)
    self._cursor     = None   # 커서 객체 (아직 연결 안 함)
```

접속 정보만 저장하고 실제 연결은 하지 않는다.  
연결은 `connect()` 또는 `with` 문 진입 시 수행된다.

---

#### `connect` / `disconnect` — 연결 열기·닫기

```python
def connect(self):
    self._connection = mysql.connector.connect(
        host=self._host, port=self._port,
        user=self._user, password=self._password,
        database=self._database,
    )
    self._cursor = self._connection.cursor()

def disconnect(self):
    if self._cursor:
        self._cursor.close()
    if self._connection and self._connection.is_connected():
        self._connection.close()
```

- `connect()`: MySQL 서버에 연결하고 SQL을 실행할 **커서**를 만든다.  
- `disconnect()`: 커서와 연결을 순서대로 닫는다. `is_connected()` 확인으로 이중 닫기를 방지한다.

---

#### `__enter__` / `__exit__` — `with` 문 지원

```python
def __enter__(self):
    self.connect()
    return self

def __exit__(self, exc_type, exc_val, exc_tb):
    if exc_type is None:
        self._connection.commit()   # 정상 종료 → 커밋
    else:
        self._connection.rollback() # 예외 발생 → 롤백
    self.disconnect()
    return False  # 예외를 상위로 전파
```

`with MySQLHelper(...) as db:` 형태로 사용하면:
- 블록 진입 시 자동으로 `connect()` 호출
- 블록 종료 시 성공이면 **커밋**, 오류면 **롤백** 후 `disconnect()` 자동 호출
- 리소스 누수 없이 안전하게 DB를 사용할 수 있다

---

#### `execute_query` — 단일 쿼리 실행

```python
def execute_query(self, query, params=None):
    self._cursor.execute(query, params or ())
    return self._cursor.rowcount
```

- `params`에 `(값1, 값2, ...)` 형태의 튜플을 전달하면 SQL 인젝션 없이 안전하게 값을 바인딩한다.  
- `rowcount`로 영향받은 행 수를 반환한다.

---

#### `execute_many` — 다건 일괄 실행

```python
def execute_many(self, query, data):
    self._cursor.executemany(query, data)
    self._connection.commit()
    return self._cursor.rowcount
```

- `data`는 튜플의 리스트. 같은 쿼리를 여러 행에 반복 적용할 때 사용한다.  
- 내부적으로 한 번의 네트워크 요청으로 처리돼 `execute_query` 반복보다 빠르다.

---

#### `fetch_all` / `fetch_one` — 조회

```python
def fetch_all(self, query, params=None):
    self._cursor.execute(query, params or ())
    return self._cursor.fetchall()  # 전체 결과 반환

def fetch_one(self, query, params=None):
    self._cursor.execute(query, params or ())
    return self._cursor.fetchone()  # 첫 번째 행만 반환
```

| 메서드 | 반환 | 주요 사용처 |
|---|---|---|
| `fetch_all` | `list[tuple]` | 여러 행 조회 (목록, 리포트) |
| `fetch_one` | `tuple \| None` | 단일 값 조회 (`COUNT(*)` 등) |

---

### 2-4. CSV 처리 함수

#### `read_csv` — 파일 읽기

```python
def read_csv(file_path):
    rows = []
    with open(file_path, newline='', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        headers = reader.fieldnames          # ['weather_id', 'mars_date', 'temp', 'stom']
        for row in reader:
            rows.append(row)                 # 각 행을 dict로 저장
    return headers, rows
```

- `csv.DictReader`를 사용하면 첫 번째 행(헤더)을 자동으로 키로 인식해 각 행을 `dict`로 반환한다.
- `newline=''`은 줄바꿈 문자 처리 오류를 방지하는 표준 권장 방식이다.

---

#### `build_insert_data` — 타입 변환 및 오타 처리

```python
def build_insert_data(rows):
    data = []
    for row in rows:
        mars_date = row['mars_date']
        temp      = int(float(row['temp']))              # '21.4' → 21
        storm_raw = row.get('storm') or row.get('stom') or 0  # 오타 'stom' 허용
        storm     = int(storm_raw)
        data.append((mars_date, temp, storm))
    return data
```

- `temp`: CSV에 `21.4`처럼 소수점으로 저장된 값을 `int(float(...))` 으로 정수 변환해 DB `INT` 타입에 맞춘다.
- `storm`: CSV 헤더가 `stom`으로 오타가 나 있어 `row.get('storm') or row.get('stom')`으로 두 경우 모두 처리한다.

---

### 2-5. `main` — 전체 실행 흐름

```python
def main():
    # 1. CSV 읽기
    headers, rows = read_csv(CSV_FILE_PATH)
    preview_csv(headers, rows)

    # 2. INSERT 데이터 준비
    insert_data = build_insert_data(rows)

    # 3. DB 작업 (with 블록 = 자동 커밋/롤백/연결 해제)
    with MySQLHelper(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME) as db:

        db.create_table_if_not_exists(CREATE_TABLE_QUERY)  # 테이블 생성

        inserted = 0
        for params in insert_data:                          # 행 단위 반복 INSERT
            db.execute_query(INSERT_QUERY, params)
            inserted += 1
        db.commit()

        total  = db.fetch_one('SELECT COUNT(*) FROM mars_weather')[0]
        sample = db.fetch_all('SELECT * FROM mars_weather LIMIT 5')
```

#### 실행 순서 요약

```
CSV 파일 읽기
    ↓
헤더 & 데이터 미리보기 출력
    ↓
(mars_date, temp, storm) 튜플 목록 생성
    ↓
MySQLHelper with 블록 진입 → DB 연결
    ↓
mars_weather 테이블 생성 (없을 때만)
    ↓
1000건 행 단위 INSERT 반복
    ↓
커밋 → 결과 확인 출력
    ↓
with 블록 종료 → DB 연결 해제
```

---

## 3. 실행 방법

```bash
# 1. 패키지 설치
/usr/local/bin/python3 -m pip install mysql-connector-python

# 2. SQL 실행 (테이블 생성)
mysql -u root -p < mars_weather_ddl.sql

# 3. Python 스크립트 실행
/usr/local/bin/python3 /Users/sebin/Desktop/src/mars_weather_summary.py
```

> `CSV_FILE_PATH`를 절대 경로로 지정하는 것을 권장한다.
> ```python
> CSV_FILE_PATH = '/Users/sebin/Desktop/src/mars_weathers_data.csv'
> ```
