import pygame
import math
import os

from subroutine import (
    WHITE, BLACK, GRAY, RED, ORANGE, YELLOW, BLUE, GREEN, LIGHT_BLUE, BROWN,
    assets_function, hitting_animation_function,
    draw_trajectory_prediction, SeedProjectile, Explosion
)

# 1. 初始化 Pygame
pygame.init()
pygame.font.init()

# 視窗設定
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("萌寵大亂鬥 - 雙人對戰版 (ESC 暫停選單)")

FONT_SMALL = pygame.font.SysFont("microsoftjhenghei", 18, bold=True)
FONT_MED   = pygame.font.SysFont("microsoftjhenghei", 24, bold=True)
FONT_BIG   = pygame.font.SysFont("microsoftjhenghei", 36, bold=True)
CLOCK = pygame.time.Clock()
FPS = 60

# 2. 自動取得素材路徑並載入
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_ASSETS_DIR = os.path.join(CURRENT_DIR, "hamster_assets")

assets = assets_function(TARGET_ASSETS_DIR, WIDTH, HEIGHT)
BACKGROUND_IMG = assets["bg_img"]
CHARACTERS     = assets["characters"]
TABLE_IMG      = assets["table_img"]

EXPLOSION_FRAMES = hitting_animation_function(TARGET_ASSETS_DIR)


# 3. 玩家角色類別
class Player:
    def __init__(self, x, ground_y, char_data, name, is_left):
        self.name = name
        self.is_left = is_left
        self.char_name = char_data["name"]
        
        scale = char_data["scale"]
        self.width = int(70 * scale)
        self.height = int(70 * scale)
        
        self.max_hp = char_data["max_hp"]
        self.hp = self.max_hp

        raw_img = char_data["img_left"]
        scaled_img = pygame.transform.scale(raw_img, (self.width, self.height))
        
        if is_left:
            self.image = scaled_img
        else:
            self.image = pygame.transform.flip(scaled_img, True, False)

        self.weapon_img = char_data["weapon"]
        
        self.x = x
        self.y = ground_y - self.height
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, surface):
        surface.blit(self.image, (self.x, self.y))
        
        bar_w = self.width
        pygame.draw.rect(surface, RED, (self.x, self.y - 15, bar_w, 8))
        if self.hp > 0:
            pygame.draw.rect(surface, GREEN, (self.x, self.y - 15, bar_w * (self.hp / self.max_hp), 8))
        pygame.draw.rect(surface, BLACK, (self.x, self.y - 15, bar_w, 8), 1)


# 4. 中央茶几障礙物類別
class ObstacleWall:
    def __init__(self, x, ground_y, image):
        self.width = 250
        self.height = 150
        self.x = x - self.width // 2
        
        offset_down = 35
        self.y = (ground_y + offset_down) - self.height

        self.image = image
        self.max_hp = 200
        self.hp = self.max_hp

        self.hit_height = 100
        self.hit_y = (ground_y + offset_down) - self.hit_height
        self.rect = pygame.Rect(self.x, self.hit_y, self.width, self.hit_height)

    def draw(self, surface):
        if self.hp <= 0:
            return
            
        if self.image:
            surface.blit(self.image, (self.x, self.y))
        else:
            pygame.draw.rect(surface, BROWN, self.rect)
            pygame.draw.rect(surface, (100, 40, 10), (self.x, self.rect.y, self.width, 20))
            pygame.draw.rect(surface, BLACK, self.rect, 2)
            
        bar_width = 120
        bar_x = self.x + (self.width - bar_width) // 2
        bar_y = self.y - 15
        pygame.draw.rect(surface, RED, (bar_x, bar_y, bar_width, 6))
        pygame.draw.rect(surface, YELLOW, (bar_x, bar_y, bar_width * (self.hp / self.max_hp), 6))
        pygame.draw.rect(surface, BLACK, (bar_x, bar_y, bar_width, 6), 1)

        txt_wall = FONT_SMALL.render("防禦茶几", True, BLACK)
        surface.blit(txt_wall, (self.x + self.width // 2 - txt_wall.get_width() // 2, self.y - 35))


# 5. 繪製背景
def draw_background():
    if BACKGROUND_IMG:
        screen.blit(BACKGROUND_IMG, (0, 0))
    else:
        screen.fill(LIGHT_BLUE)
        pygame.draw.rect(screen, (100, 60, 30), (0, HEIGHT - 50, WIDTH, 50))
        pygame.draw.rect(screen, GREEN, (0, HEIGHT - 50, WIDTH, 10))


# 6. 主程式入口
def main():
    game_stage = "START"  # START -> SELECT -> GAME
    paused = False        # 是否開啟 ESC 暫停選單
    pause_selection = 0   # 暫停選單游標 (0: 回到首頁, 1: 重新選擇角色, 2: 退出遊戲)
    
    select_player = 1
    p1_char_idx = 0
    p2_char_idx = 1
    
    player1 = None
    player2 = None
    obstacle = None

    turn = 0
    state = 0
    
    angle = 45.0
    angle_dir = 1
    power = 5.0
    power_dir = 1
    
    projectile = None
    explosions = []

    running = True
    while running:
        CLOCK.tick(FPS)
        
        # -----------------------------------------------------
        # 階段 1: 開始封面畫面
        # -----------------------------------------------------
        if game_stage == "START":
            draw_background()
            
            overlay = pygame.Surface((500, 220), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 220))
            screen.blit(overlay, (WIDTH // 2 - 250, HEIGHT // 2 - 110))
            pygame.draw.rect(screen, BLACK, (WIDTH // 2 - 250, HEIGHT // 2 - 110, 500, 220), 3)

            title = FONT_BIG.render("🐾 萌寵彈道大亂鬥 🐾", True, RED)
            start_tip = FONT_MED.render("按下【 SPACE 鍵 】進入角色選擇", True, BLACK)
            
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 70))
            screen.blit(start_tip, (WIDTH // 2 - start_tip.get_width() // 2, HEIGHT // 2 + 20))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    game_stage = "SELECT"

        # -----------------------------------------------------
        # 階段 2: 選擇角色畫面
        # -----------------------------------------------------
        elif game_stage == "SELECT":
            draw_background()

            overlay = pygame.Surface((600, 420), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 230))
            screen.blit(overlay, (WIDTH // 2 - 300, 90))
            pygame.draw.rect(screen, BLACK, (WIDTH // 2 - 300, 90, 600, 420), 3)

            stage_title = FONT_BIG.render(f"請 【玩家 {select_player}】 選擇角色", True, RED if select_player == 1 else BLUE)
            tip_select = FONT_SMALL.render("使用【 UP / DOWN 方向鍵 】切換，【 SPACE 】確認選擇", True, BLACK)
            screen.blit(stage_title, (WIDTH // 2 - stage_title.get_width() // 2, 105))
            screen.blit(tip_select, (WIDTH // 2 - tip_select.get_width() // 2, 150))

            current_idx = p1_char_idx if select_player == 1 else p2_char_idx

            for i, char in enumerate(CHARACTERS):
                box_y = 195 + i * 95
                is_selected = (i == current_idx)
                
                box_color = RED if (is_selected and select_player == 1) else (BLUE if is_selected else GRAY)
                pygame.draw.rect(screen, box_color, (WIDTH // 2 - 240, box_y, 480, 80), 0 if is_selected else 2)
                
                screen.blit(char["img_left"], (WIDTH // 2 - 220, box_y + 5))
                screen.blit(char["weapon"], (WIDTH // 2 + 150, box_y + 24))
                
                txt_name = FONT_MED.render(f"{char['name']} (血量: {char['max_hp']})", True, WHITE if is_selected else BLACK)
                txt_info = FONT_SMALL.render(f"體型比例: {int(char['scale']*100)}%", True, WHITE if is_selected else GRAY)
                
                screen.blit(txt_name, (WIDTH // 2 - 120, box_y + 15))
                screen.blit(txt_info, (WIDTH // 2 - 120, box_y + 45))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        if select_player == 1:
                            p1_char_idx = (p1_char_idx - 1) % len(CHARACTERS)
                        else:
                            p2_char_idx = (p2_char_idx - 1) % len(CHARACTERS)
                    elif event.key == pygame.K_DOWN:
                        if select_player == 1:
                            p1_char_idx = (p1_char_idx + 1) % len(CHARACTERS)
                        else:
                            p2_char_idx = (p2_char_idx + 1) % len(CHARACTERS)
                    elif event.key == pygame.K_SPACE:
                        if select_player == 1:
                            select_player = 2
                        else:
                            player1 = Player(80, HEIGHT - 50, CHARACTERS[p1_char_idx], "玩家 1 (左)", True)
                            player2 = Player(WIDTH - 150, HEIGHT - 50, CHARACTERS[p2_char_idx], "玩家 2 (右)", False)
                            obstacle = ObstacleWall(WIDTH // 2, HEIGHT - 50, TABLE_IMG)
                            turn = 0
                            state = 0
                            game_stage = "GAME"

        # -----------------------------------------------------
        # 階段 3: 戰鬥進行中畫面
        # -----------------------------------------------------
        elif game_stage == "GAME":
            draw_background()

            current_player = player1 if turn == 0 else player2
            target_player = player2 if turn == 0 else player1

            game_over = (player1.hp <= 0 or player2.hp <= 0)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    # 💡 按下 ESC 鍵切換暫停選單
                    if event.key == pygame.K_ESCAPE and not game_over:
                        paused = not paused

                    # 若處於暫停選單中，用上下鍵選擇選項，SPACE 確認
                    if paused:
                        if event.key == pygame.K_UP:
                            pause_selection = (pause_selection - 1) % 3
                        elif event.key == pygame.K_DOWN:
                            pause_selection = (pause_selection + 1) % 3
                        elif event.key == pygame.K_SPACE:
                            if pause_selection == 0:  # 回到首頁
                                game_stage = "START"
                                paused = False
                            elif pause_selection == 1:  # 重新選擇角色
                                game_stage = "SELECT"
                                select_player = 1
                                paused = False
                            elif pause_selection == 2:  # 退出遊戲
                                running = False

                if not paused:
                    if game_over:
                        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                            game_stage = "SELECT"
                            select_player = 1
                    else:
                        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                            if state == 0:
                                state = 1
                            elif state == 1:
                                state = 2

                        elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE:
                            if state == 2:
                                state = 3
                                is_left = (turn == 0)
                                start_x = current_player.x + current_player.width // 2
                                start_y = current_player.y + current_player.height // 2
                                projectile = SeedProjectile(
                                    start_x, start_y, angle, power, is_left,
                                    current_player.weapon_img, WIDTH, HEIGHT
                                )

            if not paused and not game_over:
                if state == 1:
                    angle += 0.84 * angle_dir
                    if angle >= 80 or angle <= 15:
                        angle_dir *= -1

                elif state == 2:
                    power += 0.28 * power_dir
                    if power >= 25 or power <= 5:
                        power_dir *= -1

                if state == 3 and projectile:
                    projectile.update()
                    p_rect = projectile.get_rect()

                    if obstacle and obstacle.hp > 0 and p_rect.colliderect(obstacle.rect):
                        obstacle.hp = max(0, obstacle.hp - 20)
                        projectile.active = False
                        explosions.append(Explosion(projectile.x, projectile.y, EXPLOSION_FRAMES))

                    elif p_rect.colliderect(target_player.rect):
                        target_player.hp = max(0, target_player.hp - 20)
                        projectile.active = False
                        explosions.append(Explosion(projectile.x, projectile.y, EXPLOSION_FRAMES))

                    elif not projectile.active:
                        explosions.append(Explosion(projectile.x, projectile.y, EXPLOSION_FRAMES))

                    if not projectile.active:
                        projectile = None
                        state = 0
                        turn = 1 - turn
                        angle = 45.0
                        power = 5.0

                if state == 1 or state == 2:
                    is_left = (turn == 0)
                    start_x = current_player.x + current_player.width // 2
                    start_y = current_player.y + current_player.height // 2
                    obs_rect = obstacle.rect if (obstacle and obstacle.hp > 0) else None
                    draw_trajectory_prediction(screen, start_x, start_y, angle, power, is_left, WIDTH, HEIGHT, obs_rect)

            # 1. 繪製角色
            player1.draw(screen)
            player2.draw(screen)

            # 2. 繪製茶几牆
            if obstacle and obstacle.hp > 0:
                obstacle.draw(screen)

            # 3. 更新與繪製爆炸動畫
            for exp in explosions[:]:
                if not paused:
                    exp.update()
                exp.draw(screen)
                if exp.finished:
                    explosions.remove(exp)

            if not game_over and not paused:
                # 4. 繪製瞄準線
                is_left = (turn == 0)
                actual_angle = angle if is_left else 180 - angle
                rad = math.radians(actual_angle)
                line_len = 60
                origin_x = current_player.x + current_player.width // 2
                origin_y = current_player.y + current_player.height // 2
                line_end_x = origin_x + line_len * math.cos(rad)
                line_end_y = origin_y - line_len * math.sin(rad)
                pygame.draw.line(screen, RED if state == 1 else GRAY, (origin_x, origin_y), (line_end_x, line_end_y), 3)

                # 5. 繪製飛行武器
                if projectile:
                    projectile.draw(screen)

                # 6. UI 資訊顯示
                turn_text = FONT_SMALL.render(f"目前回合: {current_player.name} ({current_player.char_name})", True, RED if turn == 0 else BLUE)
                angle_str = f"發射角度: {int(angle)}°"
                power_str = f"初速度 (力量): {int(power)}"
                
                txt_angle = FONT_SMALL.render(angle_str, True, BLACK)
                txt_power = FONT_SMALL.render(power_str, True, BLACK)
                
                screen.blit(turn_text, (20, 15))
                screen.blit(txt_angle, (20, 40))
                screen.blit(txt_power, (20, 65))

                if state == 0:
                    tip_str = "【按住 SPACE】開始調整角度 | 【ESC】暫停選單"
                elif state == 1:
                    tip_str = "【再次按住 SPACE】鎖定角度並開始蓄力"
                elif state == 2:
                    tip_str = "【鬆開 SPACE】確定力量，發射！"
                else:
                    tip_str = "【等待飛行中...】"
                    
                txt_tip = FONT_SMALL.render(tip_str, True, BLUE)
                screen.blit(txt_tip, (20, 90))

                # 力量蓄力條
                pygame.draw.rect(screen, BLACK, (20, 120, 200, 16), 2)
                if state == 2:
                    fill_width = int(((power - 5) / 20) * 196)
                    pygame.draw.rect(screen, ORANGE, (22, 122, fill_width, 12))

            # 勝負結算顯示
            if game_over:
                winner = "玩家 2 (右)" if player1.hp <= 0 else "玩家 1 (左)"
                win_text = FONT_BIG.render(f"🎉 {winner} 獲勝！ 🎉", True, RED)
                restart_text = FONT_SMALL.render("【按下 SPACE 鍵】重新選擇角色", True, BLACK)
                
                overlay = pygame.Surface((440, 120), pygame.SRCALPHA)
                overlay.fill((255, 255, 255, 220))
                screen.blit(overlay, (WIDTH // 2 - 220, HEIGHT // 2 - 60))
                pygame.draw.rect(screen, BLACK, (WIDTH // 2 - 220, HEIGHT // 2 - 60, 440, 120), 2)

                screen.blit(win_text, (WIDTH // 2 - win_text.get_width() // 2, HEIGHT // 2 - 45))
                screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 10))

            # -----------------------------------------------------
            # 💡 暫停選單繪製 (ESC Menu Overlay)
            # -----------------------------------------------------
            if paused:
                # 半透明背景遮罩
                pause_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pause_overlay.fill((0, 0, 0, 150))
                screen.blit(pause_overlay, (0, 0))

                # 選單方框
                menu_w, menu_h = 400, 280
                menu_x = (WIDTH - menu_w) // 2
                menu_y = (HEIGHT - menu_h) // 2
                pygame.draw.rect(screen, WHITE, (menu_x, menu_y, menu_w, menu_h))
                pygame.draw.rect(screen, BLACK, (menu_x, menu_y, menu_w, menu_h), 3)

                # 選單標題
                txt_title = FONT_MED.render("=== 遊戲暫停 ===", True, BLACK)
                screen.blit(txt_title, (menu_x + (menu_w - txt_title.get_width()) // 2, menu_y + 25))

                # 選單選項
                options = ["回到首頁", "重新選擇角色", "退出遊戲"]
                for idx, text in enumerate(options):
                    is_selected = (idx == pause_selection)
                    opt_y = menu_y + 80 + idx * 55
                    
                    # 選中項目高亮底色
                    if is_selected:
                        pygame.draw.rect(screen, (255, 220, 100), (menu_x + 40, opt_y - 5, menu_w - 80, 42))
                        pygame.draw.rect(screen, RED, (menu_x + 40, opt_y - 5, menu_w - 80, 42), 2)
                        txt_opt = FONT_MED.render(f"▶ {text}", True, RED)
                    else:
                        txt_opt = FONT_MED.render(text, True, BLACK)
                        
                    screen.blit(txt_opt, (menu_x + 60, opt_y))

                tip_esc = FONT_SMALL.render("再次按下【 ESC 】返回遊戲", True, GRAY)
                screen.blit(tip_esc, (menu_x + (menu_w - tip_esc.get_width()) // 2, menu_y + 235))

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()