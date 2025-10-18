import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import threading
import time
from comtypes import CoInitialize
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, EDataFlow, ERole
from comtypes import CLSCTX_ALL
import win32com.client
from pycaw.pycaw import IMMDeviceEnumerator, IMMDevice
from comtypes import GUID
import webbrowser
import traceback
from comtypes import CoCreateInstance
from ctypes import POINTER, c_wchar_p
from comtypes import IUnknown

#debug log
import logging
from logging.handlers import TimedRotatingFileHandler

def setup_logger():
    log_dir = os.path.join(os.getenv("APPDATA"), "VolumeSetter", "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_path = os.path.join(log_dir, "debug.log")

    handler = TimedRotatingFileHandler(
        filename=log_path,
        when="midnight",       # Tạo file mới mỗi ngày lúc 00:00
        interval=1,
        backupCount=7,         # Giữ lại 7 ngày log gần nhất
        encoding="utf-8",
        utc=False              # Dùng giờ địa phương
    )

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    # Nếu muốn ghi log ra console khi chạy bằng .py
    # logger.addHandler(logging.StreamHandler())

    logging.debug("Logger theo ngày đã được khởi tạo")





CONFIG_FILE = "volume_config.json"

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        resolved_path = os.path.join(sys._MEIPASS, relative_path)
        logging.debug(f"resource_path: Đang chạy trong môi trường PyInstaller, trả về đường dẫn: {resolved_path}")
        return resolved_path
    else:
        resolved_path = os.path.join(os.path.dirname(__file__), relative_path)
        logging.debug(f"resource_path: Đang chạy từ mã nguồn, trả về đường dẫn: {resolved_path}")
        return resolved_path

def get_config_path():
    appdata_dir = os.path.join(os.getenv("APPDATA"), "VolumeSetter")
    os.makedirs(appdata_dir, exist_ok=True)
    config_path = os.path.join(appdata_dir, CONFIG_FILE)
    logging.debug(f"get_config_path: Đường dẫn file cấu hình tại: {config_path}")
    return config_path
# === Tải cấu hình âm lượng ===
def load_volume_config():
    config_path = get_config_path()
    logging.debug(f"Đang đọc cấu hình từ: {config_path}")

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                logging.debug(f"Nội dung cấu hình: {data}")
                return data
        except Exception as e:
            logging.error(f"Lỗi đọc file cấu hình: {e}")
    else:
        logging.warning("Không tìm thấy file cấu hình")

    # Nếu chưa có, sao chép từ _MEIPASS
    try:
        bundled = resource_path(CONFIG_FILE)
        with open(bundled, "r", encoding="utf-8") as f:
            data = json.load(f)
        with open(config_path, "w", encoding="utf-8") as out:
            json.dump(data, out, indent=4)
        logging.info("Đã sao chép cấu hình mặc định từ _MEIPASS")
        return data
    except Exception as e:
        logging.error(f"Lỗi sao chép file cấu hình mặc định: {e}")
        return {}

# === Lưu cấu hình âm lượng ===
def save_config(device_name, volume_level, context="default"):
    try:
        config_path = get_config_path()
        logging.debug(f"save_config: Đường dẫn cấu hình: {config_path}")

        config = load_volume_config()
        logging.debug(f"save_config: Cấu hình hiện tại trước khi cập nhật: {config}")

        if device_name not in config:
            config[device_name] = {}
            logging.debug(f"save_config: Thêm thiết bị mới: {device_name}")

        config[device_name][context] = volume_level
        logging.debug(f"save_config: Đặt âm lượng {volume_level} cho thiết bị '{device_name}' trong ngữ cảnh '{context}'")

        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)

        logging.info(f"save_config: Đã lưu cấu hình thành công cho thiết bị '{device_name}'")
        return True

    except Exception as e:
        logging.error(f"save_config: Lỗi khi lưu cấu hình: {e}")
        return False


# === Lấy tên thiết bị mặc định ===
def get_default_device_name():
    try:
        logging.debug("get_default_device_name: Bắt đầu lấy thiết bị mặc định")

        speakers = AudioUtilities.GetSpeakers()
        speaker_id = speakers.GetId()
        logging.debug(f"get_default_device_name: ID thiết bị loa mặc định: {speaker_id}")

        devices = AudioUtilities.GetAllDevices()
        for device in devices:
            logging.debug(f"get_default_device_name: Kiểm tra thiết bị: {device.FriendlyName} (ID: {device.id})")
            if device.id == speaker_id:
                logging.info(f"get_default_device_name: Thiết bị mặc định là: {device.FriendlyName}")
                return device.FriendlyName

        logging.warning("get_default_device_name: Không tìm thấy thiết bị phù hợp với ID loa mặc định")
        return "Unknown Device"

    except Exception as e:
        logging.error(f"get_default_device_name: Lỗi khi lấy tên thiết bị: {e}")
        logging.debug(traceback.format_exc())
        return None

# === Lấy danh sách thiết bị đang hoạt động ===
def get_audio_devices():
    try:
        logging.debug("get_audio_devices: Bắt đầu lấy danh sách thiết bị âm thanh")

        devices = AudioUtilities.GetAllDevices()
        active_devices = [d.FriendlyName for d in devices if d.state == 1]

        logging.info(f"get_audio_devices: Tìm thấy {len(active_devices)} thiết bị đang hoạt động")
        for name in active_devices:
            logging.debug(f"get_audio_devices: Thiết bị hoạt động: {name}")

        return active_devices

    except Exception as e:
        logging.error(f"get_audio_devices: Lỗi khi lấy danh sách thiết bị: {e}")
        return []

# === Đặt thiết bị âm thanh mặc định ===
def set_default_audio_device(device_name):
    try:
        logging.debug(f"set_default_audio_device: Bắt đầu chuyển sang thiết bị '{device_name}'")

        devices = AudioUtilities.GetAllDevices()
        target_device = None

        for device in devices:
            logging.debug(f"set_default_audio_device: Kiểm tra thiết bị: {device.FriendlyName}")
            if device.FriendlyName == device_name:
                target_device = device
                break

        if not target_device:
            logging.warning(f"set_default_audio_device: Không tìm thấy thiết bị: {device_name}")
            return False

        logging.info(f"set_default_audio_device: Đã tìm thấy thiết bị: {target_device.FriendlyName} (ID: {target_device.id})")

        # CLSID cho PolicyConfig
        CLSID_PolicyConfig = GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}")

        class IPolicyConfig(IUnknown):
            _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
            _methods_ = [
                ("GetMixFormat", []),
                ("GetDeviceFormat", []),
                ("ResetDeviceFormat", []),
                ("SetDeviceFormat", []),
                ("GetProcessingPeriod", []),
                ("SetProcessingPeriod", []),
                ("GetShareMode", []),
                ("SetShareMode", []),
                ("GetPropertyValue", []),
                ("SetPropertyValue", []),
                ("SetDefaultEndpoint", [c_wchar_p, c_wchar_p])
            ]

        try:
            policy_config = CoCreateInstance(CLSID_PolicyConfig, IPolicyConfig, CLSCTX_ALL)
            policy_config.SetDefaultEndpoint(target_device.id, "0")  # Console
            policy_config.SetDefaultEndpoint(target_device.id, "1")  # Multimedia

            logging.info(f"set_default_audio_device: Đã chuyển mặc định sang thiết bị: {device_name}")
            return True

        except Exception as e:
            logging.error(f"set_default_audio_device: Lỗi khi dùng PolicyConfig: {e}")
            logging.debug(traceback.format_exc())
            return False

    except Exception as e:
        logging.error(f"set_default_audio_device: Lỗi khi đặt thiết bị mặc định: {e}")
        logging.debug(traceback.format_exc())
        return False


# Thông báo thay đổi thiết bị
from plyer import notification

def show_device_change_notification(device_name, volume_level):
    notification.notify(
        title="Thiết bị âm thanh đã thay đổi",
        message=f"Đã chuyển sang: {device_name}\nÁp dụng âm lượng: {int(volume_level * 100)}%",
        app_name="VolumeSetter",
        timeout=5  # thời gian hiển thị (giây)
    )


# === Đặt âm lượng cho thiết bị mặc định ===
def set_volume(level):
    try:
        logging.debug(f"set_volume: Bắt đầu đặt âm lượng ở mức {level}")

        device = AudioUtilities.GetSpeakers()
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = interface.QueryInterface(IAudioEndpointVolume)
        volume.SetMasterVolumeLevelScalar(level, None)

        logging.info(f"set_volume: Đã đặt âm lượng thành công ở mức {level}")
        return True

    except Exception as e:
        logging.error(f"set_volume: Lỗi khi đặt âm lượng: {e}")
        return False


# === Áp dụng âm lượng từ giao diện ===
import logging

def apply_volume():
    device = device_var.get()
    if not device:
        logging.warning("apply_volume: Người dùng chưa chọn thiết bị âm thanh")
        messagebox.showerror("Lỗi", "Vui lòng chọn thiết bị âm thanh")
        return

    context = context_var.get()
    try:
        level = float(volume_var.get())
        logging.debug(f"apply_volume: Người dùng nhập mức âm lượng: {level}")

        if not 0 <= level <= 1:
            logging.warning(f"apply_volume: Âm lượng không hợp lệ: {level}")
            raise ValueError

        if set_volume(level):
            save_config(device, level, context)
            logging.info(f"apply_volume: Đã đặt âm lượng {int(level*100)}% cho thiết bị '{device}' ({context})")
            messagebox.showinfo("Thành công", f"Đã đặt âm lượng {int(level*100)}% cho {device} ({context})")
        else:
            logging.error(f"apply_volume: Không thể đặt âm lượng cho thiết bị '{device}'")
            messagebox.showerror("Lỗi", "Không thể đặt âm lượng")

    except ValueError:
        logging.error("apply_volume: Âm lượng nhập vào không hợp lệ (phải từ 0.0 đến 1.0)")
        messagebox.showerror("Lỗi", "Âm lượng phải là số từ 0.0 đến 1.0")

# Cập nhật thiết bị trong GUI ở luồng chính
def update_device_dropdown(new_device):
    
    device_menu['values'] = get_audio_devices()
    device_var.set(new_device)


# === Theo dõi thay đổi thiết bị mặc định và tự động áp dụng âm lượng ===
def monitor_device_change():
    CoInitialize()  # Khởi tạo COM cho luồng này
    logging.debug("monitor_device_change: COM đã được khởi tạo cho luồng giám sát")

    last_device = None
    consecutive_errors = 0
    max_errors = 3

    while True:
        try:
            current_device = get_default_device_name()
            logging.debug(f"monitor_device_change: Thiết bị hiện tại: {current_device}")

            root.after(0, update_device_dropdown, current_device)

            if current_device and current_device != last_device:
                logging.info(f"monitor_device_change: Phát hiện thiết bị mới: {current_device}")
                root.after(0, refresh_devices)

                config = load_volume_config()
                logging.debug(f"monitor_device_change: Cấu hình hiện tại: {config}")

                if current_device in config and "default" in config[current_device]:
                    volume_level = config[current_device]["default"]
                    if set_volume(volume_level):
                        logging.info(f"monitor_device_change: Đã đặt âm lượng {int(volume_level * 100)}% cho thiết bị mới: {current_device}")
                        show_device_change_notification(current_device, volume_level)
                        consecutive_errors = 0  # Reset bộ đếm lỗi
                    else:
                        logging.error(f"monitor_device_change: Không thể đặt âm lượng cho thiết bị: {current_device}")
                else:
                    logging.warning(f"monitor_device_change: Không tìm thấy cấu hình cho thiết bị: {current_device}")

                last_device = current_device

        except Exception as e:
            consecutive_errors += 1
            logging.error(f"monitor_device_change: Lỗi khi theo dõi thiết bị (lần {consecutive_errors}): {e}")

            if consecutive_errors >= max_errors:
                logging.warning("monitor_device_change: Quá nhiều lỗi liên tiếp, tăng thời gian chờ...")
                time.sleep(15)
                consecutive_errors = 0
                continue

        time.sleep(5)

# === Tự động thêm shortcut vào thư mục Startup ===
def add_to_startup():
    try:
        exe_path = sys.executable
        startup_dir = os.path.join(os.environ["APPDATA"], "Microsoft\\Windows\\Start Menu\\Programs\\Startup")
        shortcut_path = os.path.join(startup_dir, "VolumeSetter.lnk")
        
        if not os.path.exists(shortcut_path):
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = exe_path
            shortcut.WorkingDirectory = os.path.dirname(exe_path)
            shortcut.save()
            print("Đã thêm vào Startup")
    except Exception as e:
        print(f"Lỗi khi thêm vào Startup: {e}")

# === Làm mới danh sách thiết bị ===
def refresh_devices():
    logging.debug("refresh_devices: Bắt đầu cập nhật danh sách thiết bị âm thanh")

    devices = get_audio_devices()
    logging.debug(f"refresh_devices: Danh sách thiết bị lấy được: {devices}")

    device_menu['values'] = devices

    if devices and not device_var.get():
        device_var.set(devices[0])
        logging.info(f"refresh_devices: Thiết bị đầu tiên được chọn mặc định: {devices[0]}")

    current_default = get_default_device_name()
    if current_default:
        status_label.config(text=f"Thiết bị hiện tại: {current_default}")
        logging.info(f"refresh_devices: Thiết bị mặc định hiện tại: {current_default}")
    else:
        logging.warning("refresh_devices: Không lấy được thiết bị mặc định")


# Trợ giúp
def open_help_link():
    webbrowser.open("https://github.com/NamNguyen237/auto-adjust-volumes-project/blob/main/how_to_use.md") 
# GitHub
def open_github_link():
    webbrowser.open("https://github.com/NamNguyen237/auto-adjust-volumes-project")

# === Giao diện người dùng ===
root = tk.Tk()
root.title("Trình điều chỉnh âm lượng mặc định (Bản thử nghiệm)")
root.geometry("500x500")
# Ghi đè hành vi khi nhấn nút ❌
def on_close():
    root.withdraw()
    notification.notify(
        title="VolumeSetter đang chạy nền",
        message="Bạn có thể mở lại từ biểu tượng ở góc phải màn hình.",
        timeout=4
    )

root.protocol("WM_DELETE_WINDOW", on_close)
# Frame chính
main_frame = tk.Frame(root, padx=10, pady=10)
main_frame.pack(fill=tk.BOTH, expand=True)

# Thiết bị âm thanh
tk.Label(main_frame, text="Chọn thiết bị âm thanh:").pack(pady=5)
device_frame = tk.Frame(main_frame)
device_frame.pack(fill=tk.X, pady=5)

device_var = tk.StringVar()
device_menu = ttk.Combobox(device_frame, textvariable=device_var, values=get_audio_devices(), width=35)
device_menu.pack(side=tk.LEFT, padx=(0, 5))
device_var.set(get_default_device_name())

refresh_btn = tk.Button(device_frame, text="🔄", command=refresh_devices, width=3)
refresh_btn.pack(side=tk.LEFT)

# Ngữ cảnh
tk.Label(main_frame, text="Ngữ cảnh (default/music/video...):").pack(pady=5)
context_var = tk.StringVar(value="default")
context_menu = ttk.Combobox(main_frame, textvariable=context_var, values=["default", "music", "video"], width=35)
context_menu.pack()

# Âm lượng
tk.Label(main_frame, text="Âm lượng (0.0 - 1.0):").pack(pady=5)
volume_var = tk.StringVar(value="0.5")
volume_entry = tk.Entry(main_frame, textvariable=volume_var, width=37)
volume_entry.pack()

# Nút áp dụng
tk.Button(main_frame, text="Áp dụng & Lưu", command=apply_volume, bg="#4CAF50", fg="white", 
          font=("Arial", 10, "bold"), width=20).pack(pady=15)

# Nút trợ giúp
tk.Button(root, text="Trợ giúp", command=open_help_link).pack(pady=5)

# Trạng thái
status_label = tk.Label(main_frame, text="", fg="blue", font=("Arial", 8))
status_label.pack(pady=5)

#About
def show_about_window():
    about = tk.Toplevel()
    about.title("Giới thiệu phần mềm")
    about.geometry("900x690")
    about.resizable(False, False)

    # Đặt cửa sổ này luôn ở trên
    about.transient(root)
    about.grab_set()
    about.focus_force()

    info = """
🔊 VolumeSetter - Trình điều chỉnh âm lượng mặc định (Bản thử nghiệm)

📌 Tác giả: Nam Nguyen
🤖 Công cụ hỗ trợ: Microsoft Copilot, Claude.

💬 Đôi lời tác giả:

    Có một thằng bạn của mình rất hay quên chỉnh âm lượng khi chuyển đổi giữa các thiết bị âm thanh (tai nghe, loa ngoài...), điều đó thật phiền phức và đôi khi gây ảnh hưởng đến thính giác nếu lỡ để quá to.

    Mình đã thử tìm kiếm phần mềm để giải quyết vấn đề này nhưng không thấy phần mềm nào phù hợp. Vì vậy, mình quyết định tự viết một phần mềm nhỏ để giúp bạn ấy và những người khác gặp vấn đề tương tự.

    Phần mềm này được phát triển để giải quyết vấn đề âm lượng không đồng nhất khi sử dụng nhiều thiết bị âm thanh khác nhau trên Windows. Mục tiêu là giúp người dùng dễ dàng quản lý và tự động áp dụng mức âm lượng yêu thích cho từng thiết bị khi chúng được kết nối lại.


🛠️ Chức năng:
- Tự động đặt âm lượng cho từng thiết bị âm thanh khi kết nối lại
- Lưu cấu hình theo ngữ cảnh (default, music, video...)
- Khởi động cùng Windows

📋 Hướng dẫn sử dụng:
1. Chọn thiết bị âm thanh (Gõ tên nếu không thấy trong danh sách (đang là bug))
2. Chọn ngữ cảnh và mức âm lượng (ngữ cảnh thì nên là default thôi, mấy cái kia mình chưa làm gì cả)
3. Nhấn 'Áp dụng & Lưu'
4. Phần mềm sẽ tự động áp dụng mức âm lượng đã lưu khi thiết bị được kết nối lại (Khi phần mềm còn đang chạy nền)

🙏 Cảm ơn bạn đã sử dụng phần mềm!
    """

    label = tk.Label(about, text=info, justify="left", font=("Segoe UI", 10), anchor="nw",wraplength=780)
    label.pack(padx=20, pady=20, fill="both", expand=True)
    tk.Button(about, text="GitHub", command=open_github_link).pack(pady=5)
    tk.Button(about, text="OK", command=about.destroy).pack(pady=10)

# Chạy nền system tray

from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw


def create_image():
    image = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(image)

    # Vẽ hình loa
    draw.polygon([(16, 24), (32, 24), (40, 16), (40, 48), (32, 40), (16, 40)], fill="blue")

    # Vẽ sóng âm (vòng cung)
    draw.arc([44, 20, 60, 44], start=300, end=60, fill="blue", width=3)
    draw.arc([48, 16, 64, 48], start=300, end=60, fill="blue", width=2)

    return image

def hide_window():
    root.withdraw()

def show_window(icon, item):
    root.deiconify()

def quit_app(icon, item):
    icon.stop()
    root.quit()

def setup_tray():
    image = create_image()
    menu = Menu(
        MenuItem("Hiện cửa sổ", show_window),
        MenuItem("Thoát", quit_app)
    )
    tray_icon = Icon("🔊 Nam's VolumeSetter", image, "🔊 Nam's VolumeSetter", menu)
    threading.Thread(target=tray_icon.run, daemon=True).start()


# === Khởi động ===
refresh_devices()
threading.Thread(target=monitor_device_change, daemon=True).start()
add_to_startup()
show_about_window()
hide_window()         # Ẩn cửa sổ chính
setup_tray()          # Tạo icon ở system tray
setup_logger()        # Thiết lập logger
root.mainloop()       # Vẫn cần vòng lặp chính để giữ chương trình chạy
