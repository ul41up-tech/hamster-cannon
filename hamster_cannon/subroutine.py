import pygame
import math
import os

# ---------------------------------------------------------
# 1. 顏色常數定義 (COLOR_function)
# ---------------------------------------------------------
WHITE  = (255, 255, 255)
BLACK  = (0, 0, 0)
GRAY   = (180, 180, 180)
RED    = (230, 60, 60)
ORANGE = (255, 150, 0)
YELLOW = (255, 215, 0)
BLUE   = (100, 180, 255)
GREEN  = (60, 180, 80)
LIGHT_BLUE = (220, 240, 255)
BROWN  = (139, 69, 19)

def COLOR_function():
    return {
        "WHITE": WHITE, "BLACK": BLACK, "GRAY": GRAY,
        "RED": RED, "ORANGE": ORANGE, "YELLOW": YELLOW,
        "BLUE": BLUE, "GREEN": GREEN, "LIGHT_BLUE": LIGHT_BLUE,
        "BROWN": BROWN
    }


# ---------------------------------------------------------
# 2. 斜向拋射與彈道繪製 (Projectile_Motion_function)
# ---------------------------------------------------------
def draw_trajectory_prediction(surface, start_x, start_y, angle_deg, power, is_left, width, height, obstacle_rect, g=0.45):
    actual_angle = angle_deg if is_left else 180 - angle_deg
    angle_rad = math.radians(actual_angle)
    v0x = power * math.cos(angle_rad)
    v0y = -power * math.sin(angle_rad)
    
    points = []
    for t in range(0, 100, 2):
        pred_x = start_x + v0x * t
        pred_y = start_y + v0y * t + 0.5 * g * (t ** 2)
        
        if obstacle_rect and obstacle_rect.collidepoint(pred_x, pred_y):
            points.append((int(pred_x), int(pred_y)))
            break
            
        if pred_y >= height - 50 or pred_x > width or pred_x < 0:
            points.append((int(pred_x), int(height - 50)))
            break
        points.append((int(pred_x), int(pred_y)))
        
    temp_surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for pt in points:
        pygame.draw.circle(temp_surf, (255, 140, 0, 160), pt, 4)
    surface.blit(temp_surf, (0, 0))


class SeedProjectile:
    """砲彈類別"""
    def __init__(self, x, y, angle_deg, power, is_left, weapon_img, width, height, g=0.45):
        self.x0 = x
        self.y0 = y
        self.x = x
        self.y = y
        self.radius = 14
        self.g = g
        self.weapon_img = weapon_img
        self.width = width
        self.height = height
        
        actual_angle = angle_deg if is_left else 180 - angle_deg
        angle_rad = math.radians(actual_angle)
        
        self.v0x = power * math.cos(angle_rad)
        self.v0y = -power * math.sin(angle_rad)
        
        self.t = 0
        self.path_history = []
        self.active = True
        self.rotation = 0

    def update(self):
        if not self.active:
            return

        self.t += 1
        self.x = self.x0 + self.v0x * self.t
        self.y = self.y0 + self.v0y * self.t + 0.5 * self.g * (self.t ** 2)
        
        self.path_history.append((int(self.x), int(self.y)))
        
        if self.y >= self.height - 50 or self.x > self.width or self.x < 0:
            self.y = self.height - 50
            self.active = False

    def draw(self, surface):
        if len(self.path_history) > 1:
            pygame.draw.lines(surface, ORANGE, False, self.path_history, 2)

        self.rotation = (self.rotation - 10) % 360
        rotated_img = pygame.transform.rotate(self.weapon_img, self.rotation)
        rect = rotated_img.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated_img, rect.topleft)

    def get_rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)


# ---------------------------------------------------------
# 3. 素材搜尋與載入索引 (assets_function)
# ---------------------------------------------------------
def load_image_fuzzy(target_assets_dir, target_keywords, size, fallback_color):
    valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')
    
    if os.path.exists(target_assets_dir):
        for file in os.listdir(target_assets_dir):
            if file.lower().endswith(valid_exts):
                for kw in target_keywords:
                    if kw in file.lower():
                        full_path = os.path.join(target_assets_dir, file)
                        try:
                            img = pygame.image.load(full_path).convert_alpha()
                            print(f"成功載入素材: {full_path}")
                            if size:
                                return pygame.transform.scale(img, size)
                            return img
                        except Exception as e:
                            print(f"載入 {file} 失敗: {e}")
    else:
        print(f"提示: 未找到資料夾 '{target_assets_dir}'，使用備用圖形運行。")
    
    if size:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        if fallback_color is not None:
            pygame.draw.ellipse(surf, fallback_color, (0, 0, size[0], size[1]))
        return surf
    return None


def assets_function(target_assets_dir, width, height):
    """載入所有遊戲角色、武器、與障礙物素材，並定義各自的體型比例與血量"""
    bg_img = load_image_fuzzy(target_assets_dir, ["backgrand", "background", "背景"], (width, height), None)
    if bg_img:
        bg_img = bg_img.convert()

    base_size = 70  # 標準大小

    # 1. 倉鼠 (鼠: 80% 體型, 血量 80)
    hamster_raw = load_image_fuzzy(target_assets_dir, ["hamster", "倉鼠", "鼠"], (base_size, base_size), (220, 160, 100))
    seed_img = load_image_fuzzy(target_assets_dir, ["seed", "sunflower", "葵花籽", "種子"], (28, 28), (80, 50, 20))

    # 2. 小貓 (貓: 100% 標準體型, 血量 100)
    cat_raw = load_image_fuzzy(target_assets_dir, ["cat.png", "cat_"], (base_size, base_size), (240, 180, 80))
    cat_weapon = load_image_fuzzy(target_assets_dir, ["cat_weapon", "fish", "魚"], (32, 32), (100, 180, 200))

    # 3. 小狗 (狗: 120% 大體型, 血量 130)
    dog_raw = load_image_fuzzy(target_assets_dir, ["dog.png", "dog_"], (base_size, base_size), (200, 120, 60))
    dog_weapon = load_image_fuzzy(target_assets_dir, ["dog_weapon", "bone", "骨頭"], (32, 32), (230, 230, 210))

    # 茶几障礙物
    table_img = load_image_fuzzy(target_assets_dir, ["table", "coffee", "desk", "茶几", "wall"], (250, 150), None)

    # 角色清單集合 (定義各自的 scale 體型比例與 max_hp 血量)
    CHARACTERS = [
        {
            "name": "可愛倉鼠", 
            "img_left": hamster_raw, 
            "weapon": seed_img, 
            "scale": 0.8,   # 80% 體型
            "max_hp": 80
        },
        {
            "name": "頑皮貓咪", 
            "img_left": cat_raw, 
            "weapon": cat_weapon, 
            "scale": 1.0,   # 100% 體型
            "max_hp": 100
        },
        {
            "name": "霸氣狗狗", 
            "img_left": dog_raw, 
            "weapon": dog_weapon, 
            "scale": 1.2,   # 120% 體型
            "max_hp": 130
        }
    ]

    return {
        "bg_img": bg_img,
        "characters": CHARACTERS,
        "table_img": table_img
    }


# ---------------------------------------------------------
# 4. 擊中與爆炸動畫 (hitting_animation_function)
# ---------------------------------------------------------
def hitting_animation_function(target_assets_dir):
    frames = []
    size = (100, 100)
    for i in range(1, 5):
        frame = load_image_fuzzy(target_assets_dir, [f"explosion_{i}"], size, None)
        if frame:
            frames.append(frame)
            
    if len(frames) < 4:
        frames = []
        for radius in [20, 35, 50, 40]:
            surf = pygame.Surface(size, pygame.SRCALPHA)
            pygame.draw.circle(surf, ORANGE, (50, 50), radius)
            pygame.draw.circle(surf, YELLOW, (50, 50), int(radius * 0.6))
            frames.append(surf)
    return frames


class Explosion:
    def __init__(self, x, y, frames):
        self.x = x
        self.y = y
        self.frames = frames
        self.current_frame = 0
        self.frame_timer = 0
        self.frame_delay = 4
        self.finished = False

    def update(self):
        self.frame_timer += 1
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.current_frame += 1
            if self.current_frame >= len(self.frames):
                self.finished = True

    def draw(self, surface):
        if not self.finished:
            current_img = self.frames[self.current_frame]
            rect = current_img.get_rect(center=(int(self.x), int(self.y)))
            surface.blit(current_img, rect.topleft)