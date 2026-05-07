import zipfile
import time
import datetime
import itertools
import string
import zlib

def unlock_zip():
    zip_filename = 'emergency_storage_key.zip'
    output_filename = 'password.txt'
    
    try:
        zip_file = zipfile.ZipFile(zip_filename)
        if not zip_file.infolist():
            print('Error: ZIP 파일이 비어있습니다.')
            return
        test_file = zip_file.infolist()[0]
    except FileNotFoundError:
        print(f'Error: {zip_filename} 파일을 찾을 수 없습니다.')
        return
    except zipfile.BadZipFile:
        print(f'Error: {zip_filename} 파일이 손상되었거나 ZIP 형식이 아닙니다.')
        return
    except Exception as e:
        print(f'Error: 파일을 여는 중 알 수 없는 오류가 발생했습니다. ({e})')
        return

    start_time = time.time()
    start_datetime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'해킹 시작 시간: {start_datetime}')
    
    # 1단계: 화성 및 생존 관련 6자리 우선순위 단어장(Dictionary) 생성
    priority_passwords = []
    
    # 6자리 완전한 단어들
    priority_passwords.extend(['coffee', 'oxygen', 'planet', 'rocket', 'apollo', 'system', 'rescue', 'secret'])
    
    # 4자리 단어 + 2자리 숫자 (예: mars00 ~ mars99)
    for base_word in ['mars', 'ares', 'base', 'crew', 'star', 'dust', 'java', 'cafe', 'food']:
        for i in range(100):
            priority_passwords.append(f'{base_word}{i:02d}')
            
    # 5자리 단어 + 1자리 숫자 (예: earth0 ~ earth9)
    for base_word in ['space', 'earth', 'water', 'alien']:
        for i in range(10):
            priority_passwords.append(f'{base_word}{i}')

    iteration = 0
    found_password = None

    print(f'1단계: 화성 기지 관련 패턴 {len(priority_passwords)}개 우선 탐색을 시작합니다...\n')
    
    for guess in priority_passwords:
        iteration += 1
        try:
            zip_file.read(test_file, pwd=guess.encode('utf-8'))
            found_password = guess
            print(f'>>> 1단계 우선 탐색에서 암호를 찾았습니다!')
            break
        except (RuntimeError, zlib.error, zipfile.BadZipFile):
            pass
        except Exception:
            pass

    # 2단계: 1단계에서 못 찾았을 경우 전체 무차별 대입 공격 실행
    if not found_password:
        print('1단계 우선 탐색 실패. 2단계: 전체 무차별 대입(Brute-force) 공격으로 전환합니다...\n')
        chars = string.ascii_lowercase + string.digits
        password_length = 6
        
        for guess_tuple in itertools.product(chars, repeat=password_length):
            iteration += 1
            guess = ''.join(guess_tuple)
            
            if iteration % 100000 == 0:
                elapsed = time.time() - start_time
                print(f'반복 횟수: {iteration}, 현재 시도: {guess}, 진행 시간: {elapsed:.2f}초')

            try:
                zip_file.read(test_file, pwd=guess.encode('utf-8'))
                found_password = guess
                break
            except (RuntimeError, zlib.error, zipfile.BadZipFile):
                pass
            except Exception:
                pass

    total_elapsed = time.time() - start_time

    if found_password:
        print(f'\n해킹 성공! 암호를 찾았습니다: {found_password}')
        print(f'총 반복 횟수: {iteration}')
        print(f'총 소요 시간: {total_elapsed:.2f}초')
        
        try:
            with open(output_filename, 'w') as f:
                f.write(found_password)
            print(f'암호가 {output_filename}에 안전하게 저장되었습니다.')
        except IOError:
            print(f'Error: {output_filename} 파일을 저장하는 데 실패했습니다.')
    else:
        print('\n해킹 실패: 모든 조합을 시도했지만 암호를 찾지 못했습니다.')
        print(f'총 소요 시간: {total_elapsed:.2f}초')

if __name__ == '__main__':
    unlock_zip()
