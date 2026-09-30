import pygame
import sys
import random

pygame.init()

# ---------------------------
# CONFIG
# ---------------------------
WIDTH, HEIGHT = 480, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Adventure Game Puzzle")
clock = pygame.time.Clock()

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_BG = (240, 238, 233)
SOFT_BLUE = (173, 216, 230)
GRAY = (180, 180, 180)
DARK_GRAY = (100, 100, 100)
GREEN = (46, 139, 87)
RED = (178, 34, 34)

TOTAL_LEVELS = 6
GRID_SIZE = 7

THEME_POOL = [
    {"theme": "THEME: TIME FLIES", "words": ["CLOCK", "TIMER", "WATCH", "SECOND"]},
    {"theme": "THEME: FRUITY SALAD", "words": ["APPLE", "BANANA", "GRAPE", "MELON"]},
    {"theme": "THEME: DEEP BLUE SEA", "words": ["SHARK", "WHALE", "CORAL", "OCTOPUS"]},
    {"theme": "THEME: SPACE RACE", "words": ["ORBIT", "PLANET", "ROCKET", "GALAXY"]},
    {"theme": "THEME: FOREST ADVENTURE", "words": ["TREE", "BIRD", "MOSS", "RIVER"]},
    {"theme": "THEME: FROSTY WORLD", "words": ["SNOW", "ICE", "PINE", "FROST"]},
    {"theme": "THEME: CITY LIGHTS", "words": ["TAXI", "SKYLINE", "SUBWAY", "BRIDGE"]},
    {"theme": "THEME: MAGIC CASTLE", "words": ["DRAGON", "SPELL", "CASTLE", "QUEEN"]},
    {"theme": "THEME: DESERT TRIP", "words": ["CANYON", "DUNE", "OASIS", "SUN"]},
    {"theme": "THEME: MOUNTAIN HIKE", "words": ["SUMMIT", "TRAIL", "PEAK", "ALPINE"]},
    {"theme": "THEME: UNDERWORLD", "words": ["GHOST", "MOON", "CREEP", "SHADOW"]},
    {"theme": "THEME: GARDEN GLOW", "words": ["ROSE", "LEAF", "BLOOM", "PETAL"]},
]

# ---------------------------
# GLOBAL STATE
# ---------------------------
current_state = "HOME_MENU"

# Tracks completed level score data
level_results = {}
# Tracks themes already used in solved levels, so no repeats
used_themes = set()
# Stores challenge data for levels as they are generated
challenge_data = {}

# ---------------------------
# HELPERS
# ---------------------------

def get_font(size, bold=False):
    return pygame.font.SysFont("Arial", size, bold=bold)


def get_level_button_positions(W, H):
    b_w, b_h = int(W * 0.6), int(H * 0.07)
    b_x = W // 2 - b_w // 2
    start_y = int(H * 0.24)
    gap = int(H * 0.08)
    positions = []
    for i in range(TOTAL_LEVELS):
        y = start_y + i * (b_h + gap)
        positions.append({
            "rect": pygame.Rect(b_x, y, b_w, b_h),
            "level": i + 1,
        })
    return positions


def build_theme_for_level():
    remaining = [item for item in THEME_POOL if item["theme"] not in used_themes]
    if not remaining:
        remaining = THEME_POOL
    return random.choice(remaining)


def ensure_challenge(level_num):
    if level_num not in challenge_data:
        theme_data = build_theme_for_level()
        challenge_data[level_num] = create_word_search_challenge(theme_data)
    return challenge_data[level_num]


def create_word_search_challenge(theme_data):
    grid = [["" for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]

    def place_word(word):
        for _ in range(300):
            start_r = random.randint(0, GRID_SIZE - 1)
            start_c = random.randint(0, GRID_SIZE - 1)
            dr, dc = random.choice(directions)
            end_r = start_r + dr * (len(word) - 1)
            end_c = start_c + dc * (len(word) - 1)

            if not (0 <= end_r < GRID_SIZE and 0 <= end_c < GRID_SIZE):
                continue

            fits = True
            for i in range(len(word)):
                r = start_r + dr * i
                c = start_c + dc * i
                if grid[r][c] != "" and grid[r][c] != word[i]:
                    fits = False
                    break

            if fits:
                for i in range(len(word)):
                    r = start_r + dr * i
                    c = start_c + dc * i
                    grid[r][c] = word[i]
                return True
        return False

    for word in theme_data["words"]:
        placed = place_word(word)
        if not placed:
            return create_word_search_challenge(theme_data)

    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] == "":
                grid[r][c] = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    return {
        "theme": theme_data["theme"],
        "words": theme_data["words"],
        "grid": grid,
        "selected_cells": [],
        "solved_paths": [],
        "found_words": [],
        "is_selecting": False,
        "time_up": False,
        "start_ticks": pygame.time.get_ticks(),
        "stage_duration": 90,
    }


def straight_line_ok(path):
    if len(path) <= 2:
        return True
    r0, c0 = path[0]
    r1, c1 = path[1]
    dr = r1 - r0
    dc = c1 - c0
    for i in range(2, len(path)):
        rr = path[i][0] - r0
        cc = path[i][1] - c0
        if rr != dr * i or cc != dc * i:
            return False
    return True


def get_cell_from_position(pos, START_X, START_Y, CELL_SIZE, PADDING):
    x, y = pos
    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            cx = START_X + col * (CELL_SIZE + PADDING)
            cy = START_Y + row * (CELL_SIZE + PADDING)
            if cx <= x <= cx + CELL_SIZE and cy <= y <= cy + CELL_SIZE:
                return row, col
    return None


def get_level_score(challenge_data_for_level):
    if not challenge_data_for_level or challenge_data_for_level["time_up"]:
        return 0
    elapsed = (pygame.time.get_ticks() - challenge_data_for_level["start_ticks"]) / 1000
    time_left = max(0, int(challenge_data_for_level["stage_duration"] - elapsed))
    word_count = len(challenge_data_for_level["found_words"])
    total_words = len(challenge_data_for_level["words"])
    if total_words == 0:
        return 0
    base = 100 + (time_left * 2)
    progress_reward = int((word_count / total_words) * 100)
    return max(0, base + progress_reward)


def finalize_level(level_num, challenge):
    if level_num not in level_results:
        score = get_level_score(challenge)
        level_results[level_num] = {
            "points": score,
            "theme": challenge["theme"],
            "words": challenge["words"],
        }
        used_themes.add(challenge["theme"])


def render_menu(screen_surface, W, H, FONT_L, FONT_M):
    screen_surface.fill(LIGHT_BG)
    title = FONT_L.render("Home Menu", True, BLACK)
    screen_surface.blit(title, title.get_rect(center=(W // 2, H * 0.18)))

    # Settings button
    m1_w, m1_h = int(W * 0.6), int(H * 0.08)
    m1_x = W // 2 - m1_w // 2
    m1_y = int(H * 0.38)
    pygame.draw.rect(screen_surface, WHITE, (m1_x, m1_y, m1_w, m1_h), border_radius=8)
    m1_text = FONT_M.render("Go to Settings", True, BLACK)
    screen_surface.blit(m1_text, (m1_x + m1_w // 2 - m1_text.get_width() // 2, m1_y + m1_h // 2 - m1_text.get_height() // 2))

    # Start game button
    m2_w, m2_h = int(W * 0.6), int(H * 0.08)
    m2_x = W // 2 - m2_w // 2
    m2_y = int(H * 0.53)
    pygame.draw.rect(screen_surface, WHITE, (m2_x, m2_y, m2_w, m2_h), border_radius=8)
    m2_text = FONT_M.render("Start Game", True, BLACK)
    screen_surface.blit(m2_text, (m2_x + m2_w // 2 - m2_text.get_width() // 2, m2_y + m2_h // 2 - m2_text.get_height() // 2))

    return {
        "settings_rect": pygame.Rect(m1_x, m1_y, m1_w, m1_h),
        "start_rect": pygame.Rect(m2_x, m2_y, m2_w, m2_h),
    }


def render_settings(screen_surface, W, H, FONT_L, FONT_M):
    screen_surface.fill(LIGHT_BG)
    title = FONT_L.render("Settings Menu", True, BLACK)
    screen_surface.blit(title, title.get_rect(center=(W // 2, H * 0.18)))

    esc_w, back_h = int(W * 0.4), int(H * 0.07)
    esc_x = W // 2 - esc_w // 2
    esc_y = int(H * 0.72)
    pygame.draw.rect(screen_surface, WHITE, (esc_x, esc_y, esc_w, back_h), border_radius=8)
    esc_text = FONT_M.render("Back", True, BLACK)
    screen_surface.blit(esc_text, (esc_x + esc_w // 2 - esc_text.get_width() // 2, esc_y + back_h // 2 - esc_text.get_height() // 2))
    return pygame.Rect(esc_x, esc_y, esc_w, back_h)


def render_gameplay(screen_surface, W, H, FONT_L, FONT_M, FONT_S):
    screen_surface.fill(LIGHT_BG)
    title = FONT_L.render("Gameplay Screen", True, BLACK)
    screen_surface.blit(title, title.get_rect(center=(W // 2, H * 0.12)))

    total_points = sum(item["points"] for item in level_results.values())
    score_text = FONT_S.render(f"Total Points: {total_points}", True, BLACK)
    screen_surface.blit(score_text, (W // 2 - score_text.get_width() // 2, int(H * 0.18)))

    buttons = get_level_button_positions(W, H)
    for item in buttons:
        rect = item["rect"]
        level_num = item["level"]
        pygame.draw.rect(screen_surface, WHITE, rect, border_radius=8)
        label = f"Level {level_num}"
        label_surf = FONT_M.render(label, True, BLACK)
        label_rect = label_surf.get_rect(center=(rect.centerx, rect.centery - 8))
        screen_surface.blit(label_surf, label_rect)

        if level_num in level_results:
            points_surf = FONT_S.render(f"Points: {level_results[level_num]['points']}", True, GREEN)
            screen_surface.blit(points_surf, (rect.centerx - points_surf.get_width() // 2, rect.centery + 18))
        else:
            status_surf = FONT_S.render("Ready", True, DARK_GRAY)
            screen_surface.blit(status_surf, (rect.centerx - status_surf.get_width() // 2, rect.centery + 18))

    back_w, back_h = int(W * 0.4), int(H * 0.07)
    back_x = W // 2 - back_w // 2
    back_y = int(H * 0.82)
    back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
    pygame.draw.rect(screen_surface, WHITE, back_rect, border_radius=8)
    back_text = FONT_M.render("Back", True, BLACK)
    screen_surface.blit(back_text, (back_x + back_w // 2 - back_text.get_width() // 2, back_y + back_h // 2 - back_text.get_height() // 2))
    return buttons, back_rect


def render_level_screen(screen_surface, W, H, FONT_L, FONT_M, FONT_S, level_num):
    challenge = ensure_challenge(level_num)
    screen_surface.fill(LIGHT_BG)

    theme_txt = FONT_M.render(challenge["theme"], True, BLACK)
    screen_surface.blit(theme_txt, (W // 2 - theme_txt.get_width() // 2, int(H * 0.05)))

    # Timer box
    if not challenge["time_up"]:
        seconds_passed = (pygame.time.get_ticks() - challenge["start_ticks"]) / 1000
        time_left = max(0, int(challenge["stage_duration"] - seconds_passed))
        if time_left == 0:
            challenge["time_up"] = True
    else:
        time_left = 0

    minutes = time_left // 60
    seconds = time_left % 60
    timer_string = f"{minutes:02d}:{seconds:02d}"
    timer_color = (200, 50, 50) if time_left <= 15 else (60, 60, 60)
    box_w, box_h = int(W * 0.22), int(H * 0.06)
    box_x = W - int(W * 0.08) - box_w
    box_y = int(H * 0.10)
    pygame.draw.rect(screen_surface, timer_color, (box_x, box_y, box_w, box_h), border_radius=8, width=2)
    timer_surf = FONT_M.render(timer_string, True, timer_color)
    timer_rect = timer_surf.get_rect(center=(box_x + box_w // 2, box_y + box_h // 2))
    screen_surface.blit(timer_surf, timer_rect)

    # Words found text
    found_count = len(challenge["found_words"])
    words_text = FONT_S.render(f"Words Found: {found_count}/{len(challenge['words'])}", True, DARK_GRAY)
    screen_surface.blit(words_text, (W // 2 - words_text.get_width() // 2, int(H * 0.17)))

    # Board setup
    GRID_AREA_WIDTH = min(W, H) * 0.72
    CELL_SIZE = int(GRID_AREA_WIDTH / (GRID_SIZE + 0.2))
    PADDING = int(CELL_SIZE * 0.12)
    START_X = (W - (GRID_SIZE * (CELL_SIZE + PADDING) - PADDING)) // 2
    START_Y = int(H * 0.26)

    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            cell_x = START_X + col * (CELL_SIZE + PADDING)
            cell_y = START_Y + row * (CELL_SIZE + PADDING)

            bg_color = WHITE
            text_color = BLACK
            if (row, col) in challenge["selected_cells"]:
                bg_color = SOFT_BLUE
            elif any((row, col) in path for path in challenge["solved_paths"]):
                bg_color = GRAY
                text_color = DARK_GRAY

            pygame.draw.rect(screen_surface, bg_color, (cell_x, cell_y, CELL_SIZE, CELL_SIZE), border_radius=int(CELL_SIZE * 0.22))
            pygame.draw.rect(screen_surface, (210, 210, 200), (cell_x, cell_y, CELL_SIZE, CELL_SIZE), border_radius=int(CELL_SIZE * 0.22), width=1)

            letter_surf = FONT_M.render(challenge["grid"][row][col], True, text_color)
            letter_rect = letter_surf.get_rect(center=(cell_x + CELL_SIZE // 2, cell_y + CELL_SIZE // 2))
            screen_surface.blit(letter_surf, letter_rect)

    # Back button
    back_w, back_h = int(W * 0.42), int(H * 0.065)
    back_x = W // 2 - back_w // 2
    back_y = int(H * 0.82)
    back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
    pygame.draw.rect(screen_surface, WHITE, back_rect, border_radius=8)
    back_text = FONT_M.render("Back", True, BLACK)
    screen_surface.blit(back_text, (back_x + back_w // 2 - back_text.get_width() // 2, back_y + back_h // 2 - back_text.get_height() // 2))

    # Win/Loss overlay
    if len(challenge["found_words"]) == len(challenge["words"]) or challenge["time_up"]:
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 200))
        screen_surface.blit(overlay, (0, 0))

        msg = "YOU WIN!" if len(challenge["found_words"]) == len(challenge["words"]) else "TIME'S UP!"
        color = GREEN if "WIN" in msg else RED
        finish_surf = FONT_L.render(msg, True, color)
        screen_surface.blit(finish_surf, finish_surf.get_rect(center=(W // 2, H // 2)))

        if len(challenge["found_words"]) == len(challenge["words"]) and level_num not in level_results:
            finalize_level(level_num, challenge)

    return back_rect, START_X, START_Y, CELL_SIZE, PADDING


# ---------------------------
# MAIN LOOP
# ---------------------------
running = True
while running:
    W, H = screen.get_width(), screen.get_height()
    FONT_L = get_font(int(H * 0.06), bold=True)
    FONT_M = get_font(int(max(14, H * 0.032)), bold=True)
    FONT_S = get_font(int(max(11, H * 0.024)))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if current_state == "HOME_MENU":
                menu_data = render_menu(screen, W, H, FONT_L, FONT_M)
                if menu_data["settings_rect"].collidepoint(event.pos):
                    current_state = "SETTINGS_MENU"
                elif menu_data["start_rect"].collidepoint(event.pos):
                    current_state = "GAMEPLAY"

            elif current_state == "SETTINGS_MENU":
                settings_rect = render_settings(screen, W, H, FONT_L, FONT_M)
                if settings_rect.collidepoint(event.pos):
                    current_state = "HOME_MENU"

            elif current_state == "GAMEPLAY":
                buttons, back_rect = render_gameplay(screen, W, H, FONT_L, FONT_M, FONT_S)
                if back_rect.collidepoint(event.pos):
                    current_state = "HOME_MENU"
                for button in buttons:
                    if button["rect"].collidepoint(event.pos):
                        current_state = f"LEVEL_{button['level']}"
                        break

            elif current_state.startswith("LEVEL_"):
                level_num = int(current_state.split("_")[1])
                challenge = ensure_challenge(level_num)
                _, START_X, START_Y, CELL_SIZE, PADDING = render_level_screen(screen, W, H, FONT_L, FONT_M, FONT_S, level_num)
                back_w, back_h = int(W * 0.42), int(H * 0.065)
                back_x = W // 2 - back_w // 2
                back_y = int(H * 0.82)
                back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
                if back_rect.collidepoint(event.pos):
                    current_state = "GAMEPLAY"
                    continue

                # Board interactions
                if challenge["time_up"]:
                    continue

                cell = get_cell_from_position(event.pos, START_X, START_Y, CELL_SIZE, PADDING)
                if cell:
                    if any(cell in path for path in challenge["solved_paths"]):
                        continue
                    challenge["is_selecting"] = True
                    challenge["selected_cells"] = [cell]

        elif event.type == pygame.MOUSEMOTION:
            if current_state.startswith("LEVEL_"):
                level_num = int(current_state.split("_")[1])
                challenge = ensure_challenge(level_num)
                if challenge["is_selecting"] and not challenge["time_up"]:
                    _, START_X, START_Y, CELL_SIZE, PADDING = render_level_screen(screen, W, H, FONT_L, FONT_M, FONT_S, level_num)
                    cell = get_cell_from_position(event.pos, START_X, START_Y, CELL_SIZE, PADDING)
                    if cell and cell not in challenge["selected_cells"]:
                        if any(cell in path for path in challenge["solved_paths"]):
                            continue
                        test_path = challenge["selected_cells"] + [cell]
                        if len(test_path) >= 2:
                            if straight_line_ok(test_path):
                                last_r, last_c = challenge["selected_cells"][-1]
                                if abs(cell[0] - last_r) <= 1 and abs(cell[1] - last_c) <= 1:
                                    challenge["selected_cells"].append(cell)

        elif event.type == pygame.MOUSEBUTTONUP:
            if current_state.startswith("LEVEL_"):
                level_num = int(current_state.split("_")[1])
                challenge = ensure_challenge(level_num)
                if challenge["is_selecting"]:
                    challenge["is_selecting"] = False
                    if len(challenge["selected_cells"]) > 1:
                        current_word = "".join([challenge["grid"][r][c] for r, c in challenge["selected_cells"]])
                        reversed_word = current_word[::-1]
                        if current_word in challenge["words"] and current_word not in challenge["found_words"]:
                            challenge["found_words"].append(current_word)
                            challenge["solved_paths"].append(list(challenge["selected_cells"]))
                        elif reversed_word in challenge["words"] and reversed_word not in challenge["found_words"]:
                            challenge["found_words"].append(reversed_word)
                            challenge["solved_paths"].append(list(challenge["selected_cells"]))
                    challenge["selected_cells"] = []

    # Draw current state
    if current_state == "HOME_MENU":
        render_menu(screen, W, H, FONT_L, FONT_M)
    elif current_state == "SETTINGS_MENU":
        render_settings(screen, W, H, FONT_L, FONT_M)
    elif current_state == "GAMEPLAY":
        render_gameplay(screen, W, H, FONT_L, FONT_M, FONT_S)
    elif current_state.startswith("LEVEL_"):
        level_num = int(current_state.split("_")[1])
        render_level_screen(screen, W, H, FONT_L, FONT_M, FONT_S, level_num)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
