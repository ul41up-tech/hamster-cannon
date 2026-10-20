import pygame
import math
import os
import random

# 1. 初始化 Pygame
pygame.init()
pygame.font.init()

# 視窗與顏色設定
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("倉鼠發射葵花籽 - 雙人對戰版")

WHITE  = (255, 255, 255)
BLACK  = (0, 0, 0)
GRAY   = (180, 180, 180)
RED    = (230, 60, 60)
ORANGE = (255, 150, 0)
YELLOW = (255, 215, 0)
BLUE   = (100, 180, 255)
GREEN  = (60, 180, 80)

FONT = pygame.font.SysFont("microsoftjhenghei", 18, bold=True)
CLOCK = pygame.time.Clock()
FPS = 60

# 2. 自動定位跟 .py 檔同一資料夾下的 hamster_assets 資料夾
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_ASSETS_DIR = os.path.join(CURRENT_DIR, "hamster_assets")

def load_image_fuzzy(target_keywords, size, fallback_color):
    """在同目錄下的 hamster_assets 資料夾搜尋含有關鍵字的圖片，若無則生成備用圖示"""
    valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.webp')
    
    # 檢查 hamster_assets 資料夾是否存在
    if os.path.exists(TARGET_ASSETS_DIR):
        for file in os.listdir(TARGET_ASSETS_DIR):
            if file.lower().endswith(valid_exts):
                for kw in target_keywords:
                    if kw in file.lower():
                        full_path = os.path.join(TARGET_ASSETS_DIR, file)
                        try:
                            img = pygame.image.load(full_path).convert_alpha()
                            print(f"成功載入素材: {full_path}")
                            return pygame.transform.scale(img, size)
                        except Exception as e:
                            print(f"載入 {file} 失敗: {e}")
    else:
        print(f"提示: 未找到同目錄下的資料夾 '{TARGET_ASSETS_DIR}'，使用備用圖形運行。")
    
    # 備用圖示 (當資料夾找不到圖片時)
    surf = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.ellipse(surf, fallback_color, (0, 0, size[0], size[1]))
    return surf

# 載入同目錄下的倉鼠與葵花籽圖片，並建立右側翻轉倉鼠
HAMSTER_LEFT_IMG  = load_image_fuzzy(["hamster", "倉鼠", "鼠"], (70, 70), (220, 160, 100))
HAMSTER_RIGHT_IMG = pygame.transform.flip(HAMSTER_LEFT_IMG, True, False)  # 水平翻轉朝左
SEED_IMG          = load_image_fuzzy(["seed", "sunflower", "葵花籽", "種子"], (24, 24), (80, 50, 20))

# 3. 玩家倉鼠類別
class HamsterPlayer:
    def __init__(self, x, y, image, name, is_left):
        self.x = x
        self.y = y
        self.width = 70
        self.height = 70
        self.image = image
        self.name = name
        self.is_left = is_left
        self.hp = 100
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, surface):
        surface.blit(self.image, (self.x, self.y))
        # 繪製血條底色與當前血量
        pygame.draw.rect(surface, RED, (self.x, self.y - 15, self.width, 8))
        if self.hp > 0:
            pygame.draw.rect(surface, GREEN, (self.x, self.y - 15, self.width * (self.hp / 100), 8))
        pygame.draw.rect(surface, BLACK, (self.x, self.y - 15, self.width, 8), 1)

# 4. 預測彈道虛線繪製
def draw_trajectory_prediction(surface, start_x, start_y, angle_deg, power, is_left, g=0.45):
    """
    依當前角度與力量，快速模擬出虛線，預測拋物線落點。
    """
    actual_angle = angle_deg if is_left else 180 - angle_deg
    angle_rad = math.radians(actual_angle)
    v0x = power * math.cos(angle_rad)
    v0y = -power * math.sin(angle_rad)
    
    points = []
    # 預測最多 100 步
    for t in range(0, 100, 2):  # 步長為 2 可以形成虛線感
        pred_x = start_x + v0x * t
        pred_y = start_y + v0y * t + 0.5 * g * (t ** 2)
        
        # 預測至地面 (HEIGHT - 50) 以下或出界，即停止預報
        if pred_y >= HEIGHT - 50 or pred_x > WIDTH or pred_x < 0:
            points.append((int(pred_x), int(HEIGHT - 50)))
            break
        points.append((int(pred_x), int(pred_y)))
        
    # 建立帶透明度的畫布繪製虛線點
    temp_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for pt in points:
        pygame.draw.circle(temp_surf, (255, 140, 0, 160), pt, 4)  # 橘色帶透明度的點
    surface.blit(temp_surf, (0, 0))

# 5. 砲彈類別 (無風向，標準斜向拋射)
class SeedProjectile:
    def __init__(self, x, y, angle_deg, power, is_left, g=0.45):
        self.x0 = x
        self.y0 = y
        self.x = x
        self.y = y
        self.radius = 12
        self.g = g  # 重力加速度
        
        # 依玩家方向決定射擊角度
        actual_angle = angle_deg if is_left else 180 - angle_deg
        angle_rad = math.radians(actual_angle)
        
        # 初速度分量 (斜向拋射公式)
        self.v0x = power * math.cos(angle_rad)
        self.v0y = -power * math.sin(angle_rad)
        
        self.t = 0  # 時間步長
        self.path_history = []  # 軌跡紀錄
        self.active = True
        self.rotation = 0

    def update(self):
        if not self.active:
            return

        # 標準斜向拋射運動方程式:
        # x(t) = x0 + v0x * t
        # y(t) = y0 + v0y * t + 0.5 * g * t^2
        self.t += 1
        self.x = self.x0 + self.v0x * self.t
        self.y = self.y0 + self.v0y * self.t + 0.5 * self.g * (self.t ** 2)
        
        self.path_history.append((int(self.x), int(self.y)))
        
        # 落地或飛出邊界
        if self.y >= HEIGHT - 50 or self.x > WIDTH or self.x < 0:
            self.y = HEIGHT - 50
            self.active = False

    def draw(self, surface):
        if len(self.path_history) > 1:
            pygame.draw.lines(surface, ORANGE, False, self.path_history, 2)

        self.rotation = (self.rotation - 10) % 360
        rotated_img = pygame.transform.rotate(SEED_IMG, self.rotation)
        rect = rotated_img.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated_img, rect.topleft)

    def get_rect(self):
        return pygame.Rect(self.x - self.radius, self.y - self.radius, self.radius * 2, self.radius * 2)

# 6. 主遊戲循環
def main():
    # 建立左、右兩隻倉鼠玩家
    player1 = HamsterPlayer(80, HEIGHT - 120, HAMSTER_LEFT_IMG, "倉鼠 1 號 (左)", True)
    player2 = HamsterPlayer(WIDTH - 150, HEIGHT - 120, HAMSTER_RIGHT_IMG, "倉鼠 2 號 (右)", False)

    turn = 0    # 0: 倉鼠 1 | 1: 倉鼠 2
    state = 0   # 0: 準備 | 1: 調角度 | 2: 蓄力 | 3: 飛射中
    
    angle = 45.0          # 初始角度 (角度值)
    angle_dir = 1         # 角度往復擺動方向
    power = 5.0           # 初始力量 (初速度)
    power_dir = 1         # 蓄力條往復方向
    
    projectile = None

    running = True
    while running:
        CLOCK.tick(FPS)
        screen.fill((210, 245, 255))  # 天空背景

        # 繪製地面與草地
        pygame.draw.rect(screen, (100, 60, 30), (0, HEIGHT - 50, WIDTH, 50))
        pygame.draw.rect(screen, GREEN, (0, HEIGHT - 50, WIDTH, 10))

        current_player = player1 if turn == 0 else player2
        target_player = player2 if turn == 0 else player1

        # 處理事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if player1.hp > 0 and player2.hp > 0:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    # 第一次按住：開始擺動角度
                    if state == 0:
                        state = 1
                    # 第二次按住：固定角度，開始蓄力
                    elif state == 1:
                        state = 2

                elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
                    # 第二次放開：確定力量，鬆開發射！
                    if state == 2:
                        state = 3
                        is_left = (turn == 0)
                        start_x = current_player.x + 35
                        start_y = current_player.y + 20
                        projectile = SeedProjectile(start_x, start_y, angle, power, is_left)

        # 狀態 1：角度動態擺動
        if state == 1:
            angle += 1.2 * angle_dir
            if angle >= 80 or angle <= 15:
                angle_dir *= -1

        # 狀態 2：蓄力條動態增減
        elif state == 2:
            power += 0.4 * power_dir
            if power >= 25 or power <= 5:
                power_dir *= -1

        # 狀態 3：砲彈物理更新與碰撞處理
        if state == 3 and projectile:
            projectile.update()
            p_rect = projectile.get_rect()

            # 擊中對方倉鼠
            if p_rect.colliderect(target_player.rect):
                target_player.hp = max(0, target_player.hp - 20)
                projectile.active = False

            # 砲彈消失 (命中或落地) -> 切換回合
            if not projectile.active:
                projectile = None
                state = 0
                turn = 1 - turn
                angle = 45.0
                power = 5.0

        # --- 預計軌跡虛線與畫面元素繪製 ---
        # 在調整角度 (state == 1) 與蓄力 (state == 2) 時顯示預計彈道
        if state == 1 or state == 2:
            is_left = (turn == 0)
            start_x = current_player.x + 35
            start_y = current_player.y + 20
            draw_trajectory_prediction(screen, start_x, start_y, angle, power, is_left)

        # 1. 繪製倉鼠玩家
        player1.draw(screen)
        player2.draw(screen)

        # 2. 繪製當前發射台的角度瞄準線
        is_left = (turn == 0)
        actual_angle = angle if is_left else 180 - angle
        rad = math.radians(actual_angle)
        line_len = 60
        origin_x = current_player.x + 35
        origin_y = current_player.y + 20
        line_end_x = origin_x + line_len * math.cos(rad)
        line_end_y = origin_y - line_len * math.sin(rad)
        pygame.draw.line(screen, RED if state == 1 else GRAY, (origin_x, origin_y), (line_end_x, line_end_y), 3)

        # 3. 繪製發射中的砲彈與軌跡
        if projectile:
            projectile.draw(screen)

        # 4. 繪製 UI 提示文字與蓄力條
        turn_text = FONT.render(f"目前回合: {current_player.name}", True, RED if turn == 0 else BLUE)
        angle_str = f"發射角度: {int(angle)}°"
        power_str = f"初速度 (力量): {int(power)}"
        
        txt_angle = FONT.render(angle_str, True, BLACK)
        txt_power = FONT.render(power_str, True, BLACK)
        
        screen.blit(turn_text, (20, 15))
        screen.blit(txt_angle, (20, 40))
        screen.blit(txt_power, (20, 65))

        # 操作狀態提示
        if state == 0:
            tip_str = "【按住 SPACE】開始調整角度"
        elif state == 1:
            tip_str = "【再次按住 SPACE】鎖定角度並開始蓄力"
        elif state == 2:
            tip_str = "【鬆開 SPACE】確定力量，發射葵花籽！"
        else:
            tip_str = "【等待葵花籽飛行...】"
            
        txt_tip = FONT.render(tip_str, True, BLUE)
        screen.blit(txt_tip, (20, 90))

        # 力量蓄力條 UI
        pygame.draw.rect(screen, BLACK, (20, 120, 200, 16), 2)
        if state == 2:
            fill_width = int(((power - 5) / 20) * 196)
            pygame.draw.rect(screen, ORANGE, (22, 122, fill_width, 12))

        # 勝負判定顯示
        if player1.hp <= 0 or player2.hp <= 0:
            winner = "倉鼠 2 號 (右)" if player1.hp <= 0 else "倉鼠 1 號 (左)"
            win_text = FONT.render(f"🎉 {winner} 獲勝！遊戲結束 🎉", True, RED)
            screen.blit(win_text, (WIDTH // 2 - 130, HEIGHT // 2 - 20))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()