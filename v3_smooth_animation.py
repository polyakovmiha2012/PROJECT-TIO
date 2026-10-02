from pywinauto import Desktop
from pynput import mouse, keyboard
import tkinter as tk
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
        self.keyboard_controller = keyboard.Controller()

        self.mouse_listner = mouse.Listener(on_click=self.click)
        self.mouse_listner.start()

    def click(self, x, y, button, pressed):
        if pressed and button == mouse.Button.left:
            if self.selected_icon:
                now = time.monotonic()
                if now - self.last_click < 0.3:
                    self.selected_icon.select()
                    self.selected_icon.set_focus()
                    self.keyboard_controller.press(keyboard.Key.enter)
                    self.last_click = 0
                else: self.last_click = now

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

        self.root = tk.Tk()

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        self.root.configure(bg="black")
        self.root.wm_attributes("-transparentcolor", "black")

        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.outline = self.canvas.create_polygon(0,0,0,0,0,0,0,0, outline="white", width=3)

        self.hide()

    def rotate(self, mx, my):
        size = 40 + self.margin

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

        self.angle += 0.02

        return rotated

    def icon(self, left, top, right, bottom):
        return np.array([
            [left  - self.margin, top    - self.margin],
            [left  - self.margin, bottom + self.margin],
            [right + self.margin, bottom + self.margin],
            [right + self.margin, top    - self.margin]
        ], dtype=float)

    def set_target(self, points):
        self.target_points = points
        if self.currect_points is None: self.currect_points = points.copy()

    def animate(self):
        if self.target_points is None: return
        self.currect_points += (self.target_points - self.currect_points) * self.move_speed

    def show(self):
        if self.currect_points is None: return
        padding = 10

        min_x = int(np.min(self.currect_points[:, 0])) - padding
        max_x = int(np.max(self.currect_points[:, 0])) + padding

        min_y = int(np.min(self.currect_points[:, 1])) - padding
        max_y = int(np.max(self.currect_points[:, 1])) + padding

        width  = max_x - min_x
        height = max_y - min_y

        self.root.geometry(f"{width}x{height}+{min_x}+{min_y}")

        local_points = self.currect_points - np.array([min_x, min_y])
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
        if self.input.is_mouse_on_desktop():
            mx, my = win32gui.GetCursorPos()


            icon, distance = self.icons.find_nearest(mx, my)

            if distance < 400:
                name, item, left, top, right, bottom = icon
                self.input.selected_icon = item

                target_points = self.overlay.icon(left, top, right, bottom)
            
            else:
                self.input.selected_icon = None
                target_points = self.overlay.rotate(mx, my)

            self.overlay.set_target(target_points)
            self.overlay.animate()
            self.overlay.show()

        else:
            self.input.selected_icon = None
            self.overlay.hide()

        self.overlay.root.after(16, self.update)


if __name__ == "__main__":
    script = Controller()
    script.overlay.root.mainloop()