import time
import json
import random
import platform
import psutil


class DummySensor:
    """화성 기지의 환경 데이터를 생성하는 더미 센서 클래스"""

    def get_data(self):
        """센서로부터 무작위 환경 데이터를 가져옵니다."""
        return {
            'mars_base_internal_temperature': round(random.uniform(18.0, 24.0), 2),
            'mars_base_external_temperature': round(random.uniform(-120.0, -20.0), 2),
            'mars_base_internal_humidity': round(random.uniform(30.0, 50.0), 2),
            'mars_base_external_illuminance': round(random.uniform(0.0, 1000.0), 2),
            'mars_base_internal_co2': round(random.uniform(400.0, 1000.0), 2),
            'mars_base_internal_oxygen': round(random.uniform(19.0, 21.0), 2)
        }


class MissionComputer:
    """화성 기지의 환경 데이터를 관리하고 시스템 상태를 모니터링하는 클래스"""

    def __init__(self):
        self.env_values = {
            'mars_base_internal_temperature': 0.0,
            'mars_base_external_temperature': 0.0,
            'mars_base_internal_humidity': 0.0,
            'mars_base_external_illuminance': 0.0,
            'mars_base_internal_co2': 0.0,
            'mars_base_internal_oxygen': 0.0
        }
        self.ds = DummySensor()
        self.history = []
        self.start_time = time.time()

    def _read_settings(self):
        """보너스 과제: setting.txt 파일에서 출력할 항목을 읽어옵니다."""
        try:
            with open('setting.txt', 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f'설정 파일 오류: {e}')
            return []

    def _filter_data(self, data, settings):
        """가져온 데이터 중 setting.txt에 명시된 항목만 필터링합니다."""
        if not settings:
            return data
        
        filtered = {}
        for key in settings:
            if key in data:
                filtered[key] = data[key]
        return filtered

    def get_mission_computer_info(self):
        """미션 컴퓨터의 시스템 정보를 가져옵니다."""
        try:
            mem_size_gb = psutil.virtual_memory().total / (1024 ** 3)
            
            system_info = {
                'os': platform.system(),
                'os_version': platform.version(),
                'cpu_type': platform.processor() or platform.machine(),
                'cpu_cores': psutil.cpu_count(logical=False),
                'memory_size_gb': round(mem_size_gb, 2)
            }
            
            settings = self._read_settings()
            filtered_info = self._filter_data(system_info, settings)
            
            return json.dumps(filtered_info, indent=4, ensure_ascii=False)
            
        except Exception as e:
            error_data = {'error': f'시스템 정보 수집 실패: {e}'}
            return json.dumps(error_data, ensure_ascii=False)

    def get_mission_computer_load(self):
        """미션 컴퓨터의 실시간 부하 정보를 가져옵니다."""
        try:
            load_info = {
                'cpu_usage_percent': psutil.cpu_percent(interval=1.0),
                'memory_usage_percent': psutil.virtual_memory().percent
            }
            
            settings = self._read_settings()
            filtered_load = self._filter_data(load_info, settings)
            
            return json.dumps(filtered_load, indent=4, ensure_ascii=False)
            
        except Exception as e:
            error_data = {'error': f'시스템 부하 수집 실패: {e}'}
            return json.dumps(error_data, ensure_ascii=False)

    def get_sensor_data(self):
        """Task 7: 5초마다 센서 데이터를 수집하고 5분마다 평균을 출력합니다."""
        print('\n--- Mars Mission Control System Started ---')
        
        try:
            while True:
                new_data = self.ds.get_data()
                self.env_values.update(new_data)
                self.history.append(new_data)

                json_output = json.dumps(self.env_values, indent=4)
                print(f'\n[Current Environment Data]\n{json_output}')

                current_time = time.time()
                if current_time - self.start_time >= 300:
                    self._display_average_values()
                    self.start_time = current_time
                    self.history = []

                time.sleep(5)

        except KeyboardInterrupt:
            print('\nSystem stopped....')

    def _display_average_values(self):
        """저장된 히스토리를 바탕으로 5분 평균값을 출력합니다."""
        if not self.history:
            return

        keys = self.env_values.keys()
        averages = {}

        for key in keys:
            total = sum(data[key] for data in self.history)
            averages[key] = round(total / len(self.history), 2)

        print('\n' + '=' * 40)
        print('[5-Minute Average Environment Report]')
        print(json.dumps(averages, indent=4))
        print('=' * 40)


if __name__ == '__main__':
    # 1. MissionComputer 클래스를 runComputer 라는 이름으로 인스턴스화
    runComputer = MissionComputer()
    
    # 2. get_mission_computer_info(), get_mission_computer_load() 호출 및 출력 확인
    print('=== 시스템 정보 ===')
    print(runComputer.get_mission_computer_info())
    
    print('\n=== 시스템 부하 ===')
    print(runComputer.get_mission_computer_load())
    
    # 3. 기존의 환경 데이터 수집 로직 실행
    runComputer.get_sensor_data()
