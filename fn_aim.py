import cv2
import numpy as np
import mss
import win32api
import win32con
import win32gui
import time
import threading
import pygame

# === الإعدادات ===
CONFIG = {
    'FOV_RADIUS': 180,       # حجم دائرة التصويب
    'SMOOTHNESS': 0.2,       # سرعة الماوس (0.2 سريع وثابت)
}

sct = mss.mss()
sw, sh = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
cx, cy, r = sw // 2, sh // 2, CONFIG['FOV_RADIUS']

# متغيرات للرسم
current_boxes = []
target_pos = None

# === 1. رسم دائرة POV والمربعات ===
def draw_overlay():
    pygame.init()
    screen = pygame.display.set_mode((sw, sh), pygame.NOFRAME | pygame.SRCALPHA)
    hwnd = pygame.display.get_wm_info()["window"]
    
    # تخلي النافذة شفافة
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT | win32con.WS_EX_TOPMOST | win32con.WS_EX_TOOLWINDOW)
    win32gui.SetLayeredWindowAttributes(hwnd, 0, 255, win32con.LWA_ALPHA)
    
    while True:
        screen.fill((0, 0, 0, 0))
        # رسم دائرة FOV
        pygame.draw.circle(screen, (0, 255, 140), (cx, cy), r, 2)
        
        # رسم مربعات ESP
        for b in current_boxes:
            pygame.draw.rect(screen, (255, 0, 0), b, 2)
            
        pygame.display.flip()
        time.sleep(0.01)

# === 2. اللوجيك (الإيم بوت) ===
def logic_loop():
    global current_boxes, target_pos
    prev_gray = None
    
    while True:
        bbox = {'left': cx-r, 'top': cy-r, 'width': r*2, 'height': r*2}
        img = np.array(sct.grab(bbox))[:, :, :3]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        if prev_gray is not None:
            # فلتر الفروق (بيمسك أي حاجة بتتحرك أو ليها حواف واضحة زي اللاعبين)
            diff = cv2.absdiff(prev_gray, gray)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            current_boxes, bd, bt = [], 9999, None
            
            for c in contours:
                if 100 < cv2.contourArea(c) < 10000:
                    x, y, w, h = cv2.boundingRect(c)
                    
                    # النقطة اللي الماوس هيروح عليها (نص العرض، وفوق بـ 10 بكسل "الراس")
                    tx, ty = x + (w//2), y + 10
                    
                    current_boxes.append((cx-r+x, cy-r+y, w, h))
                    
                    # حساب المسافة من مركز الشاشة
                    d = ((tx-r)**2 + (ty-r)**2)**0.5
                    if d < bd:
                        bd, bt = d, (tx, ty)
            
            target_pos = bt
            
            # تحريك الماوس لو كلك يمين مضغوط
            if win32api.GetAsyncKeyState(win32con.VK_RBUTTON) < 0 and target_pos:
                dx = int((target_pos[0] - r) * (1 - CONFIG['SMOOTHNESS']))
                dy = int((target_pos[1] - r) * (1 - CONFIG['SMOOTHNESS']))
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, dx, dy, 0, 0)
                
        prev_gray = gray
        time.sleep(0.015)

# === التشغيل ===
if __name__ == "__main__":
    threading.Thread(target=draw_overlay, daemon=True).start()
    logic_loop()
