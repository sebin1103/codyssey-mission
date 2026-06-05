CREATE DATABASE IF NOT EXISTS mars_mission
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE mars_mission;

CREATE TABLE IF NOT EXISTS mars_weather (
    weather_id  INT         NOT NULL AUTO_INCREMENT   COMMENT '날씨 데이터 고유 ID (자동 증가)',
    mars_date   DATETIME    NOT NULL                  COMMENT '화성 날짜 및 시간 (필수 입력)',
    temp        INT         NULL                      COMMENT '기온 (°C, 소수점 버림)',
    storm       INT         NULL                      COMMENT '모래 폭풍 강도 (0 ~ 100)',
    PRIMARY KEY (weather_id)
)
ENGINE  = InnoDB
DEFAULT CHARSET  = utf8mb4
COLLATE = utf8mb4_unicode_ci
COMMENT = '화성 날씨 데이터 테이블';

SHOW COLUMNS FROM mars_weather;
