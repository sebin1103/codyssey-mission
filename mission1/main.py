def analyze_mission_log():
    print('Hello Mars')
    
    file_path = 'mission_computer_main.log'
    report_file = 'error.log'
    # 수행과제 
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

            # 수행과제: 전체 내용을 화면에 출력
            print('\n 전체 내용 출력')
            for line in lines:
                print(line.strip())

            # 수행과제 : 출력 결과를 시간의 역순으로 정렬
            print('\n 역순으로 정렬')
            for line in reversed(lines) :
                print(line.strip())

            # 수행과제 : 문제가 되는 부분만 따로 파일로 저장
            with open(report_file, 'w', encoding='utf-8') as out_file:
                for line in lines:
                    if 'unstable' in line or 'explosion' in line:
                        out_file.write(line)
            
            print('\n[알림] 사고 관련 로그가 저장되었습니다.')

    except FileNotFoundError:
        print('mission_computer_main.log 파일을 찾을 수 없습니다.')
    except Exception as e:
        print(f'오류 발생: {e}')

if __name__ == '__main__':
    analyze_mission_log()
