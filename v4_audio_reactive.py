from pywinauto import Desktop
from pynput import mouse, keyboard
import tkinter as tk
from colorsys import hsv_to_rgb
import pyaudiowpatch as pyaudio
import numpy as np
import time
import win32gui

class IconManager:
    def __init__(self):
        self.icons = []
        self.load()

    def load(self):
        desktop = Desktop(backend="uia")

        for window in desktop.windows():
            try:
                if window.class_name() not in ("Progman", "WorkerW"): continue
                for item in window.descendants(control_type="ListItem"):
                    rect = item.rectangle()
                    name = item.window_text()

                    if name: self.icons.append((
                        name, item,
                        rect.left, rect.top,
                        rect.right, rect.bottom
                    ))
            except Exception: pass
        print("found", len(self.icons), "icons")

    def find_nearest(self, mouse_x, mouse_y):

        nearest = None
        nearest_distance = float("inf")

        for icon in self.icons:
            name, item, left, top, right, bottom = icon

            x = (left + right) / 2
            y = (top + bottom) / 2

            distance = np.hypot(mouse_x-x, mouse_y-y)

            if distance < nearest_distance:
                nearest_distance = distance
                nearest = icon

        return nearest, nearest_distance

class InputManager:
    def __init__(self):
        self.last_click = 0
        self.selected_icon = None
        self.pulse_request = False
        self.keyboard_controller = keyboard.Controller()

        self.mouse_listner = mouse.Listener(on_click=self.click)
        self.mouse_listner.start()

    def click(self, x, y, button, pressed):
        try:
            if pressed and button == mouse.Button.left:
                if self.is_mouse_on_desktop():
                    self.pulse_request = True
                
                if self.selected_icon:
                    now = time.monotonic()
                    if now - self.last_click < 0.3:
                        try:
                            self.selected_icon.select()
                            self.selected_icon.set_focus()
                            self.keyboard_controller.press(keyboard.Key.enter)
                            self.keyboard_controller.release(keyboard.Key.enter)
                        
                        except Exception as error:
                            print(error)
                            self.selected_icon = None
                        
                        self.last_click = 0
                    else: self.last_click = now
        except Exception: print(error)

    def is_mouse_on_desktop(self):
        try:
            pt = win32gui.GetCursorPos()
            hwnd_under_mouse = win32gui.WindowFromPoint(pt)
            root_hwnd = win32gui.GetAncestor(hwnd_under_mouse, 2)
            class_name = win32gui.GetClassName(root_hwnd)
            return class_name in ("Progman", "WorkerW")
        except Exception: return False

class Overlay:
    def __init__(self):
        self.currect_points = None
        self.target_points = None
        self.move_speed = 0.2

        self.angle = 0

        self.margin = 3
        self.outlineW = 5

        self.hue = 0
        self.color_speed = 0.01

        self.pulse = False
        self.pulse_strength = 30

        self.last_pulse = 0

        self.audio = None
        self.device = None
        self.rate = 0
        self.channels = 0
        self.stream = None
        self.last_audio_retry = 0
        self.init_audio()

        self.root = tk.Tk()

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        self.root.configure(bg="black")
        self.root.wm_attributes("-transparentcolor", "black")

        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.outline = self.canvas.create_polygon(
            0,0,0,0,0,0,0,0, outline="white", width=self.outlineW)

        self.hide()

    def init_audio(self):
        try:
            if self.stream is not None:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception: pass

            if self.audio is not None:
                try: self.audio.terminate()
                except Exception: pass

            self.audio = pyaudio.PyAudio()
            self.device = self.audio.get_default_wasapi_loopback()
            self.rate = int(self.device["defaultSampleRate"])
            self.channels = self.device["maxInputChannels"]

            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.rate,
                input=True,
                input_device_index=self.device["index"],
                frames_per_buffer=1024
            )
            
            
        except Exception as error:
            self.stream = None
            print(error)

    def rotate(self, mx, my):
        size = 30 + self.margin

        points = np.array([
            [-size, -size],
            [-size,  size],
            [ size,  size],
            [ size, -size]
        ], dtype=float)

        cos = np.cos(self.angle)
        sin = np.sin(self.angle)

        rotation = np.array([
            [ cos, sin],
            [-sin, cos]
        ])

        rotated = points @ rotation
        rotated += np.array([mx, my])

        self.angle = (self.angle + 0.02) % (np.pi*2)

        return rotated

    def icon(self, left, top, right, bottom):
        self.margin = min(10, self.margin)
        return np.array([
            [left  - self.margin, top    - self.margin],
            [left  - self.margin, bottom + self.margin],
            [right + self.margin, bottom + self.margin],
            [right + self.margin, top    - self.margin]
        ], dtype=float)

    def start_pulse(self): self.pulse = True

    def update_pulse(self):
        if self.pulse:
            self.margin += self.pulse_strength
            self.outlineW += self.pulse_strength/5
            self.hue += 0.1
            self.angle += np.pi/8

            self.pulse = False
        else:
            self.margin = 3
            self.outlineW = 5

    def audio_engine(self):
        if self.stream is None:
            now = time.monotonic()
            if now - self.last_audio_retry > 2:
                self.last_audio_retry = now
                self.init_audio()
            return

        try:
            if self.stream.get_read_available() < 1024: return
            data = self.stream.read(1024, exception_on_overflow=False)
        except Exception as error:
            print(error)
            self.stream = None
            return

        try:
            samples = np.frombuffer(data, dtype=np.int16).astype(float)
            if samples.size == 0: return
            
            extra = samples.size % self.channels
            if extra: samples = samples[:-extra]

            if samples.size == 0: return

            samples = samples.reshape(-1, self.channels)
            samples = np.mean(samples, axis=1)

            spectrum = np.abs(np.fft.rfft(samples))
            frequencies = np.fft.rfftfreq(len(samples), 1 / self.rate)

            bass = spectrum[(frequencies >= 40) & (frequencies <= 180)]
            if bass.size: bass_power = np.mean(bass)
            else: bass_power = 0

            cymbals = spectrum[(frequencies >= 5000) & (frequencies <= 12000)]
            if cymbals.size: cymbals_power = np.mean(cymbals)
            else: cymbals_power = 0

            now = time.monotonic()
            if bass_power > 3000000:
                if now- self.last_pulse > 0.2:
                    self.pulse = True
                    self.last_pulse = now

            volume = np.sqrt(np.mean(samples ** 2))

            self.margin += min(50, volume/500)
            self.outlineW += min(10, volume/1500)
        except Exception as error: print(error)
        

    def update_color(self):
        self.hue += self.color_speed
        self.hue %= 1

        r, g, b = hsv_to_rgb(self.hue, 1, 1)
        return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"

    def set_target(self, points):
        self.target_points = points
        if self.currect_points is None: self.currect_points = points.copy()

    def animate(self):
        if self.target_points is None: return
        self.currect_points += (self.target_points - self.currect_points) * self.move_speed

    def show(self):
        if self.currect_points is None: return
        padding = int(self.outlineW) + 5
        color = self.update_color()

        min_x = int(np.min(self.currect_points[:, 0])) - padding
        max_x = int(np.max(self.currect_points[:, 0])) + padding

        min_y = int(np.min(self.currect_points[:, 1])) - padding
        max_y = int(np.max(self.currect_points[:, 1])) + padding

        width  = max_x - min_x
        height = max_y - min_y

        self.root.geometry(f"{width}x{height}+{min_x}+{min_y}")

        local_points = self.currect_points - np.array([min_x, min_y])
        self.canvas.itemconfig(self.outline, outline=color, width=self.outlineW)
        self.canvas.coords(self.outline, *local_points.flatten())
        self.root.deiconify()

    def hide(self): self.root.withdraw()

class Controller:
    def __init__(self):
        self.icons = IconManager()

        self.overlay = Overlay()

        self.input = InputManager()

        self.target_points = None
        self.geomerty = None

        self.update()

    def update(self):
        try:
            if self.input.is_mouse_on_desktop():
                try:
                    mx, my = win32gui.GetCursorPos()
                except Exception:
                    self.overlay.hide()
                    return self.schedule_update()


                icon, distance = self.icons.find_nearest(mx, my)

                if distance < 400 and icon is not None:
                    name, item, left, top, right, bottom = icon
                    self.input.selected_icon = item

                    target_points = self.overlay.icon(left, top, right, bottom)
                
                else:
                    self.input.selected_icon = None
                    target_points = self.overlay.rotate(mx, my)

                if self.input.pulse_request == True:
                    self.overlay.start_pulse()
                    self.input.pulse_request = False

                self.overlay.set_target(target_points)
                self.overlay.update_pulse()
                self.overlay.audio_engine()
                self.overlay.animate()
                self.overlay.show()

            else:
                self.input.selected_icon = None
                self.overlay.hide()

        except Exception as error: print(error)

        self.schedule_update()

    def schedule_update(self):
        try: self.overlay.root.after(16, self.update)
        except tk.TclError: pass


if __name__ == "__main__":
    script = Controller()
    script.overlay.root.mainloop()