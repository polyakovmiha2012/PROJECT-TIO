from pywinauto import Desktop
from pynput import mouse, keyboard
from colorsys import hsv_to_rgb
import math
import tkinter as tk
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

            distance = ((mouse_x-x)**2 + (mouse_y-y)**2)**0.5
            if distance < nearest_distance:
                nearest_distance = distance
                nearest = icon

        return nearest, nearest_distance

class InputManager:
    def __init__(self):
        self.shift = False
        self.selected_icon = None
        self.keyboard_controller = keyboard.Controller()

        self.keyboard_listener = keyboard.Listener(on_press=self.press, on_release=self.release)
        self.keyboard_listener.start()

        self.mouse_listner = mouse.Listener(on_click=self.click)
        self.mouse_listner.start()

    def press(self, key):
        if key == keyboard.Key.shift: self.shift = True

    def release(self, key):
        if key == keyboard.Key.shift: self.shift = False

    def click(self, x, y, button, pressed):
        if pressed and button == mouse.Button.left:
            if self.selected_icon:
                self.selected_icon.select()
                self.selected_icon.set_focus()
                self.keyboard_controller.press(keyboard.Key.enter)

    def is_mouse_on_desktop(self):
        flags, hcursor, pt = win32gui.GetCursorInfo()
        hwnd_under_mouse = win32gui.WindowFromPoint(pt)
        root_hwnd = win32gui.GetAncestor(hwnd_under_mouse, 2)
        class_name = win32gui.GetClassName(root_hwnd)
        return class_name in ("Progman", "WorkerW")

class Overlay:
    def __init__(self):
        self.colors = [
            f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
            for i in range(360)
            for r, g, b in [hsv_to_rgb(i / 360, 1, 1)]]
        self.color = None
        self.color_num = 0

        self.space = 40
        self.margin = 3

        self.angle = 0

        self.root = tk.Tk()

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        self.root.configure(bg="black")
        self.root.wm_attributes("-transparentcolor", "black")

        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.outline = self.canvas.create_rectangle(0,0,0,0, outline="white", width=self.margin)
        self.arrow = self.canvas.create_polygon(0,0, 0,0, 0,0, fill="white", outline="")

        self.hide()

    def show(self, left, top, right, bottom, distance):
        self.color = self.colors[self.color_num % len(self.colors)]

        self.canvas.itemconfig(self.outline, outline=self.color)
        self.canvas.itemconfig(self.arrow, fill=self.color)

        width = right-left
        height = bottom-top

        self.root.geometry(
            f"{width+self.margin*2}x{height+20 + self.space + self.margin*2}"
            f"+{left-self.margin}"
            f"+{top-self.margin}")

        strength = 1 - distance / 1000
        strength = max(0 , min(1, strength))

        move_y = strength * self.space + math.sin(self.angle)*5

        self.canvas.coords(
            self.outline,
            self.margin, self.margin,
            width + self.margin, height + self.margin)

        self.canvas.coords(
            self.arrow,
            width/2, height+8 - move_y + self.space,
            width/2-10, height+20 - move_y + self.space,
            width/2+10, height+20 - move_y + self.space)

        self.color_num +=3
        self.angle += 0.2

        self.root.deiconify()

    def hide(self): self.root.withdraw()

class Controller:
    def __init__(self):

        self.icons = IconManager()

        self.overlay = Overlay()

        self.input = InputManager()

        self.update()

    def update(self):
        if self.input.shift:
            if self.input.is_mouse_on_desktop():

                x, y = win32gui.GetCursorPos()

                icon, distance = self.icons.find_nearest(x, y)

                name, item, left, top, right, bottom = icon
                self.input.selected_icon = item

                self.overlay.show(left, top, right, bottom, distance)
            else: self.hide()
        else: self.hide()

        self.overlay.root.after(30, self.update)

    def hide(self):
        self.input.selected_icon = None
        self.overlay.hide()

if __name__ == "__main__":
    script = Controller()
    script.overlay.root.mainloop()