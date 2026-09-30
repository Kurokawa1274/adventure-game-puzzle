import json
import os
import random
import sys
import pygame

pygame.init()

# =========================================================
# CONFIG
# =========================================================
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
BLUE = (70, 130, 180)
YELLOW = (255, 210, 80)

TOTAL_LEVELS = 6

# =========================================================
# JSON LOADING
# =========================================================
def load_challenges():
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, "challenges.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Missing challenges.json file. Make sure it is in the same folder as game.py.")
        sys.exit()
    except json.JSONDecodeError:
        print("Invalid JSON in challenges.json.")
        sys.exit()

CONFIG = load_challenges()

DEFAULT_LEVEL_PLAN = [
    {"type": "word_search", "difficulty": "easy"},
    {"type": "word_search", "difficulty": "easy"},
    {"type": "word_search", "difficulty": "normal"},
    {"type": "word_search", "difficulty": "normal"},
    {"type": "connections", "difficulty": "hard"},
    {"type": "hangman", "difficulty": "hard"},
]

LEVEL_PLAN = CONFIG.get("level_plan", DEFAULT_LEVEL_PLAN)
DIFFICULTIES = CONFIG.get("difficulties", {
    "easy": {"time_limit": 90, "grid_size": 7, "word_count": 4},
    "normal": {"time_limit": 60, "grid_size": 8, "word_count": 5},
    "hard": {"time_limit": 40, "grid_size": 9, "word_count": 6},
})

# Theme trackers so they do not repeat
USED_THEMES = {
    "word_search": set(),
    "connections": set(),
    "hangman": set(),
}

level_results = {}
level_data_cache = {}
current_state = "HOME_MENU"

# =========================================================
# HELPERS
# =========================================================
def get_font(size, bold=False):
    return pygame.font.SysFont("Arial", size, bold=bold)

def get_theme_pool(challenge_type):
    if challenge_type == "word_search":
        return CONFIG.get("themes", [])
    if challenge_type == "connections":
        return CONFIG.get("connections_challenges", [])
    if challenge_type == "hangman":
        return CONFIG.get("hangman_challenges", [])
    return []

def pick_unused_theme(challenge_type):
    pool = get_theme_pool(challenge_type)
    if not pool:
        return None

    used = USED_THEMES.get(challenge_type, set())
    candidates = [t for t in pool if (t.get("name") or t.get("theme")) not in used]

    if not candidates:
        candidates = pool

    chosen = random.choice(candidates)
    key = chosen.get("name") or chosen.get("theme")
    if key:
        USED_THEMES[challenge_type].add(key)
    return chosen

def get_level_definition(level_number):
    idx = level_number - 1
    if idx < 0 or idx >= len(LEVEL_PLAN):
        return {"type": "word_search", "difficulty": "easy"}
    return LEVEL_PLAN[idx]

def get_level_points(level_number):
    result = level_results.get(level_number)
    if not result:
        return 0
    return int(result.get("points", 0))

def get_total_points():
    return sum(get_level_points(i) for i in range(1, TOTAL_LEVELS + 1))

def level_button_positions(W, H):
    b_w, b_h = int(W * 0.6), int(H * 0.07)
    b_x = W // 2 - b_w // 2
    start_y = int(H * 0.24)
    gap = int(H * 0.09)
    positions = []
    for i in range(TOTAL_LEVELS):
        y = start_y + i * (b_h + gap)
        positions.append({
            "rect": pygame.Rect(b_x, y, b_w, b_h),
            "level": i + 1,
        })
    return positions

# =========================================================
# WORD SEARCH CHALLENGE
# =========================================================
def make_word_search_grid(words, grid_size):
    grid = [["" for _ in range(grid_size)] for _ in range(grid_size)]
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]

    def can_place(word, r, c, dr, dc):
        for i in range(len(word)):
            rr = r + dr * i
            cc = c + dc * i
            if not (0 <= rr < grid_size and 0 <= cc < grid_size):
                return False
            if grid[rr][cc] != "" and grid[rr][cc] != word[i]:
                return False
        return True

    for word in words:
        placed = False
        for _ in range(400):
            r = random.randint(0, grid_size - 1)
            c = random.randint(0, grid_size - 1)
            dr, dc = random.choice(directions)
            if can_place(word, r, c, dr, dc):
                for i in range(len(word)):
                    rr = r + dr * i
                    cc = c + dc * i
                    grid[rr][cc] = word[i]
                placed = True
                break
        if not placed:
            return None

    for r in range(grid_size):
        for c in range(grid_size):
            if grid[r][c] == "":
                grid[r][c] = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    return grid

def build_word_search_challenge(level_num, difficulty_name):
    diff_cfg = DIFFICULTIES.get(difficulty_name, DIFFICULTIES["easy"])
    theme = pick_unused_theme("word_search")
    if not theme:
        theme = {"theme": "THEME: CUSTOM", "words": ["WORD"]}

    words = list(theme.get("words", []))
    if len(words) < 2:
        words = ["WORD", "GRID", "PUZZLE", "GAME"]

    chosen_words = words[:max(3, diff_cfg.get("word_count", 4))]
    random.shuffle(chosen_words)

    grid_size = diff_cfg.get("grid_size", 7)
    grid = make_word_search_grid(chosen_words, grid_size)
    if grid is None:
        return build_word_search_challenge(level_num, difficulty_name)

    challenge = {
        "type": "word_search",
        "theme": theme.get("theme") or theme.get("name"),
        "words": chosen_words,
        "grid": grid,
        "difficulty": difficulty_name,
        "grid_size": grid_size,
        "time_limit": diff_cfg.get("time_limit", 90),
        "start_ticks": pygame.time.get_ticks(),
        "time_up": False,
        "selected_cells": [],
        "solved_paths": [],
        "found_words": [],
        "is_selecting": False,
    }
    return challenge

def straight_line_ok(path):
    if len(path) <= 2:
        return True

    r0, c0 = path[0]
    r1, c1 = path[1]
    dr = r1 - r0
    dc = c1 - c0

    for i in range(1, len(path)):
        curr_r, curr_c = path[i]
        prev_r, prev_c = path[i - 1]
        if (curr_r - prev_r) != dr or (curr_c - prev_c) != dc:
            return False
    return True

def get_cell_from_position(pos, start_x, start_y, cell_size, padding, grid_size):
    x, y = pos
    for row in range(grid_size):
        for col in range(grid_size):
            cx = start_x + col * (cell_size + padding)
            cy = start_y + row * (cell_size + padding)
            if cx <= x <= cx + cell_size and cy <= y <= cy + cell_size:
                return row, col
    return None

# =========================================================
# CONNECTIONS CHALLENGE
# =========================================================
def build_connections_challenge(level_num, difficulty_name):
    theme = pick_unused_theme("connections")
    if not theme:
        theme = {"theme": "THEME: CUSTOM", "groups": [{"category": "Group A", "items": ["A", "B", "C", "D"]}]}

    groups = theme.get("groups", [])
    if not groups:
        groups = [{"category": "Group 1", "items": ["A", "B", "C", "D"]}]

    board_items = []
    group_lookup = {}
    for group in groups:
        for item in group["items"]:
            item_clean = str(item).upper()
            group_lookup[item_clean] = group["category"]
            board_items.append(item_clean)

    random.shuffle(board_items)

    challenge = {
        "type": "connections",
        "theme": theme.get("theme") or theme.get("name"),
        "difficulty": difficulty_name,
        "groups": groups,
        "board_items": board_items,
        "group_lookup": group_lookup,
        "selected": [],
        "solved_groups": [],
        "time_up": False,
        "start_ticks": pygame.time.get_ticks(),
        "time_limit": DIFFICULTIES.get(difficulty_name, DIFFICULTIES["easy"]).get("time_limit", 60),
    }
    return challenge

# =========================================================
# HANGMAN CHALLENGE
# =========================================================
def build_hangman_challenge(level_num, difficulty_name):
    theme = pick_unused_theme("hangman")
    if not theme:
        theme = {"theme": "THEME: CUSTOM", "words": ["PUZZLE", "GAME", "LEVEL"]}

    words = theme.get("words", [])
    selected_word = random.choice(words).upper()
    challenge = {
        "type": "hangman",
        "theme": theme.get("theme") or theme.get("name"),
        "difficulty": difficulty_name,
        "word": selected_word,
        "revealed": ["_"] * len(selected_word),
        "guessed": set(),
        "wrong_count": 0,
        "max_wrong": 6,
        "letters": [chr(i) for i in range(ord("A"), ord("Z") + 1)],
        "time_up": False,
        "start_ticks": pygame.time.get_ticks(),
        "time_limit": DIFFICULTIES.get(difficulty_name, DIFFICULTIES["easy"]).get("time_limit", 60),
    }
    return challenge

# =========================================================
# LEVEL CREATION / CACHE
# =========================================================
def ensure_challenge(level_number, force_new=False):
    """
    Get or create challenge for a level.
    If force_new=True, always create a fresh challenge (for re-entering a level).
    """
    if force_new or level_number not in level_data_cache:
        level_def = get_level_definition(level_number)
        challenge_type = level_def.get("type", "word_search")
        difficulty = level_def.get("difficulty", "easy")

        if challenge_type == "word_search":
            challenge = build_word_search_challenge(level_number, difficulty)
        elif challenge_type == "connections":
            challenge = build_connections_challenge(level_number, difficulty)
        elif challenge_type == "hangman":
            challenge = build_hangman_challenge(level_number, difficulty)
        else:
            challenge = build_word_search_challenge(level_number, difficulty)

        level_data_cache[level_number] = challenge

    return level_data_cache[level_number]

# =========================================================
# POINTS / COMPLETION
# =========================================================
def get_challenge_status(challenge):
    if challenge["type"] == "word_search":
        found_total = len(challenge.get("found_words", []))
        total_words = len(challenge.get("words", []))
        return found_total >= total_words or challenge.get("time_up", False)
    if challenge["type"] == "connections":
        return len(challenge.get("solved_groups", [])) >= len(challenge.get("groups", [])) or challenge.get("time_up", False)
    if challenge["type"] == "hangman":
        return all(letter != "_" for letter in challenge.get("revealed", [])) or challenge.get("time_up", False)

def calculate_points(challenge, level_number):
    difficulty = challenge.get("difficulty", "easy")
    level_def = get_level_definition(level_number)
    difficulty_cfg = DIFFICULTIES.get(difficulty, DIFFICULTIES["easy"])
    mult = {"easy": 1.0, "normal": 1.4, "hard": 1.8}[difficulty]

    if challenge["type"] == "word_search":
        total_words = len(challenge.get("words", []))
        found_words = len(challenge.get("found_words", []))
        remaining = max(0, challenge["time_limit"] - max(0, int((pygame.time.get_ticks() - challenge["start_ticks"]) / 1000)))
        base = 200 * mult
        progress = int((found_words / max(1, total_words)) * 150)
        return int(base + progress + remaining * 2)

    if challenge["type"] == "connections":
        solved = len(challenge.get("solved_groups", []))
        total = len(challenge.get("groups", []))
        base = 250 * mult
        return int(base + solved * 120 + (total - solved) * 25)

    if challenge["type"] == "hangman":
        word_len = len(challenge.get("word", ""))
        guessed = sum(1 for ch in challenge.get("revealed", []) if ch != "_")
        base = 300 * mult
        remaining = max(0, challenge.get("max_wrong", 6) - challenge.get("wrong_count", 0))
        return int(base + guessed * 20 + remaining * 30)

    return 100

def finalize_level(level_number, challenge):
    if level_number in level_results:
        return

    won = get_challenge_status(challenge)
    points = calculate_points(challenge, level_number) if won else 0

    level_results[level_number] = {
        "points": points,
        "type": challenge["type"],
        "theme": challenge.get("theme"),
        "difficulty": challenge.get("difficulty", "easy"),
        "won": won,
    }

# =========================================================
# DRAW FUNCTIONS
# =========================================================
def draw_text(surface, text, font, color, x, y):
    text_obj = font.render(text, True, color)
    text_rect = text_obj.get_rect()
    text_rect.topleft = (x, y)
    surface.blit(text_obj, text_rect)

def render_home_menu(W, H, FONT_L, FONT_M):
    screen.fill(LIGHT_BG)

    title = FONT_L.render("Home Menu", True, BLACK)
    screen.blit(title, title.get_rect(center=(W // 2, H * 0.18)))

    settings_w, settings_h = int(W * 0.6), int(H * 0.08)
    settings_x = W // 2 - settings_w // 2
    settings_y = int(H * 0.38)
    pygame.draw.rect(screen, WHITE, (settings_x, settings_y, settings_w, settings_h), border_radius=8)
    settings_text = FONT_M.render("Go to Settings", True, BLACK)
    screen.blit(settings_text, (settings_x + settings_w // 2 - settings_text.get_width() // 2,
                               settings_y + settings_h // 2 - settings_text.get_height() // 2))

    start_w, start_h = int(W * 0.6), int(H * 0.08)
    start_x = W // 2 - start_w // 2
    start_y = int(H * 0.53)
    pygame.draw.rect(screen, WHITE, (start_x, start_y, start_w, start_h), border_radius=8)
    start_text = FONT_M.render("Start Game", True, BLACK)
    screen.blit(start_text, (start_x + start_w // 2 - start_text.get_width() // 2,
                            start_y + start_h // 2 - start_text.get_height() // 2))

    return {
        "settings_rect": pygame.Rect(settings_x, settings_y, settings_w, settings_h),
        "start_rect": pygame.Rect(start_x, start_y, start_w, start_h),
    }

def render_settings_menu(W, H, FONT_L, FONT_M):
    screen.fill(LIGHT_BG)

    title = FONT_L.render("Settings Menu", True, BLACK)
    screen.blit(title, title.get_rect(center=(W // 2, H * 0.18)))

    back_w, back_h = int(W * 0.4), int(H * 0.07)
    back_x = W // 2 - back_w // 2
    back_y = int(H * 0.72)
    pygame.draw.rect(screen, WHITE, (back_x, back_y, back_w, back_h), border_radius=8)
    back_text = FONT_M.render("Back", True, BLACK)
    screen.blit(back_text, (back_x + back_w // 2 - back_text.get_width() // 2,
                           back_y + back_h // 2 - back_text.get_height() // 2))
    return pygame.Rect(back_x, back_y, back_w, back_h)

def render_gameplay_screen(W, H, FONT_L, FONT_M, FONT_S):
    screen.fill(LIGHT_BG)

    title = FONT_L.render("Gameplay Screen", True, BLACK)
    screen.blit(title, title.get_rect(center=(W // 2, H * 0.12)))

    total_points = get_total_points()
    score_text = FONT_S.render(f"Total Points: {total_points}", True, BLACK)
    screen.blit(score_text, (W // 2 - score_text.get_width() // 2, int(H * 0.18)))

    buttons = level_button_positions(W, H)
    for item in buttons:
        rect = item["rect"]
        level_num = item["level"]

        pygame.draw.rect(screen, WHITE, rect, border_radius=8)

        label = f"Level {level_num}"
        label_surf = FONT_M.render(label, True, BLACK)
        screen.blit(label_surf, (rect.centerx - label_surf.get_width() // 2, rect.centery - 7))

        result = level_results.get(level_num)
        if result:
            pts_surf = FONT_S.render(f"Pts: {result.get('points', 0)}", True, GREEN)
            screen.blit(pts_surf, (rect.centerx - pts_surf.get_width() // 2, rect.centery + 17))
        else:
            status_surf = FONT_S.render("Ready", True, DARK_GRAY)
            screen.blit(status_surf, (rect.centerx - status_surf.get_width() // 2, rect.centery + 17))

    # Back button - positioned BELOW all level buttons
    back_w, back_h = int(W * 0.4), int(H * 0.07)
    back_x = W // 2 - back_w // 2
    back_y = int(H * 0.93)  # Moved to bottom
    back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
    pygame.draw.rect(screen, WHITE, back_rect, border_radius=8)
    back_text = FONT_M.render("Back", True, BLACK)
    screen.blit(back_text, (back_x + back_w // 2 - back_text.get_width() // 2,
                           back_y + back_h // 2 - back_text.get_height() // 2))

    return buttons, back_rect

# =========================================================
# RENDER CHALLENGES
# =========================================================
def render_word_search_screen(level_num, challenge, W, H, FONT_L, FONT_M, FONT_S):
    screen.fill(LIGHT_BG)

    # Theme
    theme_text = FONT_M.render(challenge["theme"], True, BLACK)
    screen.blit(theme_text, (W // 2 - theme_text.get_width() // 2, int(H * 0.05)))

    # Timer
    if challenge.get("time_up", False) is False:
        elapsed = (pygame.time.get_ticks() - challenge["start_ticks"]) / 1000
        time_left = max(0, int(challenge["time_limit"] - elapsed))
        if time_left <= 0:
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
    pygame.draw.rect(screen, timer_color, (box_x, box_y, box_w, box_h), border_radius=8, width=2)
    timer_surf = FONT_M.render(timer_string, True, timer_color)
    screen.blit(timer_surf, (box_x + box_w // 2 - timer_surf.get_width() // 2,
                             box_y + box_h // 2 - timer_surf.get_height() // 2))

    # Found count
    found_count = len(challenge["found_words"])
    status_text = FONT_S.render(f"Words Found: {found_count}/{len(challenge['words'])}", True, DARK_GRAY)
    screen.blit(status_text, (W // 2 - status_text.get_width() // 2, int(H * 0.17)))

    grid_size = challenge["grid_size"]
    board_area_w = min(W, H) * 0.75
    cell_size = int(board_area_w / (grid_size + 0.25))
    padding = int(cell_size * 0.12)
    start_x = (W - ((grid_size * (cell_size + padding)) - padding)) // 2
    start_y = int(H * 0.26)

    for row in range(grid_size):
        for col in range(grid_size):
            rect_x = start_x + col * (cell_size + padding)
            rect_y = start_y + row * (cell_size + padding)

            bg = WHITE
            text_color = BLACK
            if (row, col) in challenge["selected_cells"]:
                bg = SOFT_BLUE
            elif any((row, col) in path for path in challenge["solved_paths"]):
                bg = GRAY
                text_color = DARK_GRAY

            pygame.draw.rect(screen, bg, (rect_x, rect_y, cell_size, cell_size), border_radius=int(cell_size * 0.2))
            pygame.draw.rect(screen, (210, 210, 200), (rect_x, rect_y, cell_size, cell_size),
                             border_radius=int(cell_size * 0.2), width=1)

            letter = challenge["grid"][row][col]
            letter_surf = FONT_M.render(letter, True, text_color)
            screen.blit(letter_surf, (rect_x + cell_size // 2 - letter_surf.get_width() // 2,
                                     rect_y + cell_size // 2 - letter_surf.get_height() // 2))

    # Back button
    back_w, back_h = int(W * 0.42), int(H * 0.065)
    back_x = W // 2 - back_w // 2
    back_y = int(H * 0.88)
    back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
    pygame.draw.rect(screen, WHITE, back_rect, border_radius=8)
    back_text = FONT_M.render("Back", True, BLACK)
    screen.blit(back_text, (back_x + back_w // 2 - back_text.get_width() // 2,
                           back_y + back_h // 2 - back_text.get_height() // 2))

    if len(challenge["found_words"]) == len(challenge["words"]) or challenge["time_up"]:
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 200))
        screen.blit(overlay, (0, 0))

        msg = "YOU WIN!" if len(challenge["found_words"]) == len(challenge["words"]) else "TIME'S UP!"
        color = GREEN if "WIN" in msg else RED
        finish_surf = FONT_L.render(msg, True, color)
        screen.blit(finish_surf, finish_surf.get_rect(center=(W // 2, H // 2)))

        if len(challenge["found_words"]) == len(challenge["words"]) and level_num not in level_results:
            finalize_level(level_num, challenge)

    return back_rect, start_x, start_y, cell_size, padding, grid_size

def render_connections_screen(level_num, challenge, W, H, FONT_L, FONT_M, FONT_S):
    screen.fill(LIGHT_BG)

    # Header
    theme_text = FONT_M.render(challenge["theme"], True, BLACK)
    screen.blit(theme_text, (W // 2 - theme_text.get_width() // 2, int(H * 0.045)))

    # Timer
    if not challenge.get("time_up", False):
        elapsed = (pygame.time.get_ticks() - challenge["start_ticks"]) / 1000
        time_left = max(0, int(challenge["time_limit"] - elapsed))
        if time_left <= 0:
            challenge["time_up"] = True
    else:
        time_left = 0

    minutes = time_left // 60
    seconds = time_left % 60
    timer_string = f"{minutes:02d}:{seconds:02d}"
    timer_color = (200, 50, 50) if time_left <= 15 else (60, 60, 60)

    box_w, box_h = int(W * 0.22), int(H * 0.06)
    box_x = W - int(W * 0.08) - box_w
    box_y = int(H * 0.09)
    pygame.draw.rect(screen, timer_color, (box_x, box_y, box_w, box_h), border_radius=8, width=2)
    timer_surf = FONT_M.render(timer_string, True, timer_color)
    screen.blit(timer_surf, (box_x + box_w // 2 - timer_surf.get_width() // 2,
                             box_y + box_h // 2 - timer_surf.get_height() // 2))

    # Categories solved
    solved_text = FONT_S.render(f"Solved: {len(challenge['solved_groups'])}/{len(challenge['groups'])}", True, DARK_GRAY)
    screen.blit(solved_text, (W // 2 - solved_text.get_width() // 2, int(H * 0.12)))

    # Board layout
    board_items = challenge["board_items"]
    columns = 3
    rows = (len(board_items) + columns - 1) // columns
    cell_w = int(W * 0.24)
    cell_h = int(H * 0.08)
    gap_x = int(W * 0.05)
    gap_y = int(H * 0.03)
    start_x = (W - (columns * cell_w + (columns - 1) * gap_x)) // 2
    start_y = int(H * 0.18)

    button_rects = []
    for index, item in enumerate(board_items):
        col = index % columns
        row = index // columns
        x = start_x + col * (cell_w + gap_x)
        y = start_y + row * (cell_h + gap_y)
        rect = pygame.Rect(x, y, cell_w, cell_h)

        is_selected = item in challenge["selected"]
        is_solved = any(item in group["items"] for group in challenge["groups"] if group["category"] in challenge["solved_groups"])

        if is_selected:
            color = SOFT_BLUE
        elif is_solved:
            color = GRAY
        else:
            color = WHITE

        pygame.draw.rect(screen, color, rect, border_radius=8)
        pygame.draw.rect(screen, (200, 200, 200), rect, border_radius=8, width=1)

        label = FONT_S.render(item, True, BLACK)
        screen.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))

        button_rects.append((rect, item))

    # Back button
    back_w, back_h = int(W * 0.42), int(H * 0.065)
    back_x = W // 2 - back_w // 2
    back_y = int(H * 0.88)
    back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
    pygame.draw.rect(screen, WHITE, back_rect, border_radius=8)
    back_text = FONT_M.render("Back", True, BLACK)
    screen.blit(back_text, (back_x + back_w // 2 - back_text.get_width() // 2,
                           back_y + back_h // 2 - back_text.get_height() // 2))

    # Win overlay
    if len(challenge["solved_groups"]) >= len(challenge["groups"]) or challenge.get("time_up", False):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 200))
        screen.blit(overlay, (0, 0))

        msg = "YOU WIN!" if len(challenge["solved_groups"]) >= len(challenge["groups"]) else "TIME'S UP!"
        color = GREEN if "WIN" in msg else RED
        finish_surf = FONT_L.render(msg, True, color)
        screen.blit(finish_surf, finish_surf.get_rect(center=(W // 2, H // 2)))

        if len(challenge["solved_groups"]) >= len(challenge["groups"]) and level_num not in level_results:
            finalize_level(level_num, challenge)

    return back_rect, button_rects

def render_hangman_screen(level_num, challenge, W, H, FONT_L, FONT_M, FONT_S):
    screen.fill(LIGHT_BG)

    # Theme
    theme_text = FONT_M.render(challenge["theme"], True, BLACK)
    screen.blit(theme_text, (W // 2 - theme_text.get_width() // 2, int(H * 0.05)))

    # Timer
    if not challenge.get("time_up", False):
        elapsed = (pygame.time.get_ticks() - challenge["start_ticks"]) / 1000
        time_left = max(0, int(challenge["time_limit"] - elapsed))
        if time_left <= 0:
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
    pygame.draw.rect(screen, timer_color, (box_x, box_y, box_w, box_h), border_radius=8, width=2)
    timer_surf = FONT_M.render(timer_string, True, timer_color)
    screen.blit(timer_surf, (box_x + box_w // 2 - timer_surf.get_width() // 2,
                             box_y + box_h // 2 - timer_surf.get_height() // 2))

    # Word reveal
    word_display = " ".join(challenge["revealed"])
    reveal_surf = FONT_L.render(word_display, True, BLACK)
    screen.blit(reveal_surf, reveal_surf.get_rect(center=(W // 2, H * 0.25)))

    # Wrong guesses
    wrong_text = FONT_S.render(f"Wrong guesses: {challenge['wrong_count']}/{challenge['max_wrong']}", True, RED)
    screen.blit(wrong_text, (W // 2 - wrong_text.get_width() // 2, int(H * 0.34)))

    # Hangman drawing
    center_x = W // 2
    base_y = int(H * 0.55)
    # Create a simple hanging scene
    if challenge["wrong_count"] >= 1:
        pygame.draw.line(screen, BLACK, (center_x - 90, base_y), (center_x + 90, base_y), 4)
    if challenge["wrong_count"] >= 2:
        pygame.draw.line(screen, BLACK, (center_x - 60, base_y), (center_x - 60, base_y - 130), 4)
    if challenge["wrong_count"] >= 3:
        pygame.draw.line(screen, BLACK, (center_x - 60, base_y - 130), (center_x + 20, base_y - 130), 4)
    if challenge["wrong_count"] >= 4:
        pygame.draw.line(screen, BLACK, (center_x + 20, base_y - 130), (center_x + 20, base_y - 90), 4)
    if challenge["wrong_count"] >= 5:
        pygame.draw.circle(screen, BLACK, (center_x + 20, base_y - 70), 18, 4)
    if challenge["wrong_count"] >= 6:
        pygame.draw.line(screen, BLACK, (center_x + 20, base_y - 50), (center_x + 20, base_y - 10), 4)
        pygame.draw.line(screen, BLACK, (center_x + 20, base_y - 40), (center_x + 40, base_y - 25), 4)
        pygame.draw.line(screen, BLACK, (center_x + 20, base_y - 40), (center_x, base_y - 25), 4)
        pygame.draw.line(screen, BLACK, (center_x + 20, base_y - 10), (center_x + 40, base_y + 15), 4)
        pygame.draw.line(screen, BLACK, (center_x + 20, base_y - 10), (center_x, base_y + 15), 4)

    # Letter buttons
    letters = challenge["letters"]
    cols = 7
    gap = 8
    cell_w = int((W * 0.7) / cols)
    start_x = (W - (cols * cell_w + (cols - 1) * gap)) // 2
    start_y = int(H * 0.68)
    letter_rects = []

    for i, letter in enumerate(letters):
        row = i // cols
        col = i % cols
        x = start_x + col * (cell_w + gap)
        y = start_y + row * (cell_h := int(H * 0.06))
        rect = pygame.Rect(x, y, cell_w - 8, cell_h - 8)

        button_color = GRAY if letter in challenge["guessed"] else WHITE
        text_color = BLACK
        pygame.draw.rect(screen, button_color, rect, border_radius=6)
        letter_text = FONT_M.render(letter, True, text_color)
        screen.blit(letter_text, (rect.centerx - letter_text.get_width() // 2,
                                 rect.centery - letter_text.get_height() // 2))
        letter_rects.append((rect, letter))

    # Back button
    back_w, back_h = int(W * 0.42), int(H * 0.065)
    back_x = W // 2 - back_w // 2
    back_y = int(H * 0.92)
    back_rect = pygame.Rect(back_x, back_y, back_w, back_h)
    pygame.draw.rect(screen, WHITE, back_rect, border_radius=8)
    back_text = FONT_M.render("Back", True, BLACK)
    screen.blit(back_text, (back_x + back_w // 2 - back_text.get_width() // 2,
                           back_y + back_h // 2 - back_text.get_height() // 2))

    # Win / loss
    word_complete = all(ch != "_" for ch in challenge["revealed"])
    if word_complete or challenge["time_up"] or challenge["wrong_count"] >= challenge["max_wrong"]:
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 200))
        screen.blit(overlay, (0, 0))

        msg = "YOU WIN!" if word_complete else "TIME'S UP!"
        color = GREEN if word_complete else RED
        finish_surf = FONT_L.render(msg, True, color)
        screen.blit(finish_surf, finish_surf.get_rect(center=(W // 2, H // 2)))

        if word_complete and level_num not in level_results:
            finalize_level(level_num, challenge)

    return back_rect, letter_rects

# =========================================================
# MAIN PROGRAM LOOP
# =========================================================
running = True
entering_level = False  # Track if we just entered a level to generate fresh challenge

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
                menu_data = render_home_menu(W, H, FONT_L, FONT_M)
                if menu_data["settings_rect"].collidepoint(event.pos):
                    current_state = "SETTINGS_MENU"
                elif menu_data["start_rect"].collidepoint(event.pos):
                    current_state = "GAMEPLAY"

            elif current_state == "SETTINGS_MENU":
                settings_rect = render_settings_menu(W, H, FONT_L, FONT_M)
                if settings_rect.collidepoint(event.pos):
                    current_state = "HOME_MENU"

            elif current_state == "GAMEPLAY":
                buttons, back_rect = render_gameplay_screen(W, H, FONT_L, FONT_M, FONT_S)
                if back_rect.collidepoint(event.pos):
                    current_state = "HOME_MENU"
                else:
                    for item in buttons:
                        if item["rect"].collidepoint(event.pos):
                            current_state = f"LEVEL_{item['level']}"
                            entering_level = True  # Flag to generate fresh challenge
                            break

            elif current_state.startswith("LEVEL_"):
                level_number = int(current_state.split("_")[1])
                challenge = ensure_challenge(level_number, force_new=entering_level)
                entering_level = False  # Reset flag after generating challenge

                if challenge["type"] == "word_search":
                    back_rect, start_x, start_y, cell_size, padding, grid_size = render_word_search_screen(
                        level_number, challenge, W, H, FONT_L, FONT_M, FONT_S
                    )

                    if back_rect.collidepoint(event.pos):
                        current_state = "GAMEPLAY"
                        continue

                    if challenge["time_up"]:
                        continue

                    cell = get_cell_from_position(event.pos, start_x, start_y, cell_size, padding, grid_size)
                    if cell:
                        if any(cell in path for path in challenge["solved_paths"]):
                            continue
                        challenge["is_selecting"] = True
                        challenge["selected_cells"] = [cell]

                elif challenge["type"] == "connections":
                    back_rect, button_rects = render_connections_screen(level_number, challenge, W, H, FONT_L, FONT_M, FONT_S)

                    if back_rect.collidepoint(event.pos):
                        current_state = "GAMEPLAY"
                        continue

                    for rect, item in button_rects:
                        if rect.collidepoint(event.pos):
                            if item in challenge["selected"]:
                                challenge["selected"].remove(item)
                            else:
                                challenge["selected"].append(item)
                                if len(challenge["selected"]) == 4:
                                    selected_set = set(challenge["selected"])
                                    matched_category = None

                                    for group in challenge["groups"]:
                                        category = group["category"]
                                        group_items = [str(i).upper() for i in group["items"]]
                                        if set(group_items).issubset(selected_set):
                                            matched_category = category
                                            break

                                    if matched_category:
                                        challenge["solved_groups"].append(matched_category)
                                        challenge["selected"] = []
                                    else:
                                        challenge["selected"] = []

                                    challenge["solved_groups"] = list(dict.fromkeys(challenge["solved_groups"]))

                                    if len(challenge["solved_groups"]) >= len(challenge["groups"]):
                                        finalize_level(level_number, challenge)
                            break

                elif challenge["type"] == "hangman":
                    back_rect, letter_rects = render_hangman_screen(level_number, challenge, W, H, FONT_L, FONT_M, FONT_S)

                    if back_rect.collidepoint(event.pos):
                        current_state = "GAMEPLAY"
                        continue

                    for rect, letter in letter_rects:
                        if rect.collidepoint(event.pos):
                            if letter in challenge["guessed"]:
                                break
                            challenge["guessed"].add(letter)
                            if letter in challenge["word"]:
                                for i, ch in enumerate(challenge["word"]):
                                    if ch == letter:
                                        challenge["revealed"][i] = letter
                            else:
                                challenge["wrong_count"] += 1

                            if all(ch != "_" for ch in challenge["revealed"]):
                                finalize_level(level_number, challenge)
                            elif challenge["wrong_count"] >= challenge["max_wrong"]:
                                challenge["time_up"] = True
                                finalize_level(level_number, challenge)
                            break

        elif event.type == pygame.MOUSEMOTION:
            if current_state.startswith("LEVEL_"):
                level_number = int(current_state.split("_")[1])
                challenge = ensure_challenge(level_number)

                if challenge["type"] == "word_search" and challenge["is_selecting"] and not challenge["time_up"]:
                    grid_size = challenge["grid_size"]
                    board_area_w = min(W, H) * 0.75
                    cell_size = int(board_area_w / (grid_size + 0.25))
                    padding = int(cell_size * 0.12)
                    start_x = (screen.get_width() - ((grid_size * (cell_size + padding)) - padding)) // 2
                    start_y = int(screen.get_height() * 0.26)

                    cell = get_cell_from_position(event.pos, start_x, start_y, cell_size, padding, grid_size)
                    if cell and cell not in challenge["selected_cells"]:
                        if any(cell in path for path in challenge["solved_paths"]):
                            continue
                        test_path = challenge["selected_cells"] + [cell]
                        if len(test_path) >= 2 and straight_line_ok(test_path):
                            last_r, last_c = challenge["selected_cells"][-1]
                            if abs(cell[0] - last_r) <= 1 and abs(cell[1] - last_c) <= 1:
                                challenge["selected_cells"].append(cell)

        elif event.type == pygame.MOUSEBUTTONUP:
            if current_state.startswith("LEVEL_"):
                level_number = int(current_state.split("_")[1])
                challenge = ensure_challenge(level_number)
                if challenge["type"] == "word_search" and challenge["is_selecting"]:
                    challenge["is_selecting"] = False
                    if len(challenge["selected_cells"]) > 1:
                        word = "".join(challenge["grid"][r][c] for r, c in challenge["selected_cells"])
                        reversed_word = word[::-1]

                        if word in challenge["words"] and word not in challenge["found_words"]:
                            challenge["found_words"].append(word)
                            challenge["solved_paths"].append(list(challenge["selected_cells"]))
                        elif reversed_word in challenge["words"] and reversed_word not in challenge["found_words"]:
                            challenge["found_words"].append(reversed_word)
                            challenge["solved_paths"].append(list(challenge["selected_cells"]))

                        if len(challenge["found_words"]) >= len(challenge["words"]):
                            finalize_level(level_number, challenge)

                    challenge["selected_cells"] = []

    # DRAW STATE
    if current_state == "HOME_MENU":
        render_home_menu(W, H, FONT_L, FONT_M)
    elif current_state == "SETTINGS_MENU":
        render_settings_menu(W, H, FONT_L, FONT_M)
    elif current_state == "GAMEPLAY":
        render_gameplay_screen(W, H, FONT_L, FONT_M, FONT_S)
    elif current_state.startswith("LEVEL_"):
        level_number = int(current_state.split("_")[1])
        challenge = ensure_challenge(level_number, force_new=entering_level)

        if challenge["type"] == "word_search":
            render_word_search_screen(level_number, challenge, W, H, FONT_L, FONT_M, FONT_S)
        elif challenge["type"] == "connections":
            render_connections_screen(level_number, challenge, W, H, FONT_L, FONT_M, FONT_S)
        elif challenge["type"] == "hangman":
            render_hangman_screen(level_number, challenge, W, H, FONT_L, FONT_M, FONT_S)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
