import itertools
import string
import time
import zipfile
from pathlib import Path


def unlock_zip(
    zip_path='emergency_storage_key.zip',
    password_file='password.txt',
    progress_step=10000,
):
    start_time = time.time()
    start_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
    print(f'시작 시간: {start_text}')

    charset = string.ascii_lowercase + string.digits
    zip_file_path = Path(zip_path)

    if not zip_file_path.exists():
        print(f'오류: zip 파일을 찾을 수 없습니다. ({zip_file_path})')
        return None

    attempts = 0
    found_password = None

    try:
        with zipfile.ZipFile(zip_file_path) as zip_file:
            for chars in itertools.product(charset, repeat=6):
                attempts += 1
                candidate = ''.join(chars)

                if attempts % progress_step == 0:
                    print(f'시도 횟수: {attempts:,} / 현재 비밀번호: {candidate}')

                try:
                    zip_file.extractall(pwd=candidate.encode('utf-8'))
                    found_password = candidate
                    break
                except (RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile):
                    continue
                except Exception:
                    continue
    except FileNotFoundError:
        print(f'오류: zip 파일을 열 수 없습니다. ({zip_file_path})')
        return None
    except zipfile.BadZipFile:
        print(f'오류: 손상된 zip 파일입니다. ({zip_file_path})')
        return None

    end_time = time.time()
    end_text = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))
    elapsed = end_time - start_time

    print(f'종료 시간: {end_text}')
    print(f'총 소요 시간: {elapsed:.2f}초')
    print(f'총 시도 횟수: {attempts:,}')

    if found_password is None:
        print('비밀번호를 찾지 못했습니다.')
        return None

    password_path = Path(password_file)
    password_path.write_text(found_password, encoding='utf-8')
    print(f'비밀번호를 찾았습니다: {found_password}')
    print(f'비밀번호 저장 파일: {password_path}')
    return found_password


if __name__ == '__main__':
    unlock_zip()