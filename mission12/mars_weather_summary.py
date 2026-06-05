"""
mars_weather_summary.py

화성 날씨 데이터를 MySQL 데이터베이스에 저장하는 스크립트.
MySQLHelper 클래스를 통해 DB 연결 및 쿼리를 관리한다.
"""

import csv
import mysql.connector


# ──────────────────────────────────────────────
# 데이터베이스 접속 정보 (환경에 맞게 수정)
# ──────────────────────────────────────────────
DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = 'dodi5231'
DB_NAME = 'mars_mission'

CSV_FILE_PATH = 'mars_weathers_data.csv'


class MySQLHelper:
    """MySQL 데이터베이스 연결 및 쿼리 실행을 편리하게 관리하는 헬퍼 클래스."""

    def __init__(self, host, port, user, password, database):
        """
        MySQLHelper 초기화.

        Args:
            host (str): MySQL 서버 호스트 주소.
            port (int): MySQL 서버 포트 번호.
            user (str): MySQL 접속 사용자 이름.
            password (str): MySQL 접속 비밀번호.
            database (str): 사용할 데이터베이스 이름.
        """
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._connection = None
        self._cursor = None

    # ── 연결 관리 ──────────────────────────────

    def connect(self):
        """MySQL 서버에 연결하고 커서를 초기화한다."""
        self._connection = mysql.connector.connect(
            host=self._host,
            port=self._port,
            user=self._user,
            password=self._password,
            database=self._database,
        )
        self._cursor = self._connection.cursor()
        print(f'[MySQLHelper] 데이터베이스 "{self._database}" 연결 성공.')

    def disconnect(self):
        """커서와 연결을 안전하게 닫는다."""
        if self._cursor:
            self._cursor.close()
        if self._connection and self._connection.is_connected():
            self._connection.close()
        print('[MySQLHelper] 데이터베이스 연결 종료.')

    def __enter__(self):
        """with 문 진입 시 자동 연결."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """with 문 종료 시 자동 연결 해제 및 예외 처리."""
        if exc_type is None:
            self._connection.commit()
        else:
            self._connection.rollback()
            print(f'[MySQLHelper] 오류 발생 — 롤백 처리: {exc_val}')
        self.disconnect()
        return False  # 예외를 상위로 전파

    # ── DDL 유틸리티 ───────────────────────────

    def create_table_if_not_exists(self, ddl_query):
        """
        테이블이 없을 경우 생성한다.

        Args:
            ddl_query (str): CREATE TABLE ... IF NOT EXISTS 형태의 DDL 문.
        """
        self._cursor.execute(ddl_query)
        self._connection.commit()
        print('[MySQLHelper] 테이블 생성(또는 이미 존재) 확인 완료.')

    # ── DML 유틸리티 ───────────────────────────

    def execute_query(self, query, params=None):
        """
        단일 DML/DDL 쿼리를 실행한다.

        Args:
            query (str): 실행할 SQL 문.
            params (tuple | None): 바인딩 파라미터.

        Returns:
            int: 영향을 받은 행 수.
        """
        self._cursor.execute(query, params or ())
        return self._cursor.rowcount

    def execute_many(self, query, data):
        """
        동일한 쿼리를 여러 행의 데이터로 반복 실행한다.

        Args:
            query (str): 실행할 SQL 문 (플레이스홀더 포함).
            data (list[tuple]): 삽입할 데이터 목록.

        Returns:
            int: 영향을 받은 행 수.
        """
        self._cursor.executemany(query, data)
        self._connection.commit()
        return self._cursor.rowcount

    def fetch_all(self, query, params=None):
        """
        SELECT 쿼리를 실행하고 모든 결과 행을 반환한다.

        Args:
            query (str): 실행할 SELECT 문.
            params (tuple | None): 바인딩 파라미터.

        Returns:
            list[tuple]: 조회 결과 행 목록.
        """
        self._cursor.execute(query, params or ())
        return self._cursor.fetchall()

    def fetch_one(self, query, params=None):
        """
        SELECT 쿼리를 실행하고 첫 번째 결과 행을 반환한다.

        Args:
            query (str): 실행할 SELECT 문.
            params (tuple | None): 바인딩 파라미터.

        Returns:
            tuple | None: 첫 번째 결과 행 또는 None.
        """
        self._cursor.execute(query, params or ())
        return self._cursor.fetchone()

    def commit(self):
        """현재 트랜잭션을 커밋한다."""
        self._connection.commit()

    def rollback(self):
        """현재 트랜잭션을 롤백한다."""
        self._connection.rollback()


# ──────────────────────────────────────────────
# DDL — 테이블 생성 쿼리
# ──────────────────────────────────────────────
CREATE_TABLE_QUERY = """
CREATE TABLE IF NOT EXISTS mars_weather (
    weather_id  INT             NOT NULL AUTO_INCREMENT,
    mars_date   DATETIME        NOT NULL,
    temp        INT             NULL,
    storm       INT             NULL,
    PRIMARY KEY (weather_id)
)
"""

INSERT_QUERY = (
    'INSERT INTO mars_weather (mars_date, temp, storm) '
    'VALUES (%s, %s, %s)'
)


# ──────────────────────────────────────────────
# CSV 처리 함수
# ──────────────────────────────────────────────

def read_csv(file_path):
    """
    CSV 파일을 읽어 헤더와 데이터 행 목록을 반환한다.

    Args:
        file_path (str): CSV 파일 경로.

    Returns:
        tuple[list[str], list[dict]]: (헤더 목록, 행 딕셔너리 목록).
    """
    rows = []
    with open(file_path, newline='', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        headers = reader.fieldnames
        for row in reader:
            rows.append(row)
    print(f'[CSV] "{file_path}" 읽기 완료 — 총 {len(rows)}건.')
    return headers, rows


def preview_csv(headers, rows, limit=5):
    """
    CSV 데이터의 헤더와 상위 N개 행을 출력한다.

    Args:
        headers (list[str]): 컬럼 헤더 목록.
        rows (list[dict]): 행 데이터 목록.
        limit (int): 출력할 최대 행 수. 기본값 5.
    """
    print('\n[CSV 미리보기]')
    print('  컬럼:', headers)
    for i, row in enumerate(rows[:limit]):
        print(f'  [{i + 1}]', dict(row))
    print(f'  ... (전체 {len(rows)}건 중 상위 {min(limit, len(rows))}건 표시)\n')


def build_insert_data(rows):
    """
    CSV 행 목록을 INSERT 용 튜플 목록으로 변환한다.

    CSV 헤더의 'stom' 컬럼을 'storm' 으로 매핑하며,
    temp 값은 소수점을 버려 INT 로 변환한다.

    Args:
        rows (list[dict]): CSV 행 딕셔너리 목록.

    Returns:
        list[tuple]: (mars_date, temp, storm) 튜플 목록.
    """
    data = []
    for row in rows:
        mars_date = row['mars_date']
        temp = int(float(row['temp']))
        # CSV 헤더가 'stom' 으로 오타 처리된 경우도 허용
        storm_raw = row.get('storm') or row.get('stom') or 0
        storm = int(storm_raw)
        data.append((mars_date, temp, storm))
    return data


# ──────────────────────────────────────────────
# 메인 실행 흐름
# ──────────────────────────────────────────────

def main():
    """CSV 파일을 읽어 MySQL mars_weather 테이블에 데이터를 삽입한다."""

    # 1. CSV 파일 읽기 및 미리보기
    headers, rows = read_csv(CSV_FILE_PATH)
    preview_csv(headers, rows)

    # 2. INSERT 용 데이터 준비
    insert_data = build_insert_data(rows)

    # 3. DB 연결 → 테이블 생성 → 데이터 삽입
    with MySQLHelper(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME) as db:

        # 테이블 생성 (없을 경우에만)
        db.create_table_if_not_exists(CREATE_TABLE_QUERY)

        # 행 단위 INSERT (과제 요구사항: 반복 실행)
        inserted = 0
        for params in insert_data:
            db.execute_query(INSERT_QUERY, params)
            inserted += 1
        db.commit()
        print(f'[DB] INSERT 완료 — 총 {inserted}건 삽입.')

        # 결과 확인
        total = db.fetch_one('SELECT COUNT(*) FROM mars_weather')[0]
        print(f'[DB] mars_weather 테이블 현재 행 수: {total}건.')

        sample = db.fetch_all(
            'SELECT * FROM mars_weather ORDER BY weather_id LIMIT 5'
        )
        print('[DB] 상위 5건 샘플:')
        for record in sample:
            print(' ', record)


if __name__ == '__main__':
    main()
