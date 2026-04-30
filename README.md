# Kinect Depth Camera Validation

Windows에서 Azure Kinect Developer Kit의 depth camera 값을 Azure Kinect Sensor SDK `k4a.dll` C API로 직접 획득하고, 실시간 preview, colorbar range 검증, uint8 PNG capture 저장을 수행하는 최소 검증 프로젝트입니다.

주요 기준:

- Azure Kinect Sensor SDK: https://github.com/microsoft/Azure-Kinect-Sensor-SDK
- Python wrapper 없이 `ctypes`로 `k4a.dll` 직접 호출

## Requirements

- Windows
- Azure Kinect DK
- Azure Kinect Sensor SDK v1.4.2
- Python 3.x

기본 SDK bin 경로:

```text
C:\Program Files\Azure Kinect SDK v1.4.2\sdk\windows-desktop\amd64\release\bin
```

SDK를 다른 위치에 설치했다면 실행 전에 환경 변수로 지정할 수 있습니다.

```powershell
$env:AZURE_KINECT_SDK_BIN_PATH="C:\Program Files\Azure Kinect SDK v1.4.2\sdk\windows-desktop\amd64\release\bin"
python main.py
```

## Hardware Setup

1. Azure Kinect DK 전원 어댑터를 연결합니다.
2. USB-C 케이블을 Azure Kinect DK에 연결합니다.
3. USB-A 케이블을 PC 본체의 USB 3.0 포트에 직접 연결합니다.
4. USB 허브나 모니터 내장 USB 포트는 사용하지 않는 것을 권장합니다.

## SDK Test

Python 실행 전 `k4aviewer.exe`로 장치가 정상 동작하는지 확인하세요.

```text
C:\Program Files\Azure Kinect SDK v1.4.2\tools\k4aviewer.exe
```

`k4aviewer.exe`에서도 장치가 보이지 않으면 Python 코드 문제가 아니라 USB 연결, 전원, 권한, 드라이버, SDK 설치 문제일 가능성이 큽니다.

## Install

가상환경 사용을 권장합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

실행 시 Windows 카메라 개인정보 설정 화면이 열립니다. `Camera access`와 `Let desktop apps access your camera`가 꺼져 있다면 켠 뒤 다시 실행하세요.

## Camera Configuration

현재 설정:

- color camera: off
- depth mode: `NFOV_UNBINNED`
- fps: `FPS_30`
- depth image source: raw `k4a_capture_get_depth_image`
- minimum resolvable depth for colormap: `250 mm`

Azure Kinect depth image 값은 millimeter 단위입니다. 중심 픽셀 depth 값이 `0`이면 invalid depth로 처리합니다.

## Preview Controls

Preview 상단에는 현재 camera configuration과 colormap range가 표시됩니다. Preview 오른쪽에는 현재 min-max range에 대응되는 colorbar가 표시됩니다.

키보드:

- `ESC`: 안전하게 종료
- `m`: auto range/manual range 토글
- `s`: 현재 depth frame을 PNG로 저장

`Kinect Depth Camera Validation Controls` 창:

- `Auto range`: auto/manual range 토글
- `Min mm`, `Max mm`: manual range를 정수로 직접 입력
- `Apply Range`: 입력한 min/max range 적용
- `Save PNG`: 현재 depth frame 저장

`Min mm`, `Max mm` 입력칸을 클릭한 뒤 숫자를 입력하고 Enter를 누르면 range가 적용됩니다. 직접 입력 range를 적용하면 manual mode로 전환됩니다.

현재 설정의 최소 resolvable depth는 `250 mm`로 사용합니다. Auto/manual 모드 모두에서 colormap min 값은 `250 mm` 아래로 내려가지 않습니다.

## Capture Output

`s` 키 또는 `Save PNG` 버튼을 누르면 현재 depth frame을 `captures` 폴더에 PNG로 저장합니다.

저장 이미지는 선택된 min-max range를 기준으로 `0-255` 범위로 scaling한 단일 채널 `uint8` 이미지입니다. invalid depth 값인 `0`은 저장 이미지에서도 `0`으로 유지됩니다.

파일명에는 저장 날짜와 min-max range가 포함됩니다.

```text
captures\depth_YYYYMMDD_HHMMSS_min250mm_max4000mm.png
```

## Build Windows Executable

Windows 실행 파일을 만들려면 PyInstaller 빌드 스크립트를 사용하세요.

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

`python` 명령이 PATH에 없다면 Python 경로를 직접 지정할 수 있습니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1 -PythonExe "C:\Users\<user>\anaconda3\python.exe"
```

빌드 결과:

```text
dist\KinectDepthCameraValidation\KinectDepthCameraValidation.exe
```

이 exe 폴더는 Python 설치 없이 실행할 수 있습니다. 단, 대상 PC에는 Azure Kinect Sensor SDK v1.4.2가 설치되어 있어야 하며, 기본 SDK bin 경로 또는 `AZURE_KINECT_SDK_BIN_PATH` 환경 변수가 올바르게 설정되어 있어야 합니다.

## Troubleshooting

### SDK 경로 오류

다음 경로가 존재하는지 확인하세요.

```text
C:\Program Files\Azure Kinect SDK v1.4.2\sdk\windows-desktop\amd64\release\bin
```

다른 위치에 설치했다면 `AZURE_KINECT_SDK_BIN_PATH` 환경 변수를 사용하세요.

### DLL 오류

- Azure Kinect Sensor SDK v1.4.2가 설치되어 있는지 확인하세요.
- `SDK_BIN_PATH`가 실제 SDK bin 폴더와 일치하는지 확인하세요.
- 새 터미널에서 다시 실행하세요.

### `E_ACCESSDENIED` 또는 Media Foundation camera access 오류

Windows 카메라 개인정보 보호 설정에 막힌 상태일 수 있습니다.

1. Windows 설정을 엽니다.
2. `Privacy & security > Camera`로 이동합니다.
3. `Camera access`를 켭니다.
4. `Let desktop apps access your camera`를 켭니다.
5. `k4aviewer.exe`, Teams, Zoom 등 카메라를 사용할 수 있는 프로그램을 모두 종료한 뒤 다시 실행합니다.

Depth만 사용하는 설정이어도 Azure Kinect SDK가 장치를 열 때 Media Foundation을 통해 color camera 장치 접근 권한을 확인할 수 있습니다.

### depth 값이 0으로 나오는 경우

depth 값 `0`은 invalid depth입니다.

- 중심 픽셀 위치에 측정 가능한 물체가 없음
- 물체가 너무 가깝거나 너무 멂
- 반사율이 낮거나 반사가 심한 표면
- depth camera 앞이 가려져 있음
