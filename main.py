import os
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np


PROJECT_NAME = "Kinect Depth Camera Validation"
DEFAULT_SDK_BIN_PATH = (
    r"C:\Program Files\Azure Kinect SDK v1.4.2"
    r"\sdk\windows-desktop\amd64\release\bin"
)
SDK_BIN_PATH = os.environ.get("AZURE_KINECT_SDK_BIN_PATH", DEFAULT_SDK_BIN_PATH)
CAMERA_PRIVACY_SETTINGS_URI = "ms-settings:privacy-webcam"
PREVIEW_WINDOW_NAME = PROJECT_NAME
CONTROL_WINDOW_NAME = f"{PROJECT_NAME} Controls"
CAPTURE_DIR = Path("captures")
MANUAL_RANGE_MAX_MM = 10000
MIN_RESOLVABLE_DEPTH_MM = 250
DEFAULT_MANUAL_MIN_MM = MIN_RESOLVABLE_DEPTH_MM
DEFAULT_MANUAL_MAX_MM = 4000
DEPTH_MODE_LABEL = "NFOV_UNBINNED"
FPS_LABEL = "30 FPS"
COLOR_MODE_LABEL = "Color OFF"
CAMERA_CONFIG_LABEL = (
    f"Depth: {DEPTH_MODE_LABEL} | FPS: {FPS_LABEL} | {COLOR_MODE_LABEL} | "
    f"Min resolvable depth: {MIN_RESOLVABLE_DEPTH_MM} mm"
)


def ensure_sdk_path() -> None:
    if not os.path.isdir(SDK_BIN_PATH):
        print(
            "ERROR: Azure Kinect Sensor SDK bin path was not found.\n"
            f"Expected path: {SDK_BIN_PATH}\n"
            "Install Azure Kinect Sensor SDK v1.4.2, update SDK_BIN_PATH in main.py, "
            "or set AZURE_KINECT_SDK_BIN_PATH to your SDK bin directory.",
            file=sys.stderr,
        )
        sys.exit(1)

    os.environ.setdefault("K4A_DLL_DIR", SDK_BIN_PATH)
    os.environ.setdefault("CONDA_DLL_SEARCH_MODIFICATION_ENABLE", "1")
    os.add_dll_directory(SDK_BIN_PATH)


def request_windows_camera_access() -> None:
    if os.name != "nt":
        return

    print(
        "Opening Windows camera privacy settings. Enable Camera access and "
        "Let desktop apps access your camera if they are disabled.",
        file=sys.stderr,
        flush=True,
    )
    open_windows_camera_privacy_settings()


def open_windows_camera_privacy_settings() -> None:
    if os.name != "nt":
        return

    try:
        os.startfile(CAMERA_PRIVACY_SETTINGS_URI)
    except OSError as exc:
        print(
            f"Could not open Windows camera privacy settings automatically: {exc}",
            file=sys.stderr,
            flush=True,
        )


def print_device_start_help() -> None:
    print(
        "\nERROR: Failed to open or start Azure Kinect DK.\n"
        "Common checks:\n"
        "- Windows Settings > Privacy & security > Camera: enable camera access.\n"
        "- Enable camera access for desktop apps.\n"
        "- Close k4aviewer.exe, Teams, Zoom, or any app that may be using the camera.\n"
        "- Connect Azure Kinect DK directly to a USB 3.0 port without a USB hub.\n"
        "- Confirm the device works in k4aviewer.exe first.",
        file=sys.stderr,
    )


class RangeControls:
    def __init__(self) -> None:
        self.save_requested = False
        self.auto_range = True
        self.manual_min_mm = DEFAULT_MANUAL_MIN_MM
        self.manual_max_mm = DEFAULT_MANUAL_MAX_MM
        self.min_text = str(DEFAULT_MANUAL_MIN_MM)
        self.max_text = str(DEFAULT_MANUAL_MAX_MM)
        self.active_field = None
        self.status = "Ready"
        self.regions = {}

        cv2.namedWindow(CONTROL_WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(CONTROL_WINDOW_NAME, 460, 260)
        cv2.setMouseCallback(CONTROL_WINDOW_NAME, self.on_mouse)

    def sync_from_state(self) -> None:
        if self.active_field != "min" and self.min_text != str(self.manual_min_mm):
            self.min_text = str(self.manual_min_mm)
        if self.active_field != "max" and self.max_text != str(self.manual_max_mm):
            self.max_text = str(self.manual_max_mm)

    def apply_manual_range(self) -> None:
        try:
            min_mm = int(self.min_text)
            max_mm = int(self.max_text)
        except ValueError:
            self.set_status("Min/max must be integers")
            return

        min_mm = max(MIN_RESOLVABLE_DEPTH_MM, min(min_mm, MANUAL_RANGE_MAX_MM))
        max_mm = max(0, min(max_mm, MANUAL_RANGE_MAX_MM))

        if max_mm <= min_mm:
            self.set_status("Max must be greater than min")
            return

        self.auto_range = False
        self.manual_min_mm = min_mm
        self.manual_max_mm = max_mm
        self.min_text = str(min_mm)
        self.max_text = str(max_mm)
        self.active_field = None
        self.set_status(f"Manual range applied: {min_mm}-{max_mm} mm")

    def toggle_auto_range(self) -> None:
        self.auto_range = not self.auto_range
        self.set_status("Auto range enabled" if self.auto_range else "Manual range enabled")

    def get_range(self, depth_image: np.ndarray) -> tuple[int, int]:
        return get_display_range(depth_image, self.auto_range, self.manual_min_mm, self.manual_max_mm)

    def request_save(self) -> None:
        self.save_requested = True
        self.set_status("Save requested")

    def consume_save_request(self) -> bool:
        if not self.save_requested:
            return False
        self.save_requested = False
        return True

    def set_status(self, message: str) -> None:
        self.status = message
        print(message)

    def update(self) -> None:
        panel = np.full((260, 460, 3), 36, dtype=np.uint8)
        cv2.putText(
            panel,
            "Depth Controls",
            (16, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.82,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        self.regions = {
            "auto": (18, 54, 214, 92),
            "min": (136, 108, 282, 146),
            "max": (136, 154, 282, 192),
            "apply": (306, 108, 438, 146),
            "save": (306, 154, 438, 192),
        }

        self.draw_button(panel, "auto", "Auto: ON" if self.auto_range else "Auto: OFF")
        self.draw_label(panel, "Min mm", (18, 134))
        self.draw_label(panel, "Max mm", (18, 180))
        self.draw_input(panel, "min", self.min_text)
        self.draw_input(panel, "max", self.max_text)
        self.draw_button(panel, "apply", "Apply Range")
        self.draw_button(panel, "save", "Save PNG")

        cv2.putText(
            panel,
            self.status[:54],
            (18, 232),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (210, 230, 255),
            1,
            cv2.LINE_AA,
        )

        cv2.imshow(CONTROL_WINDOW_NAME, panel)

    def draw_label(self, panel: np.ndarray, text: str, origin: tuple[int, int]) -> None:
        cv2.putText(panel, text, origin, cv2.FONT_HERSHEY_SIMPLEX, 0.58, (230, 230, 230), 1, cv2.LINE_AA)

    def draw_button(self, panel: np.ndarray, region_key: str, text: str) -> None:
        x1, y1, x2, y2 = self.regions[region_key]
        color = (86, 125, 170) if region_key != "save" else (72, 145, 102)
        cv2.rectangle(panel, (x1, y1), (x2, y2), color, -1)
        cv2.rectangle(panel, (x1, y1), (x2, y2), (210, 220, 230), 1)
        cv2.putText(panel, text, (x1 + 10, y1 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)

    def draw_input(self, panel: np.ndarray, region_key: str, text: str) -> None:
        x1, y1, x2, y2 = self.regions[region_key]
        border = (80, 190, 255) if self.active_field == region_key else (160, 170, 180)
        cv2.rectangle(panel, (x1, y1), (x2, y2), (245, 245, 245), -1)
        cv2.rectangle(panel, (x1, y1), (x2, y2), border, 2)
        cursor = "|" if self.active_field == region_key else ""
        cv2.putText(panel, f"{text}{cursor}", (x1 + 10, y1 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (20, 20, 20), 1, cv2.LINE_AA)

    def on_mouse(self, event: int, x: int, y: int, _flags: int, _param) -> None:
        if event != cv2.EVENT_LBUTTONDOWN:
            return

        clicked = None
        for key, (x1, y1, x2, y2) in self.regions.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                clicked = key
                break

        if clicked == "auto":
            self.toggle_auto_range()
            self.active_field = None
        elif clicked in ("min", "max"):
            self.active_field = clicked
        elif clicked == "apply":
            self.apply_manual_range()
        elif clicked == "save":
            self.request_save()
            self.active_field = None
        else:
            self.active_field = None

    def handle_key(self, key: int) -> bool:
        if self.active_field not in ("min", "max") or key == 255:
            return False

        if key in (13, 10):
            self.apply_manual_range()
            return True

        if key in (8, 127):
            if self.active_field == "min":
                self.min_text = self.min_text[:-1]
            else:
                self.max_text = self.max_text[:-1]
            return True

        if ord("0") <= key <= ord("9"):
            if self.active_field == "min":
                self.min_text = (self.min_text + chr(key))[:5]
            else:
                self.max_text = (self.max_text + chr(key))[:5]
            return True

        return False

    def close(self) -> None:
        cv2.destroyWindow(CONTROL_WINDOW_NAME)


def create_range_controls() -> RangeControls:
    return RangeControls()


def get_display_range(
    depth_image: np.ndarray,
    auto_range: bool,
    manual_min_mm: int,
    manual_max_mm: int,
) -> tuple[int, int]:
    if auto_range:
        valid_depth = depth_image[depth_image >= MIN_RESOLVABLE_DEPTH_MM]
        if valid_depth.size > 0:
            min_mm = max(MIN_RESOLVABLE_DEPTH_MM, int(valid_depth.min()))
            max_mm = int(valid_depth.max())
            if min_mm < max_mm:
                return min_mm, max_mm

    min_mm = max(MIN_RESOLVABLE_DEPTH_MM, manual_min_mm)
    max_mm = min(MANUAL_RANGE_MAX_MM, manual_max_mm)

    if max_mm <= min_mm:
        max_mm = min(min_mm + 1, MANUAL_RANGE_MAX_MM)
        min_mm = max(MIN_RESOLVABLE_DEPTH_MM, max_mm - 1)

    return min_mm, max_mm


def scale_depth_to_uint8(depth_image: np.ndarray, min_mm: int, max_mm: int) -> np.ndarray:
    range_mm = max(max_mm - min_mm, 1)
    clipped = np.clip(depth_image, min_mm, max_mm).astype(np.float32)
    scaled = ((clipped - min_mm) * 255.0 / range_mm).astype(np.uint8)
    scaled[depth_image == 0] = 0
    return scaled


def create_colorbar(height: int, min_mm: int, max_mm: int) -> np.ndarray:
    bar_width = 48
    label_width = 150
    gradient = np.linspace(255, 0, height, dtype=np.uint8).reshape(height, 1)
    gradient = np.repeat(gradient, bar_width, axis=1)
    colorbar = cv2.applyColorMap(gradient, cv2.COLORMAP_JET)

    label_panel = np.full((height, label_width, 3), 32, dtype=np.uint8)
    panel = np.hstack((colorbar, label_panel))

    cv2.putText(
        panel,
        f"{max_mm} mm",
        (bar_width + 8, 24),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        panel,
        f"{min_mm} mm",
        (bar_width + 8, height - 12),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    return panel


def build_preview(depth_image: np.ndarray, min_mm: int, max_mm: int, auto_range: bool) -> np.ndarray:
    depth_scaled = scale_depth_to_uint8(depth_image, min_mm, max_mm)
    depth_display = cv2.applyColorMap(depth_scaled, cv2.COLORMAP_JET)
    depth_display[depth_image == 0] = (0, 0, 0)

    height, width = depth_image.shape[:2]
    center_x = width // 2
    center_y = height // 2
    mode_text = "AUTO" if auto_range else "MANUAL"

    cv2.circle(depth_display, (center_x, center_y), 4, (255, 255, 255), -1)
    cv2.putText(
        depth_display,
        CAMERA_CONFIG_LABEL,
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (0, 0, 0),
        3,
        cv2.LINE_AA,
    )
    cv2.putText(
        depth_display,
        CAMERA_CONFIG_LABEL,
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        depth_display,
        f"{mode_text} colormap range: {min_mm}-{max_mm} mm",
        (12, 56),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (0, 0, 0),
        3,
        cv2.LINE_AA,
    )
    cv2.putText(
        depth_display,
        f"{mode_text} colormap range: {min_mm}-{max_mm} mm",
        (12, 56),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )

    colorbar = create_colorbar(height, min_mm, max_mm)
    return np.hstack((depth_display, colorbar))


def save_depth_capture(depth_image: np.ndarray, min_mm: int, max_mm: int) -> Path:
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"depth_{timestamp}_min{min_mm}mm_max{max_mm}mm.png"
    output_path = CAPTURE_DIR / filename
    depth_uint8 = scale_depth_to_uint8(depth_image, min_mm, max_mm)

    if not cv2.imwrite(str(output_path), depth_uint8):
        raise RuntimeError(f"Failed to save capture: {output_path}")

    return output_path


def main() -> None:
    ensure_sdk_path()
    request_windows_camera_access()

    import pyk4a
    from pyk4a import Config, PyK4A
    from pyk4a.errors import K4AException

    k4a = PyK4A(
        Config(
            color_resolution=pyk4a.ColorResolution.OFF,
            depth_mode=pyk4a.DepthMode.NFOV_UNBINNED,
            camera_fps=pyk4a.FPS.FPS_30,
            synchronized_images_only=False,
        )
    )
    started = False
    controls = create_range_controls()

    try:
        try:
            k4a.start()
            started = True
        except K4AException:
            print_device_start_help()
            open_windows_camera_privacy_settings()
            sys.exit(1)

        while True:
            controls.update()
            controls.sync_from_state()

            capture = k4a.get_capture()
            depth_image = capture.depth

            if depth_image is None:
                continue

            depth_image = np.asarray(depth_image)
            height, width = depth_image.shape[:2]
            center_x = width // 2
            center_y = height // 2
            auto_range = controls.auto_range
            min_mm, max_mm = controls.get_range(depth_image)

            # Azure Kinect depth image values are measured in millimeters (mm).
            center_depth_mm = int(depth_image[center_y, center_x])

            if center_depth_mm == 0:
                print("Center depth: invalid depth")
            else:
                print(f"Center depth: {center_depth_mm} mm")

            depth_display = build_preview(depth_image, min_mm, max_mm, auto_range)
            cv2.imshow(PREVIEW_WINDOW_NAME, depth_display)

            key = cv2.waitKey(1) & 0xFF
            if controls.handle_key(key):
                continue
            if key == 27:
                break
            if key == ord("m"):
                controls.toggle_auto_range()
            if key == ord("s"):
                output_path = save_depth_capture(depth_image, min_mm, max_mm)
                controls.set_status(f"Saved capture: {output_path}")
            if controls.consume_save_request():
                output_path = save_depth_capture(depth_image, min_mm, max_mm)
                controls.set_status(f"Saved capture: {output_path}")

    finally:
        if started:
            k4a.stop()
        controls.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
