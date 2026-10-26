import pygame
import sys
import random
import array

# 初期化
pygame.init()
pygame.font.init()

# ミキサー（音声）の初期化
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

SCREEN_WIDTH, SCREEN_HEIGHT = 600, 650
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Space Invaders with Sound")
clock = pygame.time.Clock()

# フォント設定
font_large = pygame.font.SysFont("arial", 50, bold=True)
font_medium = pygame.font.SysFont("arial", 30)
font_small = pygame.font.SysFont("arial", 20)

# 色の定義
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 50, 50)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)

# ---------------------------------------------------------
# 効果音のプログラミング生成
# ---------------------------------------------------------
def create_shoot_sound():
    """ビーム発射音の生成"""
    sample_rate = 22050
    duration = 0.1  # 秒
    n_samples = int(sample_rate * duration)
    buf = array.array('h', [0] * (n_samples * 2))
    
    for i in range(n_samples):
        # 周波数を急激に下げるピコピコ音
        freq = 800 - (i / n_samples) * 600
        t = float(i) / sample_rate
        val = int(16383.0 * (1 if (int(t * freq * 2) % 2 == 0) else -1))
        buf[i * 2] = val
        buf[i * 2 + 1] = val
    return pygame.mixer.Sound(buffer=buf)

def create_explosion_sound():
    """爆発音（撃破音）の生成"""
    sample_rate = 22050
    duration = 0.2
    n_samples = int(sample_rate * duration)
    buf = array.array('h', [0] * (n_samples * 2))
    
    for i in range(n_samples):
        # ノイズ（雑音）を減衰させて爆発っぽくする
        decay = 1.0 - (i / n_samples)
        val = int((random.random() * 2 - 1) * 16383.0 * decay)
        buf[i * 2] = val
        buf[i * 2 + 1] = val
    return pygame.mixer.Sound(buffer=buf)

# 音声オブジェクトを作成
sound_shoot = create_shoot_sound()
sound_explosion = create_explosion_sound()

# ---------------------------------------------------------
# ドット絵パターンの定義
# ---------------------------------------------------------
PLAYER_PIXELS = [
    "    1    ",
    "   111   ",
    "   111   ",
    " 1111111 ",
    "111111111",
    "111111111",
    "111111111"
]

INVADER_TOP = [
    "  1111  ",
    " 111111 ",
    "11111111",
    "11 11 11",
    "11111111",
    "  1  1  ",
    " 1 11 1 ",
    "1 1  1 1"
]

INVADER_MID = [
    "  11111  ",
    " 1111111 ",
    "111111111",
    "11 111 11",
    "111111111",
    "  11 11  ",
    " 11   11 ",
    " 1     1 "
]

INVADER_BOT = [
    "   1111   ",
    " 11111111 ",
    "1111111111",
    "11 1111 11",
    "1111111111",
    "   1111   ",
    "  11  11  ",
    "11      11"
]

def draw_pixel_art(surface, pattern, color, x, y, pixel_size=3):
    for row_idx, row in enumerate(pattern):
        for col_idx, char in enumerate(row):
            if char == '1':
                rect = pygame.Rect(
                    x + col_idx * pixel_size,
                    y + row_idx * pixel_size,
                    pixel_size,
                    pixel_size
                )
                pygame.draw.rect(surface, color, rect)

def create_bunkers():
    bunkers = []
    bunker_width = 60
    bunker_height = 40
    start_x = 50
    spacing = 135
    bunker_y = 480

    for i in range(4):
        bx = start_x + i * spacing
        for x in range(bx, bx + bunker_width, 6):
            for y in range(bunker_y, bunker_y + bunker_height, 6):
                if not ((y < bunker_y + 12 and (x < bx + 12 or x >= bx + bunker_width - 12)) or
                        (y >= bunker_y + 24 and (bx + 18 <= x < bx + bunker_width - 18))):
                    bunkers.append(pygame.Rect(x, y, 6, 6))
    return bunkers

def reset_game():
    player_rect = pygame.Rect(SCREEN_WIDTH // 2 - 15, SCREEN_HEIGHT - 60, 30, 21)
    bullets = []
    enemy_bullets = []

    invaders = []
    invader_types = [INVADER_TOP, INVADER_MID, INVADER_BOT]
    colors = [CYAN, MAGENTA, YELLOW]

    for row in range(3):
        for col in range(8):
            x = 60 + col * 60
            y = 70 + row * 45
            invaders.append({
                'rect': pygame.Rect(x, y, 30, 24),
                'pattern': invader_types[row],
                'color': colors[row]
            })

    bunkers = create_bunkers()
    direction = 1  # 1: 右移動, -1: 左移動

    return player_rect, bullets, enemy_bullets, invaders, bunkers, 0, direction, False, False

# ゲーム初期化
player, bullets, enemy_bullets, invaders, bunkers, score, direction, game_over, game_win = reset_game()

player_speed = 5
bullet_w, bullet_h = 4, 10
bullet_speed = 8
enemy_bullet_speed = 4

# メインゲームループ
running = True
while running:
    clock.tick(60)
    screen.fill(BLACK)

    # --- 1. イベント処理 ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if not game_over and not game_win:
                if event.key == pygame.K_SPACE:
                    if len(bullets) < 3:
                        bullet_x = player.centerx - bullet_w // 2
                        bullets.append(pygame.Rect(bullet_x, player.top, bullet_w, bullet_h))
                        sound_shoot.play()  # 発射音を鳴らす
            else:
                if event.key == pygame.K_r:
                    player, bullets, enemy_bullets, invaders, bunkers, score, direction, game_over, game_win = reset_game()
                elif event.key == pygame.K_q:
                    running = False

    # --- 2. 状態の更新 ---
    if not game_over and not game_win:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and player.left > 0:
            player.x -= player_speed
        if keys[pygame.K_RIGHT] and player.right < SCREEN_WIDTH:
            player.x += player_speed

        # 弾の移動
        for bullet in bullets[:]:
            bullet.y -= bullet_speed
            if bullet.y < 0:
                bullets.remove(bullet)

        for e_bullet in enemy_bullets[:]:
            e_bullet.y += enemy_bullet_speed
            if e_bullet.y > SCREEN_HEIGHT:
                enemy_bullets.remove(e_bullet)

        # 敵のランダム攻撃
        if invaders and random.random() < 0.015:
            shooter = random.choice(invaders)
            bx = shooter['rect'].centerx - bullet_w // 2
            by = shooter['rect'].bottom
            enemy_bullets.append(pygame.Rect(bx, by, bullet_w, bullet_h))

        # インベーダーの移動処理（暴走対策版）
        move_down = False
        # 敵が減ると少しずつ速くなる
        current_speed = 1.2 + (24 - len(invaders)) * 0.08

        # 端に達したか確認
        for invader in invaders:
            if direction == 1 and invader['rect'].right >= SCREEN_WIDTH - 15:
                move_down = True
                break
            elif direction == -1 and invader['rect'].left <= 15:
                move_down = True
                break

        if move_down:
            direction *= -1  # 反転
            for invader in invaders:
                invader['rect'].y += 15  # 15ピクセル一段下がる
        else:
            for invader in invaders:
                invader['rect'].x += current_speed * direction

        # 当たり判定
        for bullet in bullets[:]:
            hit = False
            for invader in invaders[:]:
                if bullet.colliderect(invader['rect']):
                    bullets.remove(bullet)
                    invaders.remove(invader)
                    score += 100
                    sound_explosion.play()  # 撃破音を鳴らす
                    hit = True
                    break
            if hit:
                continue

            for block in bunkers[:]:
                if bullet.colliderect(block):
                    bullets.remove(bullet)
                    bunkers.remove(block)
                    break

        for e_bullet in enemy_bullets[:]:
            for block in bunkers[:]:
                if e_bullet.colliderect(block):
                    enemy_bullets.remove(e_bullet)
                    bunkers.remove(block)
                    break

        for e_bullet in enemy_bullets:
            if e_bullet.colliderect(player):
                sound_explosion.play()
                game_over = True

        for invader in invaders:
            for block in bunkers[:]:
                if invader['rect'].colliderect(block):
                    bunkers.remove(block)
            
            # 自機までの到達チェック
            if invader['rect'].bottom >= player.top:
                sound_explosion.play()
                game_over = True
                break

        if len(invaders) == 0:
            game_win = True

    # --- 3. 描画処理 ---
    if not game_over and not game_win:
        draw_pixel_art(screen, PLAYER_PIXELS, GREEN, player.x, player.y, pixel_size=3)

        for bullet in bullets:
            pygame.draw.rect(screen, YELLOW, bullet)

        for e_bullet in enemy_bullets:
            pygame.draw.rect(screen, RED, e_bullet)

        for invader in invaders:
            draw_pixel_art(screen, invader['pattern'], invader['color'], invader['rect'].x, invader['rect'].y, pixel_size=3)

        for block in bunkers:
            pygame.draw.rect(screen, GREEN, block)

        score_surface = font_small.render(f"SCORE: {score}", True, WHITE)
        screen.blit(score_surface, (15, 15))

    else:
        if game_over:
            title_text = font_large.render("GAME OVER", True, RED)
        else:
            title_text = font_large.render("YOU WIN!", True, GREEN)

        score_text = font_medium.render(f"FINAL SCORE: {score}", True, WHITE)
        restart_text = font_small.render("Press R to Restart | Q to Quit", True, WHITE)

        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10))
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70))

        screen.blit(title_text, title_rect)
        screen.blit(score_text, score_rect)
        screen.blit(restart_text, restart_rect)

    pygame.display.flip()

pygame.quit()
sys.exit()