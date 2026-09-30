import json
import os
import random
import sys
import pygame

pygame.init()
pygame.mixer.init()

# ----------------------------------------
# Game window
# ----------------------------------------
WIDTH, HEIGHT = 480, 720
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Adventure Game Puzzle")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
LIGHT_BG = (240, 238, 233)
DARK_BG = (220, 220, 220)
SOFT_BLUE = (173, 216, 230)
BRIGHT_BLUE = (100, 180, 220)
GRAY = (180, 180, 180)
DARK_GRAY = (100, 100, 100)
GREEN = (46, 139, 87)
BRIGHT_GREEN = (76, 175, 80)
RED = (178, 34, 34)
BRIGHT_RED = (244, 67, 54)
YELLOW = (255, 210, 80)
GOLD = (255, 215, 0)
PURPLE = (155, 89, 182)
LIGHT_PURPLE = (188, 143, 241)

TOTAL_LEVELS = 6

# ----------------------------------------
# Sound effects (placeholder paths - you can replace with your own)
# ----------------------------------------
SOUNDS = {
    "win": None,
    "lose": None,
    "click": None,
    "correct": None,
}

def load_sounds():
    base_dir = os.path.dirname(__file__)
    sound_dir = os.path.join(base_dir, "sounds")
    
    if os.path.exists(sound_dir):
        try:
            if os.path.exists(os.path.join(sound_dir, "win.wav")):
                SOUNDS["win"] = pygame.mixer.Sound(os.path.join(sound_dir, "win.wav"))
            if os.path.exists(os.path.join(sound_dir, "lose.wav")):
                SOUNDS["lose"] = pygame.mixer.Sound(os.path.join(sound_dir, "lose.wav"))
            if os.path.exists(os.path.join(sound_dir, "click.wav")):
                SOUNDS["click"] = pygame.mixer.Sound(os.path.join(sound_dir, "click.wav"))
            if os.path.exists(os.path.join(sound_dir, "correct.wav")):
                SOUNDS["correct"] = pygame.mixer.Sound(os.path.join(sound_dir, "correct.wav"))
        except Exception as e:
            print(f"Warning: Could not load sounds - {e}")

def play_sound(sound_name):
    if SOUNDS.get(sound_name):
        SOUNDS[sound_name].play()

load_sounds()

# ----------------------------------------
# Load config from JSON
# ----------------------------------------
def load_config():
    base_dir = os.path.dirname(__file__)
    path = os.path.join(base_dir, "challenges.json")

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print("Missing challenges.json. Put it in the same folder as game.py.")
        sys.exit()
    except json.JSONDecodeError:
        print("Your challenges.json file is invalid.")
        sys.exit()

CONFIG = load_config()

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

# Keeps track of already used themes so they don't repeat
USED_THEMES = {
    "word_search": set(),
    "connections": set(),
    "hangman": set(),
}

LEVEL_DATA = {}
LEVEL_RESULTS = {}
CURRENT_STATE = "HOME_MENU"

# Animation tracking
ANIMATION_TIMER = 0
PARTICLE_EFFECTS = []

class Particle:
    def __init__(self, x, y, vx, vy, color, lifetime):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = lifetime
        self.age = 0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2  # Gravity
        self.age += 1

    def is_alive(self):
        return self.age < self.lifetime

    def draw(self, surface):
        alpha = int(255 * (1 - self.age / self.lifetime))
        size = max(2, int(5 * (1 - self.age / self.lifetime)))
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), size)

def create_particle_burst(x, y, color, count=10):
    for _ in range(count):
        angle = random.uniform(0, 2 * 3.14159)
        speed = random.uniform(2, 6)
        vx = speed * (angle ** 0.5) * random.choice([-1, 1])
        vy = speed * (angle ** 0.5) * random.choice([-1, 1])
        PARTICLE_EFFECTS.append(Particle(x, y, vx, vy, color, 30))

def update_particles():
    for particle in PARTICLE_EFFECTS[:]:
        particle.update()
        if not particle.is_alive():
            PARTICLE_EFFECTS.remove(particle)

def draw_particles(surface):
    for particle in PARTICLE_EFFECTS:
        particle.draw(surface)

# ----------------------------------------
# Basic helpers
# ----------------------------------------
def get_font(size, bold=False):
    return pygame.font.SysFont("Arial", size, bold=bold)

def draw_button(surface, x, y, w, h, label, font, text_color=BLACK, fill_color=WHITE, 
                border_color=DARK_GRAY, border_width=2, hover=False):
    rect = pygame.Rect(x, y, w, h)
    
    if hover:
        fill_color = tuple(min(255, c + 20) for c in fill_color)
        border_color = BRIGHT_GREEN
        border_width = 3
    
    pygame.draw.rect(surface, fill_color, rect, border_radius=12)
    pygame.draw.rect(surface, border_color, rect, border_radius=12, width=border_width)
    
    text = font.render(label, True, text_color)
    text_rect = text.get_rect(center=rect.center)
    surface.blit(text, text_rect)
    return rect

def draw_rounded_box(surface, x, y, w, h, color, border_color=DARK_GRAY, border_width=2):
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, color, rect, border_radius=15)
    pygame.draw.rect(surface, border_color, rect, border_radius=15, width=border_width)

def get_level_definition(level_number):
    index = level_number - 1
    if index < 0 or index >= len(LEVEL_PLAN):
        return {"type": "word_search", "difficulty": "easy"}
    return LEVEL_PLAN[index]

def get_total_points():
    total = 0
    for level_number in range(1, TOTAL_LEVELS + 1):
        if level_number in LEVEL_RESULTS:
            total += LEVEL_RESULTS[level_number]["points"]
    return total

def get_theme_pool(challenge_type):
    if challenge_type == "word_search":
        return CONFIG.get("themes", [])
    if challenge_type == "connections":
        return CONFIG.get("connections_challenges", [])
    if challenge_type == "hangman":
        return CONFIG.get("hangman_challenges", [])
    return []

def choose_unused_theme(challenge_type):
    pool = get_theme_pool(challenge_type)
    if not pool:
        return None

    used = USED_THEMES[challenge_type]
    available = [item for item in pool if (item.get("name") or item.get("theme")) not in used]

    if not available:
        available = pool

    chosen = random.choice(available)
    theme_name = chosen.get("name") or chosen.get("theme")
    if theme_name:
        USED_THEMES[challenge_type].add(theme_name)
    return chosen

# ----------------------------------------
# Word Search
# ----------------------------------------
def make_word_search_grid(words, grid_size):
    grid = [["" for _ in range(grid_size)] for _ in range(grid_size)]
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]

    def fits(word, row, col, dr, dc):
        for i in range(len(word)):
            r = row + dr * i
            c = col + dc * i

            if not (0 <= r < grid_size and 0 <= c < grid_size):
                return False

            if grid[r][c] != "" and grid[r][c] != word[i]:
                return False

        return True

    for word in words:
        placed = False

        for _ in range(500):
            row = random.randint(0, grid_size - 1)
            col = random.randint(0, grid_size - 1)
            dr, dc = random.choice(directions)

            if fits(word, row, col, dr, dc):
                for i in range(len(word)):
                    r = row + dr * i
                    c = col + dc * i
                    grid[r][c] = word[i]

                placed = True
                break

        if not placed:
            return None

    for row in range(grid_size):
        for col in range(grid_size):
            if grid[row][col] == "":
                grid[row][col] = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    return grid

def build_word_search_challenge(difficulty_name):
    diff = DIFFICULTIES.get(difficulty_name, DIFFICULTIES["easy"])

    theme = choose_unused_theme("word_search")
    if theme is None:
        theme = {"theme": "THEME: CUSTOM", "words": ["WORD", "PUZZLE", "GAME", "LEVEL"]}

    words = list(theme.get("words", []))
    if len(words) < 3:
        words = ["WORD", "PUZZLE", "GAME", "LEVEL"]

    word_count = max(3, diff.get("word_count", 4))
    chosen_words = words[:word_count]
    random.shuffle(chosen_words)

    grid_size = diff.get("grid_size", 7)
    grid = make_word_search_grid(chosen_words, grid_size)

    if grid is None:
        return build_word_search_challenge(difficulty_name)

    return {
        "type": "word_search",
        "theme": theme.get("theme") or theme.get("name"),
        "words": chosen_words,
        "grid": grid,
        "difficulty": difficulty_name,
        "grid_size": grid_size,
        "time_limit": diff.get("time_limit", 90),
        "start_ticks": pygame.time.get_ticks(),
        "time_up": False,
        "selected_cells": [],
        "solved_paths": [],
        "found_words": [],
        "is_selecting": False,
        "finished": False,
    }

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

def get_cell_from_pos(pos, start_x, start_y, cell_size, padding, grid_size):
    x, y = pos

    for row in range(grid_size):
        for col in range(grid_size):
            cell_x = start_x + col * (cell_size + padding)
            cell_y = start_y + row * (cell_size + padding)

            if cell_x <= x <= cell_x + cell_size and cell_y <= y <= cell_y + cell_size:
                return row, col

    return None

# ----------------------------------------
# Connections
# ----------------------------------------
def build_connections_challenge(difficulty_name):
    theme = choose_unused_theme("connections")
    if theme is None:
        theme = {
            "theme": "THEME: CUSTOM",
            "groups": [
                {"category": "Group A", "items": ["A", "B", "C", "D"]},
                {"category": "Group B", "items": ["E", "F", "G", "H"]},
            ]
        }

    groups = theme.get("groups", [])
    if not groups:
        groups = [{"category": "Group A", "items": ["A", "B", "C", "D"]}]

    all_items = []
    for group in groups:
        for item in group["items"]:
            all_items.append(str(item).upper())

    random.shuffle(all_items)

    return {
        "type": "connections",
        "theme": theme.get("theme") or theme.get("name"),
        "difficulty": difficulty_name,
        "groups": groups,
        "board_items": all_items,
        "selected": [],
        "solved_groups": [],
        "time_limit": DIFFICULTIES.get(difficulty_name, DIFFICULTIES["easy"]).get("time_limit", 60),
        "start_ticks": pygame.time.get_ticks(),
        "time_up": False,
        "finished": False,
    }

# ----------------------------------------
# Hangman
# ----------------------------------------
def build_hangman_challenge(difficulty_name):
    theme = choose_unused_theme("hangman")
    if theme is None:
        theme = {"theme": "THEME: CUSTOM", "words": ["PUZZLE", "GAME", "LEVEL"]}

    words = theme.get("words", [])
    if not words:
        words = ["PUZZLE", "GAME", "LEVEL"]

    secret_word = random.choice(words).upper()

    return {
        "type": "hangman",
        "theme": theme.get("theme") or theme.get("name"),
        "difficulty": difficulty_name,
        "word": secret_word,
        "revealed": ["_"] * len(secret_word),
        "guessed": set(),
        "wrong_count": 0,
        "max_wrong": 6,
        "letters": [chr(i) for i in range(ord("A"), ord("Z") + 1)],
        "time_limit": DIFFICULTIES.get(difficulty_name, DIFFICULTIES["easy"]).get("time_limit", 60),
        "start_ticks": pygame.time.get_ticks(),
        "time_up": False,
        "finished": False,
    }

# ----------------------------------------
# Get/create level data
# ----------------------------------------
def get_level_data(level_number):
    if level_number not in LEVEL_DATA:
        level_def = get_level_definition(level_number)
        level_type = level_def["type"]
        difficulty = level_def["difficulty"]

        if level_type == "word_search":
            LEVEL_DATA[level_number] = build_word_search_challenge(difficulty)
        elif level_type == "connections":
            LEVEL_DATA[level_number] = build_connections_challenge(difficulty)
        elif level_type == "hangman":
            LEVEL_DATA[level_number] = build_hangman_challenge(difficulty)
        else:
            LEVEL_DATA[level_number] = build_word_search_challenge("easy")

    return LEVEL_DATA[level_number]

def clear_level_data(level_number):
    LEVEL_DATA.pop(level_number, None)

# ----------------------------------------
# Finish level and points
# ----------------------------------------
def challenge_finished(challenge):
    if challenge["type"] == "word_search":
        all_words_found = len(challenge["found_words"]) >= len(challenge["words"])
        return all_words_found or challenge["time_up"]

    if challenge["type"] == "connections":
        solved_count = len(challenge["solved_groups"])
        total_groups = len(challenge["groups"])
        return solved_count >= total_groups or challenge["time_up"]

    if challenge["type"] == "hangman":
        word_complete = all(letter != "_" for letter in challenge["revealed"])
        return word_complete or challenge["time_up"] or challenge["wrong_count"] >= challenge["max_wrong"]

    return False

def challenge_won(challenge):
    if challenge["type"] == "word_search":
        return len(challenge["found_words"]) >= len(challenge["words"])

    if challenge["type"] == "connections":
        return len(challenge["solved_groups"]) >= len(challenge["groups"])

    if challenge["type"] == "hangman":
        return all(letter != "_" for letter in challenge["revealed"])

    return False

def calculate_points(challenge, level_number):
    difficulty = challenge.get("difficulty", "easy")
    mult = {"easy": 1.0, "normal": 1.4, "hard": 1.8}[difficulty]

    if challenge["type"] == "word_search":
        total_words = len(challenge["words"])
        found_words = len(challenge["found_words"])
        elapsed = int((pygame.time.get_ticks() - challenge["start_ticks"]) / 1000)
        remaining_time = max(0, challenge["time_limit"] - elapsed)
        base = 200 * mult
        progress = int((found_words / total_words) * 150)
        return int(base + progress + remaining_time * 2)

    if challenge["type"] == "connections":
        solved = len(challenge["solved_groups"])
        total = len(challenge["groups"])
        base = 250 * mult
        return int(base + solved * 120 + (total - solved) * 25)

    if challenge["type"] == "hangman":
        guessed = sum(1 for letter in challenge["revealed"] if letter != "_")
        remaining_wrong = max(0, challenge["max_wrong"] - challenge["wrong_count"])
        base = 300 * mult
        return int(base + guessed * 20 + remaining_wrong * 30)

    return 0

def finish_level(level_number, challenge):
    if level_number in LEVEL_RESULTS:
        return

    won = challenge_won(challenge)
    points = calculate_points(challenge, level_number) if won else 0

    if won:
        play_sound("win")
        create_particle_burst(WIDTH // 2, HEIGHT // 2, GOLD, 20)
    else:
        play_sound("lose")

    LEVEL_RESULTS[level_number] = {
        "points": points,
        "type": challenge["type"],
        "theme": challenge.get("theme"),
        "difficulty": challenge.get("difficulty", "easy"),
    }

    challenge["finished"] = True

# ----------------------------------------
# Screens
# ----------------------------------------
def draw_home_screen():
    screen.fill(LIGHT_BG)

    # Title with gradient effect
    title = get_font(int(HEIGHT * 0.08), bold=True).render("Adventure Puzzle", True, BRIGHT_GREEN)
    title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT * 0.15))
    screen.blit(title, title_rect)

    subtitle = get_font(int(HEIGHT * 0.024)).render("Challenge Yourself", True, DARK_GRAY)
    screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, HEIGHT * 0.22))

    settings_rect = draw_button(
        screen,
        WIDTH // 2 - int(WIDTH * 0.3),
        int(HEIGHT * 0.45),
        int(WIDTH * 0.6),
        int(HEIGHT * 0.08),
        "⚙ Settings",
        get_font(int(HEIGHT * 0.03), bold=True),
        text_color=WHITE,
        fill_color=BRIGHT_BLUE,
    )

    start_rect = draw_button(
        screen,
        WIDTH // 2 - int(WIDTH * 0.3),
        int(HEIGHT * 0.58),
        int(WIDTH * 0.6),
        int(HEIGHT * 0.08),
        "▶ Start Game",
        get_font(int(HEIGHT * 0.03), bold=True),
        text_color=WHITE,
        fill_color=BRIGHT_GREEN,
    )

    return settings_rect, start_rect

def draw_settings_screen():
    screen.fill(LIGHT_BG)

    title = get_font(int(HEIGHT * 0.06), bold=True).render("Settings", True, BRIGHT_GREEN)
    title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT * 0.1))
    screen.blit(title, title_rect)

    info_text = get_font(int(HEIGHT * 0.022)).render("Sound: Enabled", True, DARK_GRAY)
    screen.blit(info_text, (WIDTH // 2 - info_text.get_width() // 2, HEIGHT * 0.3))

    info_text2 = get_font(int(HEIGHT * 0.022)).render("Difficulty: Dynamic", True, DARK_GRAY)
    screen.blit(info_text2, (WIDTH // 2 - info_text2.get_width() // 2, HEIGHT * 0.4))

    back_rect = draw_button(
        screen,
        WIDTH // 2 - int(WIDTH * 0.2),
        int(HEIGHT * 0.85),
        int(WIDTH * 0.4),
        int(HEIGHT * 0.07),
        "← Back",
        get_font(int(HEIGHT * 0.03), bold=True),
        text_color=WHITE,
        fill_color=PURPLE,
    )
    return back_rect

def draw_gameplay_screen():
    screen.fill(LIGHT_BG)

    title = get_font(int(HEIGHT * 0.06), bold=True).render("Select Level", True, BRIGHT_GREEN)
    title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT * 0.08))
    screen.blit(title, title_rect)

    score_box_rect = pygame.Rect(WIDTH // 2 - int(WIDTH * 0.35), int(HEIGHT * 0.14), int(WIDTH * 0.7), int(HEIGHT * 0.06))
    draw_rounded_box(screen, score_box_rect.x, score_box_rect.y, score_box_rect.w, score_box_rect.h, LIGHT_PURPLE)
    score_text = get_font(int(HEIGHT * 0.03), bold=True).render(f"Points: {get_total_points()}", True, WHITE)
    screen.blit(score_text, (score_box_rect.centerx - score_text.get_width() // 2, score_box_rect.centery - score_text.get_height() // 2))

    buttons = []
    for level_number in range(1, TOTAL_LEVELS + 1):
        b_w = int(WIDTH * 0.6)
        b_h = int(HEIGHT * 0.065)
        x = WIDTH // 2 - b_w // 2
        y = int(HEIGHT * 0.23) + (level_number - 1) * (b_h + int(HEIGHT * 0.015))

        level_def = get_level_definition(level_number)
        level_type = level_def["type"]
        icons = {"word_search": "🔍", "connections": "🔗", "hangman": "🎭"}
        label = f"{icons.get(level_type, '📋')} Level {level_number}"

        if level_number in LEVEL_RESULTS:
            fill_color = BRIGHT_GREEN
            text_color = WHITE
        else:
            fill_color = WHITE
            text_color = BLACK

        rect = draw_button(screen, x, y, b_w, b_h, label, get_font(int(HEIGHT * 0.025), bold=True),
                          text_color=text_color, fill_color=fill_color)

        if level_number in LEVEL_RESULTS:
            points_text = get_font(int(HEIGHT * 0.018)).render(f"✓ {LEVEL_RESULTS[level_number]['points']} pts", True, GOLD)
            screen.blit(points_text, (rect.right - points_text.get_width() - 10, rect.centery - points_text.get_height() // 2))
        else:
            ready_text = get_font(int(HEIGHT * 0.018)).render("Ready →", True, DARK_GRAY)
            screen.blit(ready_text, (rect.right - ready_text.get_width() - 10, rect.centery - ready_text.get_height() // 2))

        buttons.append((rect, level_number))

    back_rect = draw_button(
        screen,
        WIDTH // 2 - int(WIDTH * 0.2),
        int(HEIGHT * 0.91),
        int(WIDTH * 0.4),
        int(HEIGHT * 0.07),
        "← Back",
        get_font(int(HEIGHT * 0.03), bold=True),
        text_color=WHITE,
        fill_color=PURPLE,
    )

    return buttons, back_rect

def draw_word_search_screen(level_number, challenge):
    screen.fill(LIGHT_BG)

    # Top bar
    top_box_rect = pygame.Rect(10, 10, WIDTH - 20, int(HEIGHT * 0.12))
    draw_rounded_box(screen, top_box_rect.x, top_box_rect.y, top_box_rect.w, top_box_rect.h, WHITE)

    theme_text = get_font(int(HEIGHT * 0.024), bold=True).render(challenge["theme"], True, BRIGHT_GREEN)
    screen.blit(theme_text, (20, 15))

    if not challenge["time_up"]:
        elapsed = (pygame.time.get_ticks() - challenge["start_ticks"]) / 1000
        time_left = max(0, int(challenge["time_limit"] - elapsed))
        if time_left <= 0:
            challenge["time_up"] = True
    else:
        time_left = 0

    timer_color = BRIGHT_RED if time_left <= 15 else DARK_GRAY
    minutes = time_left // 60
    seconds = time_left % 60
    timer_text = get_font(int(HEIGHT * 0.03), bold=True).render(f"⏱ {minutes:02d}:{seconds:02d}", True, timer_color)
    screen.blit(timer_text, (WIDTH - timer_text.get_width() - 20, 18))

    found_count = len(challenge["found_words"])
    found_text = get_font(int(HEIGHT * 0.02)).render(
        f"Found: {found_count}/{len(challenge['words'])}",
        True,
        DARK_GRAY,
    )
    screen.blit(found_text, (20, int(HEIGHT * 0.09)))

    # Grid
    grid_size = challenge["grid_size"]
    board_area = min(WIDTH, HEIGHT) * 0.65
    cell_size = int(board_area / (grid_size + 0.25))
    padding = int(cell_size * 0.1)
    start_x = (WIDTH - ((grid_size * (cell_size + padding)) - padding)) // 2
    start_y = int(HEIGHT * 0.28)

    for row in range(grid_size):
        for col in range(grid_size):
            x = start_x + col * (cell_size + padding)
            y = start_y + row * (cell_size + padding)

            bg = WHITE
            text_color = BLACK
            border_color = DARK_GRAY

            if (row, col) in challenge["selected_cells"]:
                bg = BRIGHT_BLUE
                text_color = WHITE
                border_color = BRIGHT_BLUE
            elif any((row, col) in path for path in challenge["solved_paths"]):
                bg = BRIGHT_GREEN
                text_color = WHITE
                border_color = GREEN

            pygame.draw.rect(screen, bg, (x, y, cell_size, cell_size), border_radius=8)
            pygame.draw.rect(screen, border_color, (x, y, cell_size, cell_size), border_radius=8, width=2)

            letter = challenge["grid"][row][col]
            letter_surf = get_font(int(HEIGHT * 0.035), bold=True).render(letter, True, text_color)
            screen.blit(letter_surf, (x + cell_size // 2 - letter_surf.get_width() // 2,
                                     y + cell_size // 2 - letter_surf.get_height() // 2))

    back_rect = draw_button(
        screen,
        WIDTH // 2 - int(WIDTH * 0.2),
        int(HEIGHT * 0.88),
        int(WIDTH * 0.4),
        int(HEIGHT * 0.07),
        "← Back",
        get_font(int(HEIGHT * 0.03), bold=True),
        text_color=WHITE,
        fill_color=PURPLE,
    )

    # Finish screen overlay
    next_rect = None
    if challenge["finished"]:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        won = challenge_won(challenge)
        msg = "YOU WIN! 🎉" if won else "TIME'S UP! ⏰"
        color = BRIGHT_GREEN if won else BRIGHT_RED

        # Result box
        box_w = int(WIDTH * 0.8)
        box_h = int(HEIGHT * 0.4)
        box_x = (WIDTH - box_w) // 2
        box_y = (HEIGHT - box_h) // 2
        draw_rounded_box(screen, box_x, box_y, box_w, box_h, WHITE, border_color=color, border_width=4)

        result_text = get_font(int(HEIGHT * 0.06), bold=True).render(msg, True, color)
        screen.blit(result_text, result_text.get_rect(center=(WIDTH // 2, box_y + int(HEIGHT * 0.08))))

        if won:
            points = LEVEL_RESULTS[level_number]["points"]
            points_text = get_font(int(HEIGHT * 0.04), bold=True).render(f"+{points} Points", True, GOLD)
            screen.blit(points_text, points_text.get_rect(center=(WIDTH // 2, box_y + int(HEIGHT * 0.16))))

        next_rect = draw_button(
            screen,
            box_x + int(box_w * 0.1),
            box_y + int(box_h * 0.7),
            int(box_w * 0.8),
            int(HEIGHT * 0.08),
            "→ Continue",
            get_font(int(HEIGHT * 0.03), bold=True),
            text_color=WHITE,
            fill_color=BRIGHT_GREEN,
        )

    draw_particles(screen)
    return back_rect, start_x, start_y, cell_size, padding, grid_size, next_rect

def draw_connections_screen(level_number, challenge):
    screen.fill(LIGHT_BG)

    # Top bar
    top_box_rect = pygame.Rect(10, 10, WIDTH - 20, int(HEIGHT * 0.1))
    draw_rounded_box(screen, top_box_rect.x, top_box_rect.y, top_box_rect.w, top_box_rect.h, WHITE)

    theme_text = get_font(int(HEIGHT * 0.024), bold=True).render(challenge["theme"], True, BRIGHT_GREEN)
    screen.blit(theme_text, (20, 15))

    if not challenge["time_up"]:
        elapsed = (pygame.time.get_ticks() - challenge["start_ticks"]) / 1000
        time_left = max(0, int(challenge["time_limit"] - elapsed))
        if time_left <= 0:
            challenge["time_up"] = True
    else:
        time_left = 0

    timer_color = BRIGHT_RED if time_left <= 15 else DARK_GRAY
    timer_text = get_font(int(HEIGHT * 0.03), bold=True).render(f"⏱ {time_left // 60:02d}:{time_left % 60:02d}", True, timer_color)
    screen.blit(timer_text, (WIDTH - timer_text.get_width() - 20, 18))

    solved_text = get_font(int(HEIGHT * 0.02)).render(
        f"Solved: {len(challenge['solved_groups'])}/{len(challenge['groups'])}",
        True,
        DARK_GRAY,
    )
    screen.blit(solved_text, (20, int(HEIGHT * 0.07)))

    board_items = challenge["board_items"]
    columns = 3
    gap_x = int(WIDTH * 0.04)
    gap_y = int(HEIGHT * 0.015)
    cell_w = int(WIDTH * 0.25)
    cell_h = int(HEIGHT * 0.075)
    start_x = (WIDTH - (columns * cell_w + (columns - 1) * gap_x)) // 2
    start_y = int(HEIGHT * 0.22)

    rects = []
    for index, item in enumerate(board_items):
        col = index % columns
        row = index // columns

        x = start_x + col * (cell_w + gap_x)
        y = start_y + row * (cell_h + gap_y)
        rect = pygame.Rect(x, y, cell_w, cell_h)

        if item in challenge["selected"]:
            color = BRIGHT_BLUE
            text_color = WHITE
        else:
            color = WHITE
            text_color = BLACK

        pygame.draw.rect(screen, color, rect, border_radius=10)
        pygame.draw.rect(screen, BRIGHT_GREEN if item in challenge["selected"] else DARK_GRAY, rect, border_radius=10, width=2)

        label = get_font(int(HEIGHT * 0.02), bold=True).render(item, True, text_color)
        screen.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))
        rects.append((rect, item))

    back_rect = draw_button(
        screen,
        WIDTH // 2 - int(WIDTH * 0.2),
        int(HEIGHT * 0.88),
        int(WIDTH * 0.4),
        int(HEIGHT * 0.07),
        "← Back",
        get_font(int(HEIGHT * 0.03), bold=True),
        text_color=WHITE,
        fill_color=PURPLE,
    )

    # Finish screen overlay
    next_rect = None
    if challenge["finished"]:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        won = challenge_won(challenge)
        msg = "YOU WIN! 🎉" if won else "TIME'S UP! ⏰"
        color = BRIGHT_GREEN if won else BRIGHT_RED

        box_w = int(WIDTH * 0.8)
        box_h = int(HEIGHT * 0.4)
        box_x = (WIDTH - box_w) // 2
        box_y = (HEIGHT - box_h) // 2
        draw_rounded_box(screen, box_x, box_y, box_w, box_h, WHITE, border_color=color, border_width=4)

        result_text = get_font(int(HEIGHT * 0.06), bold=True).render(msg, True, color)
        screen.blit(result_text, result_text.get_rect(center=(WIDTH // 2, box_y + int(HEIGHT * 0.08))))

        if won:
            points = LEVEL_RESULTS[level_number]["points"]
            points_text = get_font(int(HEIGHT * 0.04), bold=True).render(f"+{points} Points", True, GOLD)
            screen.blit(points_text, points_text.get_rect(center=(WIDTH // 2, box_y + int(HEIGHT * 0.16))))

        next_rect = draw_button(
            screen,
            box_x + int(box_w * 0.1),
            box_y + int(box_h * 0.7),
            int(box_w * 0.8),
            int(HEIGHT * 0.08),
            "→ Continue",
            get_font(int(HEIGHT * 0.03), bold=True),
            text_color=WHITE,
            fill_color=BRIGHT_GREEN,
        )

    draw_particles(screen)
    return back_rect, rects, next_rect

def draw_hangman_screen(level_number, challenge):
    screen.fill(LIGHT_BG)

    # Top bar
    top_box_rect = pygame.Rect(10, 10, WIDTH - 20, int(HEIGHT * 0.1))
    draw_rounded_box(screen, top_box_rect.x, top_box_rect.y, top_box_rect.w, top_box_rect.h, WHITE)

    theme_text = get_font(int(HEIGHT * 0.024), bold=True).render(challenge["theme"], True, BRIGHT_GREEN)
    screen.blit(theme_text, (20, 15))

    if not challenge["time_up"]:
        elapsed = (pygame.time.get_ticks() - challenge["start_ticks"]) / 1000
        time_left = max(0, int(challenge["time_limit"] - elapsed))
        if time_left <= 0:
            challenge["time_up"] = True
    else:
        time_left = 0

    timer_color = BRIGHT_RED if time_left <= 15 else DARK_GRAY
    timer_text = get_font(int(HEIGHT * 0.03), bold=True).render(f"⏱ {time_left // 60:02d}:{time_left % 60:02d}", True, timer_color)
    screen.blit(timer_text, (WIDTH - timer_text.get_width() - 20, 18))

    word_display = " ".join(challenge["revealed"])
    reveal_text = get_font(int(HEIGHT * 0.045), bold=True).render(word_display, True, BLACK)
    screen.blit(reveal_text, reveal_text.get_rect(center=(WIDTH // 2, int(HEIGHT * 0.22))))

    wrong_text = get_font(int(HEIGHT * 0.024)).render(
        f"Wrong: {challenge['wrong_count']}/{challenge['max_wrong']}",
        True,
        BRIGHT_RED,
    )
    screen.blit(wrong_text, (WIDTH // 2 - wrong_text.get_width() // 2, int(HEIGHT * 0.3)))

    # Hangman drawing
    cx = WIDTH // 2 - 50
    base_y = int(HEIGHT * 0.38)

    if challenge["wrong_count"] >= 1:
        pygame.draw.line(screen, BLACK, (cx - 60, base_y), (cx + 60, base_y), 5)
    if challenge["wrong_count"] >= 2:
        pygame.draw.line(screen, BLACK, (cx - 40, base_y), (cx - 40, base_y - 90), 5)
    if challenge["wrong_count"] >= 3:
        pygame.draw.line(screen, BLACK, (cx - 40, base_y - 90), (cx + 30, base_y - 90), 5)
    if challenge["wrong_count"] >= 4:
        pygame.draw.line(screen, BLACK, (cx + 30, base_y - 90), (cx + 30, base_y - 50), 5)
    if challenge["wrong_count"] >= 5:
        pygame.draw.circle(screen, BLACK, (cx + 30, base_y - 35), 15, 3)
    if challenge["wrong_count"] >= 6:
        pygame.draw.line(screen, BLACK, (cx + 30, base_y - 20), (cx + 30, base_y + 10), 5)
        pygame.draw.line(screen, BLACK, (cx + 30, base_y - 10), (cx + 50, base_y), 5)
        pygame.draw.line(screen, BLACK, (cx + 30, base_y - 10), (cx + 10, base_y), 5)

    # Letter buttons
    letters = challenge["letters"]
    cols = 6
    gap = 6
    cell_w = int((WIDTH * 0.8) / cols)
    start_x = (WIDTH - (cols * cell_w + (cols - 1) * gap)) // 2
    start_y = int(HEIGHT * 0.52)
    letter_rects = []
    cell_h = int(HEIGHT * 0.055)

    for i, letter in enumerate(letters):
        row = i // cols
        col = i % cols
        x = start_x + col * (cell_w + gap)
        y = start_y + row * (cell_h + 5)
        rect = pygame.Rect(x, y, cell_w - gap, cell_h - 5)

        if letter in challenge["guessed"]:
            color = GRAY
            text_color = DARK_GRAY
        else:
            color = BRIGHT_BLUE
            text_color = WHITE

        pygame.draw.rect(screen, color, rect, border_radius=8)
        letter_text = get_font(int(HEIGHT * 0.025), bold=True).render(letter, True, text_color)
        screen.blit(letter_text, (rect.centerx - letter_text.get_width() // 2,
                                 rect.centery - letter_text.get_height() // 2))
        letter_rects.append((rect, letter))

    back_rect = draw_button(
        screen,
        WIDTH // 2 - int(WIDTH * 0.2),
        int(HEIGHT * 0.88),
        int(WIDTH * 0.4),
        int(HEIGHT * 0.07),
        "← Back",
        get_font(int(HEIGHT * 0.03), bold=True),
        text_color=WHITE,
        fill_color=PURPLE,
    )

    # Finish screen overlay
    next_rect = None
    if challenge["finished"]:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        won = challenge_won(challenge)
        msg = "YOU WIN! 🎉" if won else "GAME OVER! 💀"
        color = BRIGHT_GREEN if won else BRIGHT_RED

        box_w = int(WIDTH * 0.8)
        box_h = int(HEIGHT * 0.4)
        box_x = (WIDTH - box_w) // 2
        box_y = (HEIGHT - box_h) // 2
        draw_rounded_box(screen, box_x, box_y, box_w, box_h, WHITE, border_color=color, border_width=4)

        result_text = get_font(int(HEIGHT * 0.06), bold=True).render(msg, True, color)
        screen.blit(result_text, result_text.get_rect(center=(WIDTH // 2, box_y + int(HEIGHT * 0.08))))

        if won:
            points = LEVEL_RESULTS[level_number]["points"]
            points_text = get_font(int(HEIGHT * 0.04), bold=True).render(f"+{points} Points", True, GOLD)
            screen.blit(points_text, points_text.get_rect(center=(WIDTH // 2, box_y + int(HEIGHT * 0.16))))
        else:
            word_text = get_font(int(HEIGHT * 0.03)).render(f"Word: {challenge['word']}", True, DARK_GRAY)
            screen.blit(word_text, word_text.get_rect(center=(WIDTH // 2, box_y + int(HEIGHT * 0.16))))

        next_rect = draw_button(
            screen,
            box_x + int(box_w * 0.1),
            box_y + int(box_h * 0.7),
            int(box_w * 0.8),
            int(HEIGHT * 0.08),
            "→ Continue",
            get_font(int(HEIGHT * 0.03), bold=True),
            text_color=WHITE,
            fill_color=BRIGHT_GREEN,
        )

    draw_particles(screen)
    return back_rect, letter_rects, next_rect

# ----------------------------------------
# Click handling
# ----------------------------------------
def handle_word_search_click(level_number, challenge, mouse_pos):
    grid_size = challenge["grid_size"]
    board_area = min(WIDTH, HEIGHT) * 0.65
    cell_size = int(board_area / (grid_size + 0.25))
    padding = int(cell_size * 0.1)
    start_x = (WIDTH - ((grid_size * (cell_size + padding)) - padding)) // 2
    start_y = int(HEIGHT * 0.28)

    cell = get_cell_from_pos(mouse_pos, start_x, start_y, cell_size, padding, grid_size)
    if cell is None:
        return

    if any(cell in path for path in challenge["solved_paths"]):
        return

    challenge["selected_cells"] = [cell]
    challenge["is_selecting"] = True

def handle_word_search_drag(level_number, challenge, mouse_pos):
    if not challenge["is_selecting"]:
        return

    grid_size = challenge["grid_size"]
    board_area = min(WIDTH, HEIGHT) * 0.65
    cell_size = int(board_area / (grid_size + 0.25))
    padding = int(cell_size * 0.1)
    start_x = (WIDTH - ((grid_size * (cell_size + padding)) - padding)) // 2
    start_y = int(HEIGHT * 0.28)

    cell = get_cell_from_pos(mouse_pos, start_x, start_y, cell_size, padding, grid_size)
    if cell is None or cell in challenge["selected_cells"]:
        return

    if any(cell in path for path in challenge["solved_paths"]):
        return

    test_path = challenge["selected_cells"] + [cell]

    if len(test_path) >= 2 and straight_line_ok(test_path):
        last_row, last_col = challenge["selected_cells"][-1]
        if abs(cell[0] - last_row) <= 1 and abs(cell[1] - last_col) <= 1:
            challenge["selected_cells"].append(cell)

def handle_word_search_release(level_number, challenge):
    challenge["is_selecting"] = False

    if len(challenge["selected_cells"]) < 2:
        challenge["selected_cells"] = []
        return

    word = "".join(challenge["grid"][r][c] for r, c in challenge["selected_cells"])
    reversed_word = word[::-1]

    if word in challenge["words"] and word not in challenge["found_words"]:
        challenge["found_words"].append(word)
        challenge["solved_paths"].append(list(challenge["selected_cells"]))
        play_sound("correct")
        create_particle_burst(WIDTH // 2, HEIGHT // 2, BRIGHT_GREEN, 10)
    elif reversed_word in challenge["words"] and reversed_word not in challenge["found_words"]:
        challenge["found_words"].append(reversed_word)
        challenge["solved_paths"].append(list(challenge["selected_cells"]))
        play_sound("correct")
        create_particle_burst(WIDTH // 2, HEIGHT // 2, BRIGHT_GREEN, 10)

    if len(challenge["found_words"]) >= len(challenge["words"]):
        finish_level(level_number, challenge)

    challenge["selected_cells"] = []

def handle_connections_click(level_number, challenge, mouse_pos):
    for rect, item in challenge["_rects"]:
        if rect.collidepoint(mouse_pos):
            play_sound("click")
            if item in challenge["selected"]:
                challenge["selected"].remove(item)
            else:
                challenge["selected"].append(item)

                if len(challenge["selected"]) == 4:
                    selected_set = set(challenge["selected"])
                    matched_group = None

                    for group in challenge["groups"]:
                        group_items = set(str(x).upper() for x in group["items"])
                        if group_items.issubset(selected_set):
                            matched_group = group["category"]
                            break

                    if matched_group:
                        play_sound("correct")
                        create_particle_burst(WIDTH // 2, HEIGHT // 2, BRIGHT_GREEN, 15)
                        challenge["solved_groups"].append(matched_group)
                        challenge["selected"] = []
                    else:
                        challenge["selected"] = []

                    challenge["solved_groups"] = list(dict.fromkeys(challenge["solved_groups"]))

                    if len(challenge["solved_groups"]) >= len(challenge["groups"]):
                        finish_level(level_number, challenge)
            return

def handle_hangman_click(level_number, challenge, mouse_pos):
    for rect, letter in challenge["_letters_rects"]:
        if rect.collidepoint(mouse_pos):
            if letter in challenge["guessed"]:
                return

            play_sound("click")
            challenge["guessed"].add(letter)

            if letter in challenge["word"]:
                play_sound("correct")
                create_particle_burst(rect.centerx, rect.centery, BRIGHT_GREEN, 8)
                for i, ch in enumerate(challenge["word"]):
                    if ch == letter:
                        challenge["revealed"][i] = letter
            else:
                challenge["wrong_count"] += 1

            if all(char != "_" for char in challenge["revealed"]):
                finish_level(level_number, challenge)
            elif challenge["wrong_count"] >= challenge["max_wrong"]:
                challenge["time_up"] = True
                finish_level(level_number, challenge)

            return

# ----------------------------------------
# Main loop
# ----------------------------------------
running = True

while running:
    W, H = screen.get_width(), screen.get_height()
    FONT_L = get_font(int(H * 0.06), bold=True)
    FONT_M = get_font(int(max(14, H * 0.032)), bold=True)
    FONT_S = get_font(int(max(11, H * 0.024)))

    update_particles()
    ANIMATION_TIMER += 1

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if CURRENT_STATE == "HOME_MENU":
                settings_rect, start_rect = draw_home_screen()
                if settings_rect.collidepoint(event.pos):
                    play_sound("click")
                    CURRENT_STATE = "SETTINGS_MENU"
                elif start_rect.collidepoint(event.pos):
                    play_sound("click")
                    CURRENT_STATE = "GAMEPLAY"

            elif CURRENT_STATE == "SETTINGS_MENU":
                back_rect = draw_settings_screen()
                if back_rect.collidepoint(event.pos):
                    play_sound("click")
                    CURRENT_STATE = "HOME_MENU"

            elif CURRENT_STATE == "GAMEPLAY":
                buttons, back_rect = draw_gameplay_screen()
                if back_rect.collidepoint(event.pos):
                    play_sound("click")
                    CURRENT_STATE = "HOME_MENU"
                else:
                    for rect, level_number in buttons:
                        if rect.collidepoint(event.pos):
                            play_sound("click")
                            clear_level_data(level_number)
                            CURRENT_STATE = f"LEVEL_{level_number}"
                            break

            elif CURRENT_STATE.startswith("LEVEL_"):
                level_number = int(CURRENT_STATE.split("_")[1])
                challenge = get_level_data(level_number)

                if challenge["type"] == "word_search":
                    back_rect, start_x, start_y, cell_size, padding, grid_size, next_rect = draw_word_search_screen(level_number, challenge)
                    
                    if next_rect and next_rect.collidepoint(event.pos):
                        play_sound("click")
                        CURRENT_STATE = "GAMEPLAY"
                        clear_level_data(level_number)
                        continue

                    if back_rect.collidepoint(event.pos):
                        play_sound("click")
                        CURRENT_STATE = "GAMEPLAY"
                        clear_level_data(level_number)
                        continue

                    if challenge["time_up"] or challenge["finished"]:
                        continue

                    handle_word_search_click(level_number, challenge, event.pos)

                elif challenge["type"] == "connections":
                    back_rect, rects, next_rect = draw_connections_screen(level_number, challenge)
                    challenge["_rects"] = rects

                    if next_rect and next_rect.collidepoint(event.pos):
                        play_sound("click")
                        CURRENT_STATE = "GAMEPLAY"
                        clear_level_data(level_number)
                        continue

                    if back_rect.collidepoint(event.pos):
                        play_sound("click")
                        CURRENT_STATE = "GAMEPLAY"
                        clear_level_data(level_number)
                        continue

                    if challenge["finished"]:
                        continue

                    handle_connections_click(level_number, challenge, event.pos)

                elif challenge["type"] == "hangman":
                    back_rect, letter_rects, next_rect = draw_hangman_screen(level_number, challenge)
                    challenge["_letters_rects"] = letter_rects

                    if next_rect and next_rect.collidepoint(event.pos):
                        play_sound("click")
                        CURRENT_STATE = "GAMEPLAY"
                        clear_level_data(level_number)
                        continue

                    if back_rect.collidepoint(event.pos):
                        play_sound("click")
                        CURRENT_STATE = "GAMEPLAY"
                        clear_level_data(level_number)
                        continue

                    if challenge["finished"]:
                        continue

                    handle_hangman_click(level_number, challenge, event.pos)

        elif event.type == pygame.MOUSEMOTION:
            if CURRENT_STATE.startswith("LEVEL_"):
                level_number = int(CURRENT_STATE.split("_")[1])
                challenge = get_level_data(level_number)

                if challenge["type"] == "word_search" and challenge["is_selecting"]:
                    handle_word_search_drag(level_number, challenge, event.pos)

        elif event.type == pygame.MOUSEBUTTONUP:
            if CURRENT_STATE.startswith("LEVEL_"):
                level_number = int(CURRENT_STATE.split("_")[1])
                challenge = get_level_data(level_number)

                if challenge["type"] == "word_search" and challenge["is_selecting"]:
                    handle_word_search_release(level_number, challenge)

    # Draw current screen
    if CURRENT_STATE == "HOME_MENU":
        draw_home_screen()

    elif CURRENT_STATE == "SETTINGS_MENU":
        draw_settings_screen()

    elif CURRENT_STATE == "GAMEPLAY":
        draw_gameplay_screen()

    elif CURRENT_STATE.startswith("LEVEL_"):
        level_number = int(CURRENT_STATE.split("_")[1])
        challenge = get_level_data(level_number)

        if challenge["type"] == "word_search":
            draw_word_search_screen(level_number, challenge)
        elif challenge["type"] == "connections":
            draw_connections_screen(level_number, challenge)
        elif challenge["type"] == "hangman":
            draw_hangman_screen(level_number, challenge)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
