import math
import random
import sys
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

import pygame

"""Главный модуль игры: основные константы, типы данных и утилиты для CoolGame.
Содержит конфигурацию, классы сущностей и вспомогательные функции.
Поддержка сети опциональна и импортируется динамически при наличии.
"""

# Поддержка сетевой игры (опционально)
MULTIPLAYER_AVAILABLE = False

# Пытаемся импортировать модуль мультиплеера
try:
    from multiplayer import (
        GameHost, GameClient, PlayerState,
        GameState, LocalPlayerInput, DEFAULT_PORT
    )

    MULTIPLAYER_AVAILABLE = True
except ImportError as e:
    GameHost = Any
    GameClient = Any
    PlayerState = Any
    GameState = Any
    LocalPlayerInput = Any
    DEFAULT_PORT = 5555
    print(f"[ПРЕДУПРЕЖДЕНИЕ] Мультиплеер недоступен: {e}")

# === ИГРОВАЯ КОНФИГУРАЦИЯ ===
VERSION = "3.0.0-alpha"

WIDTH = 1400                  # Ширина окна игры
HEIGHT = 800                  # Высота окна игры
CENTER = pygame.Vector2(WIDTH / 2, HEIGHT / 2)  # Центр экрана
FPS = 120                     # Целевой FPS
WORLD_PADDING = 280           # Отступ за пределами видимой области
EXTRA_LIFE_SPAWN_TIME = 180.0 # Интервал появления доп. жизни (сек)
# === ЦВЕТА ===
BG_COLOR = (10, 14, 24)       # Цвет фона (тёмно-синий)
GRID_COLOR = (24, 32, 56)     # Цвет сетки
WHITE = (240, 244, 255)       # Белый
RED = (255, 90, 90)           # Красный (урон)
GREEN = (80, 230, 160)        # Зелёный (лечение)
BLUE = (90, 160, 255)         # Синий (рывок)
YELLOW = (255, 220, 110)      # Жёлтый (обычные пули)
CYAN = (100, 250, 255)        # Голубой (криты, дроны)
PURPLE = (170, 110, 255)     # Фиолетовый (доп. жизнь)
ORANGE = (255, 165, 70)       # Оранжевый
GOLD = (255, 215, 90)         # Золотой (монеты)
# === ПУТИ К ФАЙЛАМ ===
BASE_DIR = Path(__file__).parent       # Корневая папка игры
SAVE_FILE = BASE_DIR / "save_data.json"      # Файл сохранения (устаревший)
ACCOUNTS_FILE = BASE_DIR / "accounts.json" # Файл списка аккаунтов
ACCOUNTS_DIR = BASE_DIR / "accounts"       # Папка с данными аккаунтов

# === УЛУЧШЕНИЯ ВНУТРИ ЗАБЕГА ===
# Каждое улучшение имеет: название, описание, максимальный уровень
UPGRADES = {
    "damage": {
        "name": "Форсажные патроны",
        "desc": "+22% к урону пуль",
        "max": 8,
    },
    "fire_rate": {
        "name": "Рефлекторный спуск",
        "desc": "+18% к скорострельности",
        "max": 8,
    },
    "move_speed": {
        "name": "Векторные ботинки",
        "desc": "+12% к скорости движения",
        "max": 8,
    },
    "max_health": {
        "name": "Наностальная броня",
        "desc": "+20 к максимуму ОЗ и лечение на 55",
        "max": 5,
    },
    "dash": {
        "name": "Блинк-привод",
        "desc": "Меньше перезарядка рывка",
        "max": 6,
    },
    "multishot": {
        "name": "Разделяющая решётка",
        "desc": "+1 боковой снаряд",
        "max": 4,
    },
    "pierce": {
        "name": "Фазовое ядро",
        "desc": "+1 пробивание пуль",
        "max": 5,
    },
    "regen": {
        "name": "Биорегенерация",
        "desc": "+1.2 ОЗ в секунду",
        "max": 6,
    },
    "magnet": {
        "name": "Магнитный контур",
        "desc": "Опыт притягивается быстрее",
        "max": 5,
    },
    "crit": {
        "name": "Критическая призма",
        "desc": "+8% к шансу крита и +25% к крит-урону",
        "max": 5,
    },
    "shield": {
        "name": "Слой Эгиды",
        "desc": "+1 заряд щита",
        "max": 4,
    },
    "drone": {
        "name": "Дрон-охотник",
        "desc": "Добавляет орбитальный дрон",
        "max": 4,
    },
}

# === УЛУЧШЕНИЯ В МАГАЗИНЕ (мета-прогрессия) ===
# Эти улучшения дают бонусы в начале каждого забега
SHOP_UPGRADES = {
    "start_damage": {
        "name": "Стартовый урон",
        "desc": "+1 ранг урона в начале забега",
        "costs": [300, 800, 2000, 5000],
        "ingame_upgrade": "damage",
    },
    "start_health": {
        "name": "Стартовая броня",
        "desc": "+1 ранг здоровья в начале забега",
        "costs": [250, 600, 1500, 4000],
        "ingame_upgrade": "max_health",
    },
    "start_shield": {
        "name": "Стартовый щит",
        "desc": "+1 заряд щита в начале забега",
        "costs": [400, 1000, 2500],
        "ingame_upgrade": "shield",
    },
    "start_magnet": {
        "name": "Стартовый магнит",
        "desc": "+1 ранг магнита в начале забега",
        "costs": [200, 500, 1200, 3000],
        "ingame_upgrade": "magnet",
    },
    "coin_bonus": {
        "name": "Монетный бонус",
        "desc": "+25% монет за уровень",
        "costs": [300, 800, 2000, 5000],
        "ingame_upgrade": None,
    },
    "start_multishot": {
        "name": "Многоствольная атака",
        "desc": "+1 ранг многоствольности в начале забега",
        "costs": [500, 1500, 4000, 10000],
        "ingame_upgrade": "multishot",
    },
    "start_pierce": {
        "name": "Пробивание",
        "desc": "+1 ранг пробивания в начале забега",
        "costs": [250, 600, 1500, 4000],
        "ingame_upgrade": "pierce",
    },
    "start_regen": {
        "name": "Регенерация",
        "desc": "+1 ранг регенерации в начале забега",
        "costs": [200, 500, 1200, 3000],
        "ingame_upgrade": "regen",
    },
    "start_crit": {
        "name": "Критический удар",
        "desc": "+1 ранг крит. удара в начале забега",
        "costs": [300, 800, 2000, 5000],
        "ingame_upgrade": "crit",
    },
    "start_drone": {
        "name": "Дрон-союзник",
        "desc": "+1 дрон в начале забега",
        "costs": [800, 2000, 5000],
        "ingame_upgrade": "drone",
    },
    "xp_bonus": {
        "name": "Опытный боец",
        "desc": "+20% опыта за убийство",
        "costs": [400, 1000, 2500, 6000],
        "ingame_upgrade": None,
    },
    "start_dash": {
        "name": "Рывок в бой",
        "desc": "+1 ранг рывка в начале забега",
        "costs": [250, 600, 1500, 4000],
        "ingame_upgrade": "dash",
    },
}

# === СКИНЫ ИГРОКА ===
# Каждый скин имеет цвета для тела, неуязвимости и ядра
SKINS = {
    "classic": {
        "name": "Неон",
        "cost": 0,
        "body": (95, 225, 180),
        "invuln": (120, 255, 220),
        "core": (230, 255, 250),
    },
    "ember": {
        "name": "Искра",
        "cost": 70,
        "body": (255, 132, 92),
        "invuln": (255, 185, 128),
        "core": (255, 240, 225),
    },
    "frost": {
        "name": "Лёд",
        "cost": 90,
        "body": (100, 190, 255),
        "invuln": (145, 225, 255),
        "core": (235, 248, 255),
    },
    "royal": {
        "name": "Роял",
        "cost": 120,
        "body": (182, 120, 255),
        "invuln": (210, 170, 255),
        "core": (245, 236, 255),
    },
    "void": {
        "name": "Бездна",
        "cost": 160,
        "body": (55, 70, 100),
        "invuln": (115, 150, 210),
        "core": (215, 225, 245),
    },
    "toxic": {
        "name": "Токсик",
        "cost": 85,
        "body": (80, 255, 120),
        "invuln": (140, 255, 180),
        "core": (200, 255, 220),
    },
    "sunset": {
        "name": "Закат",
        "cost": 95,
        "body": (255, 180, 100),
        "invuln": (255, 210, 150),
        "core": (255, 240, 200),
    },
    "plasma": {
        "name": "Плазма",
        "cost": 110,
        "body": (255, 80, 255),
        "invuln": (255, 140, 255),
        "core": (255, 220, 255),
    },
    "shadow": {
        "name": "Тень",
        "cost": 130,
        "body": (40, 40, 60),
        "invuln": (80, 80, 120),
        "core": (150, 150, 180),
    },
    "crimson": {
        "name": "Кремзон",
        "cost": 145,
        "body": (220, 60, 60),
        "invuln": (255, 100, 100),
        "core": (255, 200, 200),
    },
    "cyber": {
        "name": "Кайбер",
        "cost": 175,
        "body": (0, 255, 200),
        "invuln": (100, 255, 220),
        "core": (200, 255, 240),
    },
    "aurora": {
        "name": "Aurora",
        "cost": 190,
        "body": (138, 43, 226),
        "invuln": (186, 85, 211),
        "core": (255, 182, 193),
    },
    "galaxy": {
        "name": "Galaxy",
        "cost": 200,
        "body": (25, 25, 112),
        "invuln": (75, 0, 130),
        "core": (138, 43, 226),
    },
    "nebula": {
        "name": "Nebula",
        "cost": 185,
        "body": (255, 20, 147),
        "invuln": (255, 105, 180),
        "core": (255, 182, 193),
    },
    "cosmic": {
        "name": "Cosmic",
        "cost": 210,
        "body": (0, 191, 255),
        "invuln": (135, 206, 235),
        "core": (176, 224, 230),
    },
    "rainbow": {
        "name": "Rainbow",
        "cost": 250,
        "body": (255, 0, 128),
        "invuln": (255, 128, 0),
        "core": (128, 255, 0),
    },
    "electric": {
        "name": "Electric",
        "cost": 195,
        "body": (0, 255, 255),
        "invuln": (127, 255, 212),
        "core": (64, 224, 208),
    },
    "fire": {
        "name": "Fire",
        "cost": 180,
        "body": (255, 69, 0),
        "invuln": (255, 140, 0),
        "core": (255, 215, 0),
    },
    "ice": {
        "name": "Ice",
        "cost": 175,
        "body": (176, 224, 230),
        "invuln": (135, 206, 235),
        "core": (176, 196, 222),
    },
    "nature": {
        "name": "Nature",
        "cost": 165,
        "body": (34, 139, 34),
        "invuln": (144, 238, 144),
        "core": (152, 251, 152),
    },
}

# === ДАННЫЕ ВРАГОВ ===
# Характеристики всех типов врагов: радиус, скорость, ОЗ, урон, опыт, очки, цвет
ENEMY_DATA = {
    "chaser": {
        "radius": 16,
        "speed": 170,
        "hp": 34,
        "damage": 12,
        "xp": 7,
        "score": 10,
        "color": (255, 95, 95),
        "title": "Chaser",
    },
    "shooter": {
        "radius": 18,
        "speed": 118,
        "hp": 46,
        "damage": 8,
        "xp": 12,
        "score": 18,
        "color": (255, 185, 80),
        "title": "Shooter",
    },
    "tank": {
        "radius": 28,
        "speed": 82,
        "hp": 150,
        "damage": 22,
        "xp": 22,
        "score": 40,
        "color": (126, 100, 255),
        "title": "Tank",
    },
    "splitter": {
        "radius": 20,
        "speed": 140,
        "hp": 62,
        "damage": 14,
        "xp": 16,
        "score": 26,
        "color": (70, 220, 170),
        "title": "Splitter",
    },
    "mine": {
        "radius": 14,
        "speed": 98,
        "hp": 20,
        "damage": 26,
        "xp": 10,
        "score": 20,
        "color": (255, 70, 190),
        "title": "Mine",
    },
    "ghost": {
        "radius": 15,
        "speed": 200,
        "hp": 28,
        "damage": 10,
        "xp": 8,
        "score": 12,
        "color": (200, 150, 255),
        "title": "Ghost",
    },
    "spawner": {
        "radius": 22,
        "speed": 65,
        "hp": 85,
        "damage": 16,
        "xp": 18,
        "score": 32,
        "color": (255, 100, 150),
        "title": "Spawner",
    },
    "laser": {
        "radius": 12,
        "speed": 145,
        "hp": 38,
        "damage": 18,
        "xp": 14,
        "score": 22,
        "color": (255, 50, 50),
        "title": "Laser",
    },
    "teleporter": {
        "radius": 16,
        "speed": 85,
        "hp": 42,
        "damage": 15,
        "xp": 16,
        "score": 28,
        "color": (255, 150, 255),
        "title": "Teleporter",
    },
    "rocket": {
        "radius": 14,
        "speed": 180,
        "hp": 32,
        "damage": 20,
        "xp": 12,
        "score": 18,
        "color": (255, 150, 50),
        "title": "Rocket",
    },
    "boss_core": {
        "radius": 56,
        "speed": 92,
        "hp": 1800,
        "damage": 20,
        "xp": 180,
        "score": 400,
        "color": (120, 245, 255),
        "title": "Ядро затмения",
    },
    "boss_blade": {
        "radius": 50,
        "speed": 122,
        "hp": 2250,
        "damage": 24,
        "xp": 190,
        "score": 430,
        "color": (255, 150, 85),
        "title": "Копьё рассвета",
    },
    "boss_hive": {
        "radius": 54,
        "speed": 84,
        "hp": 3100,
        "damage": 23,
        "xp": 210,
        "score": 470,
        "color": (188, 110, 255),
        "title": "Пустотный улей",
    },
    "boss_tempest": {
        "radius": 58,
        "speed": 140,
        "hp": 3800,
        "damage": 28,
        "xp": 280,
        "score": 600,
        "color": (100, 255, 200),
        "title": "Буря хаоса",
    },
    "boss_void": {
        "radius": 62,
        "speed": 75,
        "hp": 4800,
        "damage": 32,
        "xp": 350,
        "score": 750,
        "color": (50, 50, 80),
        "title": "Пустота забвения",
    },
    "boss_omega": {
        "radius": 66,
        "speed": 180,
        "hp": 8000,
        "damage": 45,
        "xp": 600,
        "score": 1200,
        "color": (255, 255, 255),
        "title": "Омега апокалипсис",
    },
    "boss_overlord": {
        "radius": 72,
        "speed": 95,
        "hp": 12000,
        "damage": 55,
        "xp": 800,
        "score": 1500,
        "color": (180, 60, 180),
        "title": "Властелин роя",
    },
    "boss_crystal": {
        "radius": 60,
        "speed": 110,
        "hp": 10000,
        "damage": 50,
        "xp": 700,
        "score": 1300,
        "color": (150, 255, 220),
        "title": "Кристальный титан",
    },
    "boss_time": {
        "radius": 64,
        "speed": 130,
        "hp": 9000,
        "damage": 48,
        "xp": 650,
        "score": 1250,
        "color": (100, 100, 255),
        "title": "Повелитель времени",
    },
    "boss_flame": {
        "radius": 68,
        "speed": 105,
        "hp": 11000,
        "damage": 52,
        "xp": 750,
        "score": 1400,
        "color": (255, 100, 50),
        "title": "Лорд пламени",
    },
}

# Множество типов боссов для быстрой проверки
BOSS_TYPES = {"boss_core", "boss_blade", "boss_hive", "boss_tempest", "boss_void", "boss_omega", "boss_overlord",
              "boss_crystal", "boss_time", "boss_flame"}


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def clamp(value, minimum, maximum):
    """Ограничивает значение между минимумом и максимумом"""
    return max(minimum, min(maximum, value))


def lerp(a, b, t):
    """Линейная интерполяция между a и b с коэффициентом t (0..1)"""
    return a + (b - a) * t


def draw_text(surface, font, text, color, x, y, anchor="center"):
    """Рисует текст на поверхности с указанным выравниванием"""
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    setattr(rect, anchor, (x, y))
    surface.blit(rendered, rect)
    return rect


def draw_wrapped_text(surface, font, text, color, x, y, max_width, anchor="center"):
    """Рисует текст с переносом по словам (многострочный)"""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        text_surface = font.render(test_line, True, color)
        if text_surface.get_width() <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                lines.append(word)

    if current_line:
        lines.append(' '.join(current_line))

    # Рисуем каждую строку
    line_height = font.get_height()
    total_height = len(lines) * line_height

    if anchor == "center":
        start_y = y - total_height // 2
    elif anchor == "top":
        start_y = y
    else:  # низ
        start_y = y - total_height

    rects = []
    for i, line in enumerate(lines):
        rect = draw_text(surface, font, line, color, x, start_y + i * line_height, anchor)
        rects.append(rect)

    return rects


def angle_to_vector(angle_deg):
    """Преобразует угол в градусах в вектор направления"""
    radians = math.radians(angle_deg)
    return pygame.Vector2(math.cos(radians), math.sin(radians))


# Кэш для свечения (оптимизация - не создаём поверхности каждый кадр)
glow_cache = {}


def glow_circle(surface, color, position, radius, width=0, alpha=255):
    """Рисует круг с эффектом свечения (с кэшированием)"""
    if radius <= 0:
        return

    r = int(radius)
    cache_key = (r, tuple(color), width, alpha)

    cached_surface = glow_cache.get(cache_key)
    if cached_surface is None:
        temp = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        center = pygame.Vector2(temp.get_width() / 2, temp.get_height() / 2)
        glow_color = (*color, max(20, alpha // 4))
        pygame.draw.circle(temp, glow_color, center, r + 8)
        pygame.draw.circle(temp, (*color, alpha), center, r, width)
        glow_cache[cache_key] = temp
        cached_surface = temp

    rect = cached_surface.get_rect(center=(int(position.x), int(position.y)))
    surface.blit(cached_surface, rect)


def world_to_screen(pos, camera):
    """Преобразует мировые координаты в экранные (с учётом камеры)"""
    return pygame.Vector2(pos.x - camera.x, pos.y - camera.y)


# === ИГРОВЫЕ КЛАССЫ СУЩНОСТЕЙ ===

@dataclass
class Particle:
    """Частица для эффектов (взрывы, искры, следы)"""
    pos: pygame.Vector2      # Позиция
    vel: pygame.Vector2      # Скорость
    color: tuple             # Цвет
    life: float              # Оставшееся время жизни
    radius: float            # Радиус
    shrink: float = 1.4      # Скорость уменьшения

    def __post_init__(self):
        self.max_life = self.life

    def update(self, dt):
        self.life -= dt
        self.pos += self.vel * dt
        self.vel *= 0.94 ** (dt * 60)
        self.radius = max(0.0, self.radius - self.shrink * dt)
        return self.life > 0 and self.radius > 0

    def draw(self, surface, camera):
        t = clamp(self.life / self.max_life, 0, 1)
        color = tuple(int(channel * (0.35 + 0.65 * t)) for channel in self.color)
        screen_pos = world_to_screen(self.pos, camera)
        pygame.draw.circle(surface, color, (int(screen_pos.x), int(screen_pos.y)), int(self.radius))


@dataclass
class FloatingText:
    """Летающий текст (урон, уведомления, +опыт)"""
    pos: pygame.Vector2      # Позиция
    text: str                # Текст для отображения
    color: tuple             # Цвет
    life: float = 0.9        # Время жизни в секундах

    def __post_init__(self):
        self.max_life = self.life

    def update(self, dt):
        self.life -= dt
        self.pos.y -= 40 * dt
        return self.life > 0

    def draw(self, surface, camera, font):
        t = clamp(self.life / self.max_life, 0, 1)
        color = tuple(int(c * (0.5 + 0.5 * t)) for c in self.color)
        screen_pos = world_to_screen(self.pos, camera)
        draw_text(surface, font, self.text, color, screen_pos.x, screen_pos.y)


@dataclass
class Gem:
    """Кристалл опыта - выпадает из врагов"""
    pos: pygame.Vector2      # Позиция
    value: int               # Количество опыта
    vel: pygame.Vector2      # Скорость разлёта
    radius: int = 7          # Радиус для сбора

    def update(self, dt, player):
        collect_distance = player.radius + self.radius + 8
        distance = self.pos.distance_to(player.pos)
        # Увеличенная дистанция сбора и более быстрый магнит
        if distance <= collect_distance or distance < player.magnet_radius * 1.5:
            if distance < player.magnet_radius * 1.5:
                # Быстрое притягивание в зоне действия магнита
                direction = (player.pos - self.pos).normalize()
                pull_speed = 1200 + player.speed * 0.8
                step = min(distance, pull_speed * dt)
                self.pos += direction * step
                self.vel = direction * pull_speed
            else:
                self.pos = player.pos.copy()
                self.vel = pygame.Vector2()
            return False
        self.vel *= 0.92 ** (dt * 60)
        self.pos += self.vel * dt
        return self.pos.distance_to(player.pos) > collect_distance

    def draw(self, surface, camera):
        screen_pos = world_to_screen(self.pos, camera)
        glow_circle(surface, CYAN, screen_pos, self.radius + 3, alpha=100)
        pygame.draw.circle(surface, CYAN, (int(screen_pos.x), int(screen_pos.y)), self.radius)


@dataclass
class CoinPickup:
    """Монетка для покупок в магазине"""
    pos: pygame.Vector2      # Позиция
    amount: int             # Количество монет
    vel: pygame.Vector2      # Скорость разлёта
    radius: int = 8          # Радиус
    pulse: float = 0.0       # Анимация пульсации

    def update(self, dt, player):
        self.pulse += dt * 6.0
        distance = self.pos.distance_to(player.pos)
        collect_distance = player.radius + self.radius + 8
        if distance <= collect_distance or distance < player.magnet_radius:
            self.pos = player.pos.copy()
            self.vel = pygame.Vector2()
            return False

        self.vel *= 0.9 ** (dt * 60)
        self.pos += self.vel * dt
        return self.pos.distance_to(player.pos) > collect_distance

    def draw(self, surface, camera):
        bob = math.sin(self.pulse) * 2.4
        screen_pos = world_to_screen(self.pos + pygame.Vector2(0, bob), camera)
        glow_circle(surface, GOLD, screen_pos, self.radius + 4, alpha=135)
        pygame.draw.circle(surface, GOLD, (int(screen_pos.x), int(screen_pos.y)), self.radius)
        pygame.draw.circle(surface, (190, 120, 30), (int(screen_pos.x), int(screen_pos.y)), self.radius - 3)
        pygame.draw.circle(surface, (255, 240, 180), (int(screen_pos.x), int(screen_pos.y)), self.radius - 5)


@dataclass
class ExtraLifePickup:
    """Бонусная жизнь - периодически появляется на арене"""
    pos: pygame.Vector2      # Позиция
    radius: int = 16         # Радиус
    pulse: float = 0.0       # Анимация пульсации

    def update(self, dt):
        self.pulse += dt * 3.6

    def draw(self, surface, camera):
        bob = math.sin(self.pulse * 1.8) * 4
        screen_pos = world_to_screen(self.pos + pygame.Vector2(0, bob), camera)
        animated_radius = self.radius + math.sin(self.pulse * 2.4) * 2
        glow_circle(surface, PURPLE, screen_pos, animated_radius + 7, alpha=140)
        pygame.draw.circle(surface, (255, 105, 170), (int(screen_pos.x), int(screen_pos.y)), int(animated_radius))
        pygame.draw.circle(surface, WHITE, (int(screen_pos.x), int(screen_pos.y)), int(animated_radius * 0.6), 3)
        cross = animated_radius * 0.34
        pygame.draw.line(
            surface,
            WHITE,
            (int(screen_pos.x - cross), int(screen_pos.y)),
            (int(screen_pos.x + cross), int(screen_pos.y)),
            4,
        )
        pygame.draw.line(
            surface,
            WHITE,
            (int(screen_pos.x), int(screen_pos.y - cross)),
            (int(screen_pos.x), int(screen_pos.y + cross)),
            4,
        )


class Bullet:
    """Пуля (игрока или врага)"""
    def __init__(self, pos, vel, radius, damage, color, friendly=True, life=2.0, pierce=0):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.radius = radius
        self.damage = damage
        self.color = color
        self.friendly = friendly
        self.life = life
        self.pierce = pierce
        self.dead = False

    def update(self, dt):
        self.life -= dt
        self.pos += self.vel * dt
        if self.life <= 0:
            self.dead = True

    def draw(self, surface, camera):
        screen_pos = world_to_screen(self.pos, camera)
        glow_circle(surface, self.color, screen_pos, self.radius + 4, alpha=120)
        pygame.draw.circle(surface, self.color, (int(screen_pos.x), int(screen_pos.y)), self.radius)


class Drone:
    """Орбитальный дрон-спутник, вращается вокруг игрока и наносит урон врагам"""
    def __init__(self, index):
        self.index = index       # Индекс дрона (определяет начальный угол)
        self.angle = index * 90  # Начальный угол в градусах
        self.radius = 10         # Радиус дрона
        self.orbit = 70 + (index % 2) * 14  # Радиус орбиты
        self.damage = 28         # Базовый урон
        self.hit_cooldowns = {}  # Кулдауны урона для каждого врага

    def update(self, dt, player):
        self.angle = (self.angle + (170 + player.drone_count * 18) * dt) % 360
        expired = [enemy_id for enemy_id, timer in self.hit_cooldowns.items() if timer - dt <= 0]
        for enemy_id in expired:
            self.hit_cooldowns.pop(enemy_id, None)
        for enemy_id in list(self.hit_cooldowns):
            self.hit_cooldowns[enemy_id] -= dt

    def world_pos(self, player):
        return player.pos + angle_to_vector(self.angle) * self.orbit

    def try_hit(self, game):
        pos = self.world_pos(game.player)
        for enemy in game.enemies:
            if id(enemy) in self.hit_cooldowns:
                continue
            if pos.distance_to(enemy.pos) <= self.radius + enemy.radius:
                damage = self.damage * (1 + 0.14 * game.player.upgrade_counts["damage"])
                enemy.take_damage(game, damage, crit=False)
                self.hit_cooldowns[id(enemy)] = 0.28
                game.spawn_hit_burst(pos, CYAN, 6, 3.5)
                break

    def draw(self, surface, camera, player):
        pos = world_to_screen(self.world_pos(player), camera)
        glow_circle(surface, CYAN, pos, self.radius + 5, alpha=130)
        pygame.draw.circle(surface, (190, 250, 255), (int(pos.x), int(pos.y)), self.radius)
        pygame.draw.circle(surface, (40, 90, 120), (int(pos.x), int(pos.y)), self.radius - 4)


class Player:
    """Игрок - основной персонаж с управлением WASD + мышь"""
    def __init__(self, skin):
        # Позиция и движение
        self.pos = pygame.Vector2(WIDTH / 2, HEIGHT / 2)  # Стартовая позиция в центре
        self.vel = pygame.Vector2()        # Текущая скорость
        self.radius = 18                   # Радиус хитбокса
        self.base_speed = 310                # Базовая скорость передвижения
        self.facing = pygame.Vector2(1, 0)  # Направление взгляда

        # Характеристики
        self.max_health = 100                # Максимальное здоровье
        self.health = 100                    # Текущее здоровье
        self.shield_max = 0                  # Максимум щитов
        self.shield = 0                      # Текущие щиты
        self.extra_lives = 0                 # Количество доп. жизней
        self.regen_pool = 0.0                # Накопленная регенерация

        # Прогрессия
        self.level = 1                       # Уровень игрока
        self.xp = 0                          # Текущий опыт
        self.xp_goal = 35                  # Опыт до следующего уровня
        self.score = 0                       # Очки за забег

        # Таймеры
        self.damage_cooldown = 0.0           # Кулдаун между ударами
        self.shoot_timer = 0.0               # Кулдаун стрельбы
        self.dash_timer = 0.0                # Длительность текущего рывка
        self.dash_cooldown = 0.0             # Кулдаун рывка
        self.invuln = 0.0                    # Время неуязвимости

        # Боевые характеристики
        self.magnet_radius = 130             # Радиус притягивания кристаллов
        self.crit_chance = 0.08              # Шанс критического удара (8%)
        self.crit_bonus = 0.45               # Бонус критического урона (+45%)
        self.drone_count = 0                 # Количество дронов

        # Улучшения и внешний вид
        self.upgrade_counts = {key: 0 for key in UPGRADES}  # Уровни прокачки
        self.drones = []                     # Список дронов
        self.skin = skin                     # Текущий скин

    # === СВОЙСТВА (динамически вычисляются на основе улучшений) ===

    @property
    def speed(self):
        """Итоговая скорость с учётом улучшений"""
        return self.base_speed * (1 + 0.12 * self.upgrade_counts["move_speed"])

    @property
    def fire_delay(self):
        """Задержка между выстрелами (чем меньше, тем быстрее)"""
        return 0.24 / (1 + 0.18 * self.upgrade_counts["fire_rate"])

    @property
    def bullet_damage(self):
        """Урон одной пули с учётом улучшений"""
        return 26 * (1 + 0.22 * self.upgrade_counts["damage"])

    @property
    def bullet_speed(self):
        """Скорость полёта пуль"""
        return 720 + 24 * self.upgrade_counts["fire_rate"]

    @property
    def dash_cd_max(self):
        """Максимальный кулдаун рывка"""
        return max(1.1, 3.6 - 0.42 * self.upgrade_counts["dash"])

    @property
    def dash_power(self):
        """Скорость рывка (dash)"""
        return 780 + 70 * self.upgrade_counts["dash"]

    @property
    def pierce(self):
        """Количество пробиваний пули (сколько врагов прошьёт)"""
        return self.upgrade_counts["pierce"]

    @property
    def multishot(self):
        """Уровень многоствольности (+2 пули за уровень)"""
        return self.upgrade_counts["multishot"]

    @property
    def regen(self):
        """Регенерация здоровья за секунду"""
        return 1.2 * self.upgrade_counts["regen"]

    def apply_upgrade(self, upgrade_key):
        # Проверяем не достигнут ли максимальный уровень
        if self.upgrade_counts[upgrade_key] >= UPGRADES[upgrade_key]["max"]:
            return False  # Нельзя улучшить дальше

        self.upgrade_counts[upgrade_key] += 1
        if upgrade_key == "max_health":
            self.max_health += 20
            self.health = min(self.max_health, self.health + 55)
        elif upgrade_key == "magnet":
            self.magnet_radius += 50
        elif upgrade_key == "crit":
            self.crit_chance += 0.08
            self.crit_bonus += 0.25
        elif upgrade_key == "shield":
            self.shield_max += 1
            self.shield = self.shield_max
        elif upgrade_key == "drone":
            self.drone_count += 1
            self.rebuild_drones()

        return True  # Улучшение успешно

    def rebuild_drones(self):
        self.drones = [Drone(i) for i in range(self.drone_count)]

    def gain_xp(self, amount):
        self.xp += amount
        leveled = 0
        while self.xp >= self.xp_goal:
            self.xp -= self.xp_goal
            self.level += 1
            # Ограничиваем рост опыта чтобы не было бесконечного гринда
            if self.level <= 15:
                self.xp_goal = int(self.xp_goal * 1.28 + 10)
            elif self.level <= 25:
                self.xp_goal = int(self.xp_goal * 1.15 + 8)
            else:
                self.xp_goal = int(self.xp_goal * 1.05 + 5)
            leveled += 1
        return leveled

    def take_damage(self, amount):
        if self.invuln > 0:
            return False
        if self.shield > 0:
            self.shield -= 1
            self.invuln = 0.45
            return True
        self.health -= amount
        self.invuln = 0.6
        self.damage_cooldown = 0.2
        return True

    def revive(self, game):
        if self.extra_lives <= 0:
            return False
        self.extra_lives -= 1
        self.health = max(75, int(self.max_health * 0.65))
        self.invuln = 2.2
        self.damage_cooldown = 0.0
        self.dash_cooldown = min(self.dash_cooldown, 0.35)
        game.enemy_bullets.clear()
        game.shake += 14
        game.flash = 0.45
        game.spawn_hit_burst(self.pos, CYAN, 28, 7.5)
        game.floating_texts.append(FloatingText(self.pos.copy(), "ВТОРАЯ ЖИЗНЬ", CYAN, 1.6))
        for enemy in game.enemies:
            offset = enemy.pos - self.pos
            if 0 < offset.length_squared() <= 220 * 220:
                enemy.pos += offset.normalize() * 90
        return True

    def update(self, game, dt):
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(
            keys[pygame.K_d] - keys[pygame.K_a],
            keys[pygame.K_s] - keys[pygame.K_w],
        )
        if move.length_squared() > 0:
            move = move.normalize()

        mouse_world = pygame.Vector2(pygame.mouse.get_pos()) + game.camera
        aim = mouse_world - self.pos
        if aim.length_squared() > 0:
            self.facing = aim.normalize()

        self.shoot_timer = max(0.0, self.shoot_timer - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.invuln = max(0.0, self.invuln - dt)
        self.damage_cooldown = max(0.0, self.damage_cooldown - dt)

        if self.regen > 0 and self.health < self.max_health:
            self.regen_pool += self.regen * dt
            if self.regen_pool >= 1:
                heal = int(self.regen_pool)
                self.regen_pool -= heal
                self.health = min(self.max_health, self.health + heal)

        if self.dash_timer > 0:
            self.dash_timer -= dt
            self.pos += self.vel * dt
        else:
            acceleration = move * self.speed * 9.5
            self.vel = self.vel.lerp(acceleration * dt if move.length_squared() else pygame.Vector2(), 0.18)
            self.pos += move * self.speed * dt

        if keys[pygame.K_SPACE] and self.dash_cooldown <= 0:
            dash_dir = move if move.length_squared() else self.facing
            if dash_dir.length_squared() > 0:
                dash_dir = dash_dir.normalize()
                self.vel = dash_dir * self.dash_power
                self.dash_timer = 0.16
                self.dash_cooldown = self.dash_cd_max
                self.invuln = 0.24
                game.shake += 7
                game.spawn_hit_burst(self.pos, BLUE, 12, 5.5)

        self.pos.x = clamp(self.pos.x, -WORLD_PADDING, WIDTH + WORLD_PADDING)
        self.pos.y = clamp(self.pos.y, -WORLD_PADDING, HEIGHT + WORLD_PADDING)

        if pygame.mouse.get_pressed()[0]:
            self.shoot(game)

        for drone in self.drones:
            drone.update(dt, self)
            drone.try_hit(game)

    def shoot(self, game):
        if self.shoot_timer > 0:
            return

        shot_count = 1 + self.multishot * 2
        spread = 7 if shot_count > 1 else 0
        shots = []

        if shot_count == 1:
            shots.append(self.facing)
        else:
            center_index = (shot_count - 1) / 2
            perpendicular = pygame.Vector2(-self.facing.y, self.facing.x)
            for i in range(shot_count):
                offset = i - center_index
                direction = (self.facing * 1.0 + perpendicular * (offset * spread / 22)).normalize()
                shots.append(direction)

        self.shoot_timer = self.fire_delay
        for direction in shots:
            crit = random.random() < self.crit_chance
            damage = self.bullet_damage * (1 + self.crit_bonus if crit else 1)
            velocity = direction * self.bullet_speed
            bullet = Bullet(
                self.pos.copy(),
                velocity,
                5,
                damage,
                YELLOW if not crit else CYAN,
                friendly=True,
                life=1.7,
                pierce=self.pierce,
            )
            game.bullets.append(bullet)
            game.spawn_muzzle_flash(bullet.pos, bullet.color)

    def draw(self, surface, camera):
        pos = world_to_screen(self.pos, camera)
        body_color = self.skin["invuln"] if self.invuln > 0 else self.skin["body"]
        glow_circle(surface, body_color, pos, self.radius + 7, alpha=120)
        pygame.draw.circle(surface, body_color, (int(pos.x), int(pos.y)), self.radius)
        gun_tip = pos + self.facing * 20
        pygame.draw.circle(surface, self.skin["core"], (int(gun_tip.x), int(gun_tip.y)), 7)
        for drone in self.drones:
            drone.draw(surface, camera, self)


class Enemy:
    def __init__(self, kind, pos, wave):
        self.kind = kind
        data = ENEMY_DATA[kind]
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2()
        self.radius = data["radius"]
        wave_scale = 1 + wave * 0.11
        hp_scale = 1 + wave * 0.13
        self.is_boss = kind in BOSS_TYPES
        if self.is_boss:
            wave_scale = 1 + wave * 0.08
            hp_scale = 1 + max(0, wave - 3) * 0.22
        self.speed = data["speed"] * wave_scale
        self.max_hp = data["hp"] * hp_scale
        self.hp = self.max_hp
        self.damage = data["damage"] * (1 + wave * 0.05)
        self.xp = int(data["xp"] * (1 + wave * 0.04))
        self.score = data["score"] * wave
        self.color = data["color"]
        self.title = data.get("title", "")
        self.attack_timer = random.uniform(0.4, 1.2)
        self.contact_timer = 0.0
        self.dead = False
        self.mine_fuse = random.uniform(2.8, 5.5)
        self.wave = wave
        self.phase = 0
        self.summon_timer = 5.0
        self.special_timer = random.uniform(1.6, 3.2)
        self.orbit_angle = random.uniform(0, 360)

        # Уникальные механики для новых типов врагов
        self.ghost_phase_timer = 0.0
        self.ghost_phase_duration = random.uniform(0.8, 1.5)
        self.ghost_is_intangible = False

        self.spawner_death_triggered = False
        self.laser_charge_level = 0.0
        self.laser_max_charge = 2.0
        self.laser_charging = False

        self.rocket_explosions = []

        self.teleport_attack_cooldown = 0.0
        self.teleport_strikes = 0

    def update(self, game, dt):
        self.attack_timer -= dt
        self.contact_timer = max(0.0, self.contact_timer - dt)

        # Находим ближайшего игрока (P1 или P2) для наведения
        nearest_pos, distance = game._get_nearest_player(self.pos)
        to_player = nearest_pos - self.pos
        direction = to_player.normalize() if distance > 0 else pygame.Vector2()

        if self.kind == "chaser":
            self.vel = self.vel.lerp(direction * self.speed, 0.06)
        elif self.kind == "shooter":
            desired = 280
            side = pygame.Vector2(-direction.y, direction.x)
            move = pygame.Vector2()
            if distance > desired + 45:
                move += direction
            if distance < desired - 60:
                move -= direction
            move += side * math.sin(pygame.time.get_ticks() * 0.002 + self.pos.x * 0.01) * 0.7
            if move.length_squared() > 0:
                move = move.normalize()
            self.vel = self.vel.lerp(move * self.speed, 0.05)
            if self.attack_timer <= 0 and distance < 520:
                self.attack_timer = max(0.55, 1.55 - self.wave * 0.05)
                bullet = Bullet(
                    self.pos + direction * (self.radius + 8),
                    direction * 360,
                    6,
                    self.damage,
                    RED,
                    friendly=False,
                    life=3.0,
                )
                game.enemy_bullets.append(bullet)
                game.spawn_muzzle_flash(bullet.pos, RED)
        elif self.kind == "tank":
            pulse = math.sin(pygame.time.get_ticks() * 0.003 + self.pos.x * 0.02)
            drive = direction + pygame.Vector2(-direction.y, direction.x) * pulse * 0.3
            self.vel = self.vel.lerp(drive.normalize() * self.speed if drive.length_squared() else pygame.Vector2(),
                                     0.03)
            if self.attack_timer <= 0 and distance < 220:
                self.attack_timer = 1.4
                self.vel = direction * (self.speed * 2.4)
        elif self.kind == "splitter":
            wobble = pygame.Vector2(-direction.y, direction.x) * math.sin(
                pygame.time.get_ticks() * 0.006 + self.pos.y * 0.03) * 0.6
            move = direction + wobble
            self.vel = self.vel.lerp(move.normalize() * self.speed if move.length_squared() else pygame.Vector2(), 0.07)
        elif self.kind == "mine":
            self.mine_fuse -= dt
            self.vel = self.vel.lerp(direction * self.speed, 0.045)
            if distance < 95 or self.mine_fuse <= 0:
                self.explode(game)
                return
        elif self.kind == "ghost":
            # Механика фазового сдвига призрака
            self.ghost_phase_timer += dt
            if self.ghost_phase_timer >= self.ghost_phase_duration:
                self.ghost_phase_timer = 0.0
                # Призрак нематериален ровно 1 секунду
                self.ghost_is_intangible = not self.ghost_is_intangible
                self.ghost_phase_duration = 1.0 if self.ghost_is_intangible else random.uniform(1.2, 2.5)
                # Визуальный эффект смены фазы
                if self.ghost_is_intangible:
                    game.spawn_hit_burst(self.pos, (200, 150, 255), 4, 2.0)

            # Призрак движется хаотично и проходит сквозь препятствия
            wobble = pygame.Vector2(random.uniform(-1, 1), random.uniform(-1, 1)) * 0.3
            move = direction + wobble
            speed_multiplier = 1.5 if self.ghost_is_intangible else 1.0
            # Медленное ускорение (lerp 0.12 -> 0.05)
            self.vel = self.vel.lerp(
                move.normalize() * self.speed * speed_multiplier if move.length_squared() else pygame.Vector2(), 0.05)
        elif self.kind == "spawner":
            # Спавнер движется медленно и старается держаться на средней дистанции
            desired = 350
            move = pygame.Vector2()
            if distance > desired + 80:
                move += direction
            if distance < desired - 80:
                move -= direction
            if move.length_squared() > 0:
                move = move.normalize()
            self.vel = self.vel.lerp(move * self.speed, 0.02)
        elif self.kind == "laser":
            # Лазерный враг заряжается и стреляет лазерами
            if not self.laser_charging and self.attack_timer <= 0:
                self.laser_charging = True
                self.laser_charge_level = 0.0

            if self.laser_charging:
                # Быстрая зарядка (0.5 секунды всего цикл)
                self.laser_charge_level += dt * 2.0
                if self.laser_charge_level >= 1.0:
                    # Выстрел лазером при полной зарядке
                    self.laser_charging = False
                    self.attack_timer = 0.5
                    self.laser_charge_level = 0.0

                    # Визуальный эффект зарядки
                    game.spawn_hit_burst(self.pos, (255, 50, 50), 12, 4.0)

                    # Тройной лазерный выстрел
                    for i in range(3):
                        spread_angle = (i - 1) * 0.15
                        laser_dir = direction.rotate(math.degrees(spread_angle))
                        bullet = Bullet(
                            self.pos + direction * (self.radius + 8),
                            laser_dir * 800,
                            5,
                            self.damage * 1.5,
                            (255, 100, 100),
                            friendly=False,
                            life=2.0,
                        )
                        game.enemy_bullets.append(bullet)
                        game.spawn_muzzle_flash(bullet.pos, (255, 150, 150))

            # Медленнее движется во время зарядки
            speed_mult = 0.3 if self.laser_charging else 1.0
            self.vel = self.vel.lerp(direction * self.speed * speed_mult, 0.08)
        elif self.kind == "teleporter":
            # Телепортер случайно перемещается
            self.vel = self.vel.lerp(direction * self.speed * 0.3, 0.04)
            if self.attack_timer <= 0 and distance > 150:
                self.attack_timer = random.uniform(2.0, 3.5)
                # Телепортация ближе к игроку
                offset = angle_to_vector(random.uniform(0, 360)) * random.uniform(100, 200)
                self.pos = game.player.pos + offset
                game.spawn_hit_burst(self.pos, (255, 150, 255), 8, 4.0)
        elif self.kind == "rocket":
            # Ракетный враг стреляет взрывными ракетами
            if self.attack_timer <= 0 and distance < 400:
                self.attack_timer = 1.8  # Обычная скорострельность но залпом

                # Создаём класс взрывной ракеты один раз
                class ExplosiveRocket(Bullet):
                    def __init__(self, pos, vel, radius, damage, color, friendly=True, life=2.5):
                        super().__init__(pos, vel, radius, damage, color, friendly, life)
                        self.exploded = False

                    def update(self, dt):
                        super().update(dt)
                        if self.dead and not self.exploded:
                            self.explode()

                    def explode(self):
                        self.exploded = True
                        if hasattr(self, 'game_ref'):
                            self.game_ref.spawn_hit_burst(self.pos, (255, 150, 50), 15, 6.0)
                            if self.game_ref.apply_aoe_damage(self.pos, self.damage, 120):
                                self.game_ref.shake += 8

                # Одновременный залп из 4 ракет
                for i in range(4):
                    angle_offset = (i - 1.5) * 15
                    rocket_dir = (game.player.pos - self.pos).rotate(angle_offset).normalize()

                    rocket = ExplosiveRocket(
                        self.pos + rocket_dir * (self.radius + 8),
                        rocket_dir * 500,
                        10,
                        self.damage * 1.5,
                        (255, 150, 50),
                        friendly=False,
                        life=2.0,
                    )
                    rocket.game_ref = game
                    game.enemy_bullets.append(rocket)
                    game.spawn_muzzle_flash(rocket.pos, (255, 150, 50))

            self.vel = self.vel.lerp(direction * self.speed, 0.07)
        elif self.is_boss:
            self.update_boss(game, dt, direction, distance)

        self.pos += self.vel * dt

        if self.contact_timer <= 0 and game.damage_nearest_player_in_range(self.pos, self.damage,
                                                                            self.radius + game.player.radius):
            self.contact_timer = 0.7
            game.shake += 9
            game.spawn_hit_burst(game.player.pos, RED, 18, 6.0)
            if self.kind == "mine":
                self.explode(game)

    def update_boss(self, game, dt, direction, distance):
        if self.hp < self.max_hp * 0.66 and self.phase < 1:
            self.phase = 1
            game.floating_texts.append(FloatingText(self.pos.copy(), f"{self.title}: ярость", CYAN, 1.4))
        if self.hp < self.max_hp * 0.33 and self.phase < 2:
            self.phase = 2
            game.floating_texts.append(FloatingText(self.pos.copy(), f"{self.title}: фаза 3", CYAN, 1.4))

        if self.kind == "boss_core":
            self.update_core_boss(game, dt, direction)
        elif self.kind == "boss_blade":
            self.update_blade_boss(game, dt, direction)
        elif self.kind == "boss_hive":
            self.update_hive_boss(game, dt, direction)
        elif self.kind == "boss_tempest":
            self.update_tempest_boss(game, dt, direction)
        elif self.kind == "boss_void":
            self.update_void_boss(game, dt, direction)
        elif self.kind == "boss_omega":
            self.update_omega_boss(game, dt, direction)
        elif self.kind == "boss_overlord":
            self.update_overlord_boss(game, dt, direction)
        elif self.kind == "boss_crystal":
            self.update_crystal_boss(game, dt, direction)
        elif self.kind == "boss_time":
            self.update_time_boss(game, dt, direction)
        elif self.kind == "boss_flame":
            self.update_flame_boss(game, dt, direction)

        if game.damage_nearest_player_in_range(self.pos, self.damage * 1.4, self.radius + game.player.radius + 6):
            game.shake += 12
            game.spawn_hit_burst(game.player.pos, RED, 24, 7.5)

    def update_core_boss(self, game, dt, direction):
        arena_center = pygame.Vector2(WIDTH / 2, HEIGHT / 2)
        target = arena_center + angle_to_vector((pygame.time.get_ticks() * 0.035) % 360) * 180
        to_target = target - self.pos
        drift = to_target.normalize() if to_target.length_squared() > 0 else pygame.Vector2()
        self.vel = self.vel.lerp((drift * self.speed * 0.85) + direction * 40, 0.02)

        if self.attack_timer <= 0:
            if self.phase == 0:
                self.radial_burst(game, 12, 260, CYAN)
                self.attack_timer = 2.2
            elif self.phase == 1:
                self.radial_burst(game, 16, 300, CYAN)
                self.targeted_fan(game, direction, 6, 380, PURPLE)
                self.attack_timer = 1.7
            else:
                self.radial_burst(game, 22, 350, CYAN)
                self.targeted_fan(game, direction, 9, 440, PURPLE)
                self.attack_timer = 1.4

        self.summon_timer -= dt
        if self.summon_timer <= 0:
            self.summon_timer = max(2.5, 4.6 - self.phase * 0.8)
            for _ in range(2 + self.phase):
                offset = angle_to_vector(random.uniform(0, 360)) * random.uniform(70, 140)
                game.enemies.append(
                    Enemy(random.choice(["chaser", "shooter", "splitter"]), self.pos + offset, self.wave))

    def update_blade_boss(self, game, dt, direction):
        self.orbit_angle = (self.orbit_angle + (100 + self.phase * 35) * dt) % 360
        orbit_target = game.player.pos + angle_to_vector(self.orbit_angle) * (180 + self.phase * 18)
        to_target = orbit_target - self.pos
        drift = to_target.normalize() if to_target.length_squared() > 0 else pygame.Vector2()
        side = pygame.Vector2(-direction.y, direction.x)
        self.vel = self.vel.lerp(drift * self.speed + side * 60, 0.05)

        self.special_timer -= dt
        if self.special_timer <= 0:
            self.special_timer = max(1.2, 2.3 - self.phase * 0.3)
            self.vel = direction * (self.speed * (3.8 + self.phase * 0.4))
            game.spawn_hit_burst(self.pos, ORANGE, 14, 5.8)

        if self.attack_timer <= 0:
            self.targeted_fan(game, direction, 4 + self.phase * 3, 450 + self.phase * 60, ORANGE, spread=12)
            if self.phase > 0:
                self.radial_burst(game, 10 + self.phase * 3, 280 + self.phase * 30, RED)
            self.attack_timer = max(0.65, 1.1 - self.phase * 0.22)

    def update_hive_boss(self, game, dt, direction):
        arena_center = pygame.Vector2(WIDTH / 2, HEIGHT / 2)
        target = arena_center + angle_to_vector((pygame.time.get_ticks() * 0.022 + self.orbit_angle) % 360) * 230
        to_target = target - self.pos
        drift = to_target.normalize() if to_target.length_squared() > 0 else pygame.Vector2()
        self.vel = self.vel.lerp((drift * self.speed * 0.75) + direction * 30, 0.02)

        if self.attack_timer <= 0:
            self.radial_burst(game, 8 + self.phase * 3, 220 + self.phase * 22, PURPLE)
            self.attack_timer = max(0.92, 1.5 - self.phase * 0.22)

        self.summon_timer -= dt
        if self.summon_timer <= 0:
            self.summon_timer = max(1.7, 3.2 - self.phase * 0.5)
            pool = ["chaser", "splitter", "mine"] if self.phase > 0 else ["chaser", "splitter"]
            for _ in range(3 + self.phase):
                offset = angle_to_vector(random.uniform(0, 360)) * random.uniform(70, 150)
                game.enemies.append(Enemy(random.choice(pool), self.pos + offset, self.wave))

    def update_tempest_boss(self, game, dt, direction):
        # Босс Буря - быстрое движение с молниями
        self.vel = self.vel.lerp(direction * self.speed * 1.2, 0.08)

        if self.attack_timer <= 0:
            if self.phase == 0:
                # Удар молнии
                for i in range(5):
                    angle = (i * 72) + (pygame.time.get_ticks() * 0.1) % 360
                    lightning_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + lightning_dir * (self.radius + 10),
                        lightning_dir * 400,
                        6,
                        self.damage * 0.8,
                        (100, 255, 200),
                        friendly=False,
                        life=1.5,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 2.0
            elif self.phase == 1:
                # Спиральная молния
                for i in range(8):
                    angle = (pygame.time.get_ticks() * 0.003 + i * 45) % 360
                    spiral_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + spiral_dir * (self.radius + 15),
                        spiral_dir * 350,
                        5,
                        self.damage,
                        (150, 255, 220),
                        friendly=False,
                        life=2.0,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 1.5
            else:
                # Штормовой всплеск
                self.radial_burst(game, 12, 300, (100, 255, 200))
                self.attack_timer = 1.8

    def update_void_boss(self, game, dt, direction):
        # Босс Пустота - медленный но с гравитационными колодцами
        self.vel = self.vel.lerp(direction * self.speed * 0.6, 0.04)

        if self.attack_timer <= 0:
            if self.phase == 0:
                # Создание гравитационных колодцев притягивающих игрока
                for i in range(3):
                    well_pos = self.pos + angle_to_vector(random.uniform(0, 360)) * random.uniform(100, 200)
                    # Создаём визуальный эффект и применяем силу притяжения к игроку
                    game.spawn_hit_burst(well_pos, (50, 50, 80), 8, 3.0)
                    # Применяем силу притяжения к игроку (нужна ссылка на игрока)
                self.attack_timer = 3.0
            elif self.phase == 1:
                # Сферы тёмной материи
                for i in range(6):
                    angle = i * 60
                    orb_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + orb_dir * (self.radius + 20),
                        orb_dir * 200,
                        8,
                        self.damage * 1.2,
                        (80, 80, 120),
                        friendly=False,
                        life=3.0,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 2.5
            else:
                # Взрыв пустоты
                self.radial_burst(game, 15, 250, (50, 50, 80))
                self.attack_timer = 2.0

    def update_omega_boss(self, game, dt, direction):
        # Босс Омега - финальный босс со всеми способностями
        omega_speed = self.speed * (1.0 + self.phase * 0.3)
        self.vel = self.vel.lerp(direction * omega_speed, 0.1)

        if self.attack_timer <= 0:
            if self.phase == 0:
                # Комбинированная атака: лазеры + скорострельность
                for i in range(4):
                    angle = (pygame.time.get_ticks() * 0.002 + i * 90) % 360
                    laser_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + laser_dir * (self.radius + 12),
                        laser_dir * 500,
                        7,
                        self.damage,
                        (255, 255, 255),
                        friendly=False,
                        life=1.8,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 1.2
            elif self.phase == 1:
                # Омега-всплеск: все атаки предыдущих боссов
                self.radial_burst(game, 20, 350, (255, 255, 255))
                # Добавляем дополнительные снаряды
                for i in range(8):
                    angle = i * 45
                    omega_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + omega_dir * (self.radius + 25),
                        omega_dir * 400,
                        9,
                        self.damage * 1.5,
                        (200, 200, 255),
                        friendly=False,
                        life=2.5,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 2.5
            else:
                # Финальная фаза: абсолютное уничтожение
                for i in range(12):
                    angle = (pygame.time.get_ticks() * 0.005 + i * 30) % 360
                    ultimate_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + ultimate_dir * (self.radius + 30),
                        ultimate_dir * 600,
                        10,
                        self.damage * 2.0,
                        (255, 200, 200),
                        friendly=False,
                        life=1.5,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 1.0

    def update_overlord_boss(self, game, dt, direction):
        # Босс Властелин - мастер роя спавнящий огромное количество врагов
        arena_center = pygame.Vector2(WIDTH / 2, HEIGHT / 2)
        target = arena_center + angle_to_vector((pygame.time.get_ticks() * 0.025) % 360) * 200
        to_target = target - self.pos
        drift = to_target.normalize() if to_target.length_squared() > 0 else pygame.Vector2()
        self.vel = self.vel.lerp((drift * self.speed * 0.7) + direction * 25, 0.018)

        if self.attack_timer <= 0:
            if self.phase == 0:
                self.radial_burst(game, 12, 280, (180, 60, 180))
                self.attack_timer = 2.0
            elif self.phase == 1:
                self.radial_burst(game, 16, 320, (200, 80, 200))
                self.targeted_fan(game, direction, 5, 400, (220, 100, 220), spread=12)
                self.attack_timer = 1.6
            else:
                self.radial_burst(game, 20, 380, (240, 120, 240))
                self.targeted_fan(game, direction, 7, 480, (255, 140, 255), spread=10)
                self.attack_timer = 1.3

        self.summon_timer -= dt
        if self.summon_timer <= 0:
            self.summon_timer = max(1.5, 3.0 - self.phase * 0.6)
            # Спавним огромный рой
            spawn_count = 4 + self.phase * 2
            for _ in range(spawn_count):
                offset = angle_to_vector(random.uniform(0, 360)) * random.uniform(60, 130)
                enemy_type = random.choice(["chaser", "shooter", "splitter", "mine", "ghost", "laser", "rocket"])
                baby = Enemy(enemy_type, self.pos + offset, self.wave)
                baby.max_hp *= 0.8 + self.phase * 0.2
                baby.hp = baby.max_hp
                baby.damage *= 0.7 + self.phase * 0.15
                game.enemies.append(baby)

    def update_crystal_boss(self, game, dt, direction):
        # Босс Кристалл - стреляет отскакивающими кристальными осколками
        self.orbit_angle = (self.orbit_angle + (80 + self.phase * 25) * dt) % 360
        orbit_target = game.player.pos + angle_to_vector(self.orbit_angle) * (200 + self.phase * 25)
        to_target = orbit_target - self.pos
        drift = to_target.normalize() if to_target.length_squared() > 0 else pygame.Vector2()
        self.vel = self.vel.lerp(drift * self.speed * 0.9, 0.045)

        if self.attack_timer <= 0:
            if self.phase == 0:
                # Кристальные осколки отскакивающие (симулируется длительной жизнью)
                for i in range(6):
                    angle = i * 60 + (pygame.time.get_ticks() * 0.02) % 360
                    shard_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + shard_dir * (self.radius + 15),
                        shard_dir * 320,
                        8,
                        self.damage * 0.9,
                        (150, 255, 220),
                        friendly=False,
                        life=4.0,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 2.2
            elif self.phase == 1:
                # Быстрый кристальный обстрел
                for i in range(10):
                    angle = i * 36 + random.uniform(-10, 10)
                    shard_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + shard_dir * (self.radius + 20),
                        shard_dir * 380,
                        7,
                        self.damage * 1.1,
                        (170, 255, 230),
                        friendly=False,
                        life=3.5,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 1.7
            else:
                # Кристальный шторм - наведение + радиальный
                self.targeted_fan(game, direction, 5, 450, (200, 255, 240), spread=15)
                for i in range(12):
                    angle = i * 30 + (pygame.time.get_ticks() * 0.03) % 360
                    shard_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + shard_dir * (self.radius + 25),
                        shard_dir * 350,
                        9,
                        self.damage * 1.3,
                        (180, 255, 220),
                        friendly=False,
                        life=3.0,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 1.4

    def update_time_boss(self, game, dt, direction):
        # Босс Время - манипулирует временем и предсказывает движение игрока
        # Держится на средней дистанции
        desired_distance = 320
        move = pygame.Vector2()
        if distance := (game.player.pos - self.pos).length():
            if distance > desired_distance + 50:
                move += direction
            if distance < desired_distance - 50:
                move -= direction
        if move.length_squared() > 0:
            move = move.normalize()
        self.vel = self.vel.lerp(move * self.speed * 0.85, 0.035)

        if self.attack_timer <= 0:
            # Предсказываем куда будет игрок и стреляем туда
            player_vel = game.player.vel if hasattr(game.player, 'vel') else pygame.Vector2()
            prediction = game.player.pos + player_vel * 0.5
            to_prediction = prediction - self.pos
            pred_dir = to_prediction.normalize() if to_prediction.length_squared() > 0 else direction

            if self.phase == 0:
                # Выстрелы искажения времени
                for i in range(5):
                    angle = (i - 2) * 15
                    time_dir = pred_dir.rotate(angle)
                    bullet = Bullet(
                        self.pos + time_dir * (self.radius + 12),
                        time_dir * 280,
                        7,
                        self.damage * 0.85,
                        (100, 100, 255),
                        friendly=False,
                        life=3.5,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 2.0
            elif self.phase == 1:
                # Временной всплеск
                for i in range(8):
                    angle = i * 45 + (pygame.time.get_ticks() * 0.01) % 360
                    time_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + time_dir * (self.radius + 18),
                        time_dir * 320,
                        6,
                        self.damage,
                        (120, 120, 255),
                        friendly=False,
                        life=2.8,
                    )
                    game.enemy_bullets.append(bullet)
                self.targeted_fan(game, pred_dir, 3, 380, (140, 140, 255), spread=20)
                self.attack_timer = 1.6
            else:
                # Остановка времени + обстрел
                for i in range(16):
                    angle = i * 22.5
                    time_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + time_dir * (self.radius + 22),
                        time_dir * 300 + player_vel * 0.3,  # Лёгкое наведение
                        8,
                        self.damage * 1.2,
                        (80, 80, 255),
                        friendly=False,
                        life=2.5,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 1.3

    def update_flame_boss(self, game, dt, direction):
        # Босс Пламя - огненные волны и поджигающие атаки
        # Агрессивное преследование с периодическими отступлениями
        self.special_timer -= dt
        if self.special_timer <= 0:
            self.special_timer = max(2.0, 3.5 - self.phase * 0.4)
            # Рывок в сторону игрока
            self.vel = direction * (self.speed * 2.5)
            game.spawn_hit_burst(self.pos, (255, 100, 50), 12, 4.5)
        else:
            # Обычное движение
            self.vel = self.vel.lerp(direction * self.speed * 0.9, 0.05)

        if self.attack_timer <= 0:
            if self.phase == 0:
                # Огненная волна
                for i in range(8):
                    angle = i * 45 + random.uniform(-8, 8)
                    flame_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + flame_dir * (self.radius + 15),
                        flame_dir * 260,
                        8,
                        self.damage,
                        (255, 100, 50),
                        friendly=False,
                        life=2.5,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 2.0
            elif self.phase == 1:
                # Выброс огнемёта
                for i in range(12):
                    angle = direction.angle_to(pygame.Vector2(1, 0)) + (i - 6) * 8 + random.uniform(-5, 5)
                    flame_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + flame_dir * (self.radius + 12),
                        flame_dir * random.uniform(280, 380),
                        6,
                        self.damage * 0.9,
                        (255, 120, 70),
                        friendly=False,
                        life=1.8,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 1.5
            else:
                # Адский взрыв - радиальный + наведённый
                self.radial_burst(game, 14, 300, (255, 80, 40))
                for i in range(6):
                    angle = (pygame.time.get_ticks() * 0.008 + i * 60) % 360
                    inferno_dir = angle_to_vector(angle)
                    bullet = Bullet(
                        self.pos + inferno_dir * (self.radius + 20),
                        inferno_dir * 420,
                        10,
                        self.damage * 1.4,
                        (255, 60, 30),
                        friendly=False,
                        life=2.0,
                    )
                    game.enemy_bullets.append(bullet)
                self.attack_timer = 1.2

    def radial_burst(self, game, count, speed, color):
        for i in range(count):
            direction = angle_to_vector((360 / count) * i + random.uniform(-6, 6))
            bullet = Bullet(self.pos + direction * (self.radius + 8), direction * speed, 7, self.damage, color, False,
                            4.5)
            game.enemy_bullets.append(bullet)
        game.spawn_hit_burst(self.pos, color, count + 4, 5.2)

    def targeted_fan(self, game, direction, count, speed, color, spread=18):
        base_angle = pygame.Vector2(1, 0).angle_to(direction)
        for i in range(count):
            offset = (i - (count - 1) / 2) * spread
            fan_dir = angle_to_vector(base_angle + offset)
            bullet = Bullet(self.pos + fan_dir * (self.radius + 8), fan_dir * speed, 7, self.damage, color, False, 4.0)
            game.enemy_bullets.append(bullet)

    def explode(self, game):
        if self.dead:
            return
        self.dead = True
        game.spawn_hit_burst(self.pos, self.color, 22, 7.0)
        if game.damage_nearest_player_in_range(self.pos, self.damage, 95):
            game.shake += 10

    def take_damage(self, game, amount, crit=False):
        # Фазовый сдвиг призрака - без урона когда нематериален
        if self.kind == "ghost" and self.ghost_is_intangible:
            game.floating_texts.append(FloatingText(self.pos.copy(), "PHASE", (200, 150, 255), 0.8))
            return False

        self.hp -= amount
        color = CYAN if crit else WHITE
        game.floating_texts.append(FloatingText(self.pos.copy(), str(int(amount)), color))
        game.spawn_hit_burst(self.pos, self.color, 4 if not self.is_boss else 8, 3.2)

        if self.hp <= 0:
            self.kill(game)

    def kill(self, game):
        if self.dead:
            return
        self.dead = True
        game.player.score += int(self.score)
        game.spawn_hit_burst(self.pos, self.color, 18 if not self.is_boss else 42, 8.5)

        if self.kind == "splitter":
            for _ in range(2):
                baby = Enemy("chaser", self.pos + pygame.Vector2(random.uniform(-18, 18), random.uniform(-18, 18)),
                             self.wave)
                baby.max_hp *= 0.55
                baby.hp = baby.max_hp
                baby.xp = max(1, baby.xp // 2)
                game.enemies.append(baby)
        elif self.kind == "spawner" and not self.spawner_death_triggered:
            # Спавн нескольких больших врагов при смерти
            self.spawner_death_triggered = True
            for _ in range(5):
                offset = angle_to_vector(random.uniform(0, 360)) * random.uniform(50, 80)
                spawn_pos = self.pos + offset

                # Спавн случайного обычного врага (не босса)
                enemy_types = ["chaser", "shooter", "tank", "splitter", "mine", "ghost", "laser", "teleporter",
                               "rocket"]
                spawn_type = random.choice(enemy_types)
                baby = Enemy(spawn_type, spawn_pos, self.wave)
                baby.max_hp *= 2.0  # 100% more HP
                baby.hp = baby.max_hp
                baby.radius = int(baby.radius * 1.4)  # 40% larger
                baby.damage *= 1.5  # 50% more damage
                baby.xp = int(baby.xp * 2.0)
                baby.speed *= 0.9  # Немного медленнее из-за размера
                game.enemies.append(baby)
            game.spawn_hit_burst(self.pos, (255, 100, 150), 15, 6.0)

        if self.is_boss:
            game.boss_alive = False
            game.wave_cleared_flash = 1.4
            game.post_boss_timer = 3.0

        coin_amount = {
            "chaser": 1,
            "shooter": 2,
            "mine": 2,
            "splitter": 2,
            "tank": 3,
            "boss_core": 14,
            "boss_blade": 15,
            "boss_hive": 16,
        }.get(self.kind, 1)
        coin_amount = max(1, int(round(coin_amount * game.coin_multiplier)))
        game.spawn_coin_cluster(self.pos, coin_amount)

        for _ in range(2 if self.kind == "chaser" else 4 if not self.is_boss else 14):
            vel = pygame.Vector2(random.uniform(-160, 160), random.uniform(-160, 160))
            game.gems.append(Gem(self.pos.copy(), max(1, self.xp // (2 if self.is_boss else 1)), vel))

    def draw(self, surface, camera):
        pos = world_to_screen(self.pos, camera)
        glow_circle(surface, self.color, pos, self.radius + 6, alpha=120)
        pygame.draw.circle(surface, self.color, (int(pos.x), int(pos.y)), self.radius)
        inner = tuple(int(c * 0.42) for c in self.color)
        pygame.draw.circle(surface, inner, (int(pos.x), int(pos.y)), max(4, self.radius - 7))
        if self.hp < self.max_hp:
            bar_width = self.radius * 2.2
            bar_rect = pygame.Rect(0, 0, bar_width, 6)
            bar_rect.midbottom = (pos.x, pos.y - self.radius - 12)
            pygame.draw.rect(surface, (30, 35, 50), bar_rect, border_radius=3)
            fill = pygame.Rect(bar_rect)
            fill.width = max(0, bar_rect.width * (self.hp / self.max_hp))
            pygame.draw.rect(surface, self.color, fill, border_radius=3)

        # Отрисовка имени врага
        if hasattr(self, 'title') and self.title and not self.is_boss:
            font = pygame.font.SysFont("segoeui", 12)
            name_text = font.render(self.title.upper(), True, (200, 200, 200))
            text_rect = name_text.get_rect()
            text_rect.midtop = (pos.x, pos.y + self.radius + 8)
            surface.blit(name_text, text_rect)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Неоновая Арена: Протокол Затмение")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.fullscreen = False
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("segoeui", 18)
        self.font_ui = pygame.font.SysFont("segoeui", 24, bold=True)
        self.font_big = pygame.font.SysFont("segoeui", 54, bold=True)
        self.font_huge = pygame.font.SysFont("segoeui", 92, bold=True)
        self.running = True

        # Предварительное объявление изменяемых атрибутов для статических анализаторов
        self.cheat_manager = None
        self.accounts = []
        self.current_account = None
        self.account_buttons = []
        self.account_scroll_offset = 0.0
        self.account_scroll_target = 0
        self.new_account_name = ""
        self.editing_name = False
        self.coin_multiplier = 1.0
        self.player = Player(SKINS["classic"])
        self.enemies = []
        self.bullets = []
        self.enemy_bullets = []
        self.gems = []
        self.coins_pickups = []
        self.extra_life_pickups = []
        self.particles = []
        self.floating_texts = []
        self.camera = pygame.Vector2()
        self.shake = 0.0
        self.time = 0.0
        self.wave = 1
        self.wave_timer = 0.0
        self.wave_duration = 24.0
        self.spawn_timer = 0.2
        self.boss_alive = False
        self.upgrade_choices = []
        self.pending_levels = 0
        self._last_synced_level = 1
        self.flash = 0.0
        self.wave_cleared_flash = 0.0
        self.extra_life_timer = EXTRA_LIFE_SPAWN_TIME
        self.coin_spawn_timer = 14.0
        self.run_coins = 0
        self.shop_scroll_offset = 0.0
        self.shop_scroll_target = 0
        self.upgrade_scroll_offset = 0.0
        self.upgrade_scroll_target = 0
        self.boss_wave_counter = 0.0
        self.post_boss_timer = -1.0
        self.upgrade_rects = []
        self.pause_buttons = []
        self._client_shoot_timers = {}
        self.init_account_system()
        # Начинаем с выбора аккаунта если есть, иначе создаём дефолтный
        if self.accounts:
            self.state = "accounts"
            self.progress = self.default_progress()
        else:
            # Создаём аккаунт по умолчанию
            self.create_account("Игрок 1")
            self.select_account(self.accounts[0]["id"])
        self.background_stars = [
            (pygame.Vector2(random.uniform(-200, WIDTH + 200), random.uniform(-200, HEIGHT + 200)),
             random.randint(1, 3), random.randint(80, 180))
            for _ in range(90)
        ]
        self.menu_buttons = []
        self.shop_buttons = []
        self.new_game()

        # Состояние мультиплеера
        self.multiplayer_mode: str = "single"  # "single", "host", "client"
        self.network_host: Optional[GameHost] = None
        self.network_client: Optional[GameClient] = None
        self.remote_players: Dict[int, PlayerState] = {}  # player_id -> состояние игрока
        self.multiplayer_menu_buttons = []
        self.host_ip_input = ""
        self.available_hosts = []
        self.discovering_hosts = False
        self.editing_ip = False
        self.player2: Optional[Player] = None  # Для локального коопа или данных удалённого игрока

    def default_progress(self):
        return {
            "coins": 0,
            "selected_skin": "classic",
            "unlocked_skins": ["classic"],
            "shop_levels": {key: 0 for key in SHOP_UPGRADES},
        }

    def init_account_system(self):
        """Инициализировать систему аккаунтов - создать папку аккаунтов если нужно"""
        ACCOUNTS_DIR.mkdir(exist_ok=True)
        self.accounts = self.load_accounts_list()
        self.current_account = None
        self.account_buttons = []
        self.account_scroll_offset = 0
        self.account_scroll_target = 0
        self.new_account_name = ""
        self.editing_name = False

    def load_accounts_list(self):
        """Загрузить список доступных аккаунтов"""
        if ACCOUNTS_FILE.exists():
            try:
                data = json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
                return data.get("accounts", [])
            except Exception:
                return []
        return []

    def save_accounts_list(self):
        """Сохранить список аккаунтов"""
        try:
            payload = {"accounts": self.accounts}
            ACCOUNTS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[ACCOUNTS] Failed to save accounts list: {e}")

    def create_account(self, name):
        """Создать новый аккаунт с данным именем"""
        name = name.strip()
        if not name or len(name) > 20:
            return False
        # Проверка на дубликаты
        if any(acc["name"] == name for acc in self.accounts):
            return False
        # Создание аккаунта
        account_id = f"acc_{len(self.accounts)}_{random.randint(1000, 9999)}"
        self.accounts.append({"id": account_id, "name": name})
        self.save_accounts_list()
        # Создание файла сохранения для аккаунта
        account_file = ACCOUNTS_DIR / f"{account_id}.json"
        default_data = self.default_progress()
        try:
            account_file.write_text(json.dumps(default_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[ACCOUNTS] Failed to create account file: {e}")
            return False
        return True

    def delete_account(self, account_id):
        """Удалить аккаунт по ID"""
        self.accounts = [acc for acc in self.accounts if acc["id"] != account_id]
        self.save_accounts_list()
        # Удаление файла аккаунта
        account_file = ACCOUNTS_DIR / f"{account_id}.json"
        try:
            if account_file.exists():
                account_file.unlink()
        except Exception as e:
            print(f"[ACCOUNTS] Failed to delete account file: {e}")

    def load_progress(self, account_id=None):
        """Загрузить прогресс - либо для конкретного аккаунта, либо текущего"""
        if account_id is None:
            account_id = getattr(self, 'current_account', None)
        if account_id is None:
            return self.default_progress()
        account_file = ACCOUNTS_DIR / f"{account_id}.json"
        data = self.default_progress()
        if account_file.exists():
            try:
                loaded = json.loads(account_file.read_text(encoding="utf-8"))
                for key in data:
                    if key in loaded:
                        data[key] = loaded[key]
            except Exception as e:
                print(f"[ACCOUNTS] Failed to load account {account_id}: {e}")
        # Гарантируем что unlocked_skins это список с минимум "classic"
        if "unlocked_skins" not in data or not isinstance(data["unlocked_skins"], list):
            data["unlocked_skins"] = ["classic"]
        if "classic" not in data["unlocked_skins"]:
            data["unlocked_skins"].insert(0, "classic")
        # Гарантируем что selected_skin валиден
        if data.get("selected_skin") not in SKINS:
            data["selected_skin"] = "classic"
        # Гарантируем что shop_levels существуют
        if "shop_levels" not in data:
            data["shop_levels"] = {key: 0 for key in SHOP_UPGRADES}
        for key in SHOP_UPGRADES:
            if key not in data["shop_levels"]:
                data["shop_levels"][key] = 0
        data["coins"] = max(0, int(data.get("coins", 0)))
        return data

    def save_progress(self):
        """Сохранить прогресс для текущего аккаунта"""
        if self.current_account is None:
            return
        account_file = ACCOUNTS_DIR / f"{self.current_account}.json"
        payload = {
            "coins": int(self.progress["coins"]),
            "selected_skin": self.progress["selected_skin"],
            "unlocked_skins": list(self.progress["unlocked_skins"]),
            "shop_levels": {key: int(value) for key, value in self.progress["shop_levels"].items()},
        }
        try:
            account_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[ACCOUNTS] Failed to save progress: {e}")

    def select_account(self, account_id):
        """Выбрать аккаунт и загрузить его прогресс"""
        self.current_account = account_id
        self.progress = self.load_progress(account_id)
        self.state = "menu"

    @property
    def total_coins(self):
        return self.progress["coins"]

    def add_coins(self, amount):
        if amount <= 0:
            return
        self.progress["coins"] += amount
        self.save_progress()

    def spend_coins(self, amount):
        if amount > self.progress["coins"]:
            return False
        self.progress["coins"] -= amount
        self.save_progress()
        return True

    def selected_skin_data(self):
        return SKINS[self.progress["selected_skin"]]

    def apply_meta_upgrades(self):
        self.coin_multiplier = 1.0 + self.progress["shop_levels"]["coin_bonus"] * 0.25
        for shop_key, meta in SHOP_UPGRADES.items():
            ingame_upgrade = meta["ingame_upgrade"]
            if not ingame_upgrade:
                continue
            level = self.progress["shop_levels"][shop_key]
            for _ in range(level):
                self.player.apply_upgrade(ingame_upgrade)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))

    def new_game(self):
        self.player = Player(self.selected_skin_data())
        self.enemies = []
        self.bullets = []
        self.enemy_bullets = []
        self.gems = []
        self.coins_pickups = []
        self.extra_life_pickups = []
        self.particles = []
        self.floating_texts = []
        self.camera = pygame.Vector2()
        self.shake = 0.0
        self.time = 0.0
        self.wave = 1
        self.wave_timer = 0.0
        self.wave_duration = 24.0
        self.spawn_timer = 0.2
        self.boss_alive = False
        self.upgrade_choices = []
        self.pending_levels = 0
        self._last_synced_level = self.player.level
        self.flash = 0.0
        self.wave_cleared_flash = 0.0
        self.extra_life_timer = EXTRA_LIFE_SPAWN_TIME
        self.coin_spawn_timer = 14.0
        self.run_coins = 0
        self.apply_meta_upgrades()
        self.shop_scroll_offset = 0
        self.shop_scroll_target = 0
        self.upgrade_scroll_offset = 0
        self.upgrade_scroll_target = 0
        self.boss_wave_counter = 0
        self.post_boss_timer = -1.0

    def spawn_muzzle_flash(self, pos, color):
        for _ in range(4):
            vel = pygame.Vector2(random.uniform(-120, 120), random.uniform(-120, 120))
            self.particles.append(Particle(pygame.Vector2(pos), vel, color, 0.22, random.uniform(3.0, 5.5), 8.2))

    def spawn_hit_burst(self, pos, color, amount, speed):
        for _ in range(amount):
            direction = angle_to_vector(random.uniform(0, 360))
            velocity = direction * random.uniform(speed * 14, speed * 28)
            self.particles.append(
                Particle(pygame.Vector2(pos), velocity, color, random.uniform(0.28, 0.65), random.uniform(2.5, 5.2),
                         7.0))

    def choose_upgrades(self):
        available = []
        for key, meta in UPGRADES.items():
            if self.player.upgrade_counts[key] < meta["max"]:
                available.append(key)
        if not available:
            return []
        random.shuffle(available)
        return available[: min(3, len(available))]

    def random_arena_position(self, margin=70):
        return pygame.Vector2(
            random.uniform(-WORLD_PADDING + margin, WIDTH + WORLD_PADDING - margin),
            random.uniform(-WORLD_PADDING + margin, HEIGHT + WORLD_PADDING - margin),
        )

    def inside_arena(self, pos, margin=0):
        return (
                -WORLD_PADDING - margin <= pos.x <= WIDTH + WORLD_PADDING + margin
                and -WORLD_PADDING - margin <= pos.y <= HEIGHT + WORLD_PADDING + margin
        )

    def spawn_extra_life(self):
        pos = self.random_arena_position(90)
        for _ in range(20):
            if pos.distance_to(self.player.pos) >= 220:
                break
            pos = self.random_arena_position(90)
        self.extra_life_pickups.append(ExtraLifePickup(pos))
        self.floating_texts.append(FloatingText(pos.copy(), "НА КАРТЕ ВТОРАЯ ЖИЗНЬ", PURPLE, 1.8))
        self.spawn_hit_burst(pos, PURPLE, 14, 4.8)

    def spawn_coin_cluster(self, pos=None, amount=3):
        base_pos = pygame.Vector2(pos) if pos is not None else self.random_arena_position(110)
        for _ in range(amount):
            offset = pygame.Vector2(random.uniform(-18, 18), random.uniform(-18, 18))
            vel = pygame.Vector2(random.uniform(-100, 100), random.uniform(-100, 100))
            self.coins_pickups.append(CoinPickup(base_pos + offset, 1, vel))

    def spawn_enemy(self, forced_kind=None):
        margin = 90
        side = random.choice(["top", "bottom", "left", "right"])
        if side == "top":
            pos = pygame.Vector2(random.uniform(-margin, WIDTH + margin), -margin)
        elif side == "bottom":
            pos = pygame.Vector2(random.uniform(-margin, WIDTH + margin), HEIGHT + margin)
        elif side == "left":
            pos = pygame.Vector2(-margin, random.uniform(-margin, HEIGHT + margin))
        else:
            pos = pygame.Vector2(WIDTH + margin, random.uniform(-margin, HEIGHT + margin))

        if forced_kind:
            kind = forced_kind
        else:
            options = [("chaser", 35), ("shooter", 18), ("splitter", 15), ("mine", 10), ("ghost", 12)]
            if self.wave >= 2:
                options.append(("laser", 10))
            if self.wave >= 3:
                options.append(("tank", 12))
                options.append(("rocket", 8))
            if self.wave >= 4:
                options.append(("teleporter", 6))
            if self.wave >= 5:
                options.append(("spawner", 4))
            population = []
            for enemy_type, weight in options:
                population.extend([enemy_type] * weight)
            kind = random.choice(population)
        self.enemies.append(Enemy(kind, pos, self.wave))

    def spawn_boss(self):
        self.boss_alive = True
        self.boss_wave_counter = 0  # Сброс счётчика при появлении босса
        # Прогрессивное появление боссов с увеличением сложности - всего 10 боссов
        if self.wave < 6:
            boss_kind = "boss_core"
        elif self.wave < 10:
            boss_kind = "boss_blade"
        elif self.wave < 14:
            boss_kind = "boss_hive"
        elif self.wave < 18:
            boss_kind = "boss_tempest"
        elif self.wave < 22:
            boss_kind = "boss_void"
        elif self.wave < 26:
            boss_kind = "boss_omega"
        elif self.wave < 30:
            boss_kind = "boss_overlord"
        elif self.wave < 34:
            boss_kind = "boss_crystal"
        elif self.wave < 38:
            boss_kind = "boss_time"
        else:
            boss_kind = "boss_flame"

        boss = Enemy(boss_kind, pygame.Vector2(WIDTH / 2, -120), self.wave)
        # Масштабирование сложности босса с номером волны
        if self.wave >= 36:
            boss.hp *= 1.5  # На 50% больше ОЗ для крайне поздней игры
            boss.damage *= 1.3  # На 30% больше урона
            boss.speed *= 1.15  # На 15% быстрее
        elif self.wave >= 30:
            boss.hp *= 1.35  # На 35% больше ОЗ для поздней игры
            boss.damage *= 1.2  # На 20% больше урона
            boss.speed *= 1.1  # На 10% быстрее
        elif self.wave >= 24:
            boss.hp *= 1.25  # На 25% больше ОЗ для поздней игры
            boss.damage *= 1.15  # На 15% больше урона
        elif self.wave >= 20:
            boss.hp *= 1.2  # На 20% больше ОЗ
            boss.damage *= 1.1  # На 10% больше урона
        elif self.wave >= 16:
            boss.hp *= 1.1  # На 10% больше ОЗ для средне-поздней игры

        self.enemies.append(boss)
        self.floating_texts.append(FloatingText(pygame.Vector2(WIDTH / 2, HEIGHT / 2), boss.title.upper(), CYAN, 1.8))
        self.shake += 12

    def update_playing(self, dt):
        self.time += dt
        if self.post_boss_timer <= 0:
            self.wave_timer += dt
        self.extra_life_timer -= dt
        self.coin_spawn_timer -= dt
        self.flash = max(0.0, self.flash - dt)
        self.wave_cleared_flash = max(0.0, self.wave_cleared_flash - dt)

        # Обновление счётчика волн босса когда нет босса
        if not self.boss_alive:
            self.boss_wave_counter += dt

        # Обработка сети мультиплеера
        if self.multiplayer_mode == "host" and self.network_host:
            # Хост: обновление игрока 1, обработка удалённых игроков, отправка состояния
            self.player.update(self, dt)
            # Обработка ввода клиентов и обновление удалённых игроков
            self._process_client_inputs(dt)
            # Отправка состояния игры всем клиентам
            self._send_host_state()
        elif self.multiplayer_mode in ("client", "client_connected") and self.network_client:
            # Клиент: отправка ввода хосту, получение обновлений состояния
            self._send_client_input()
            self._receive_client_state()
            # Всё ещё обновляем игрока для стрельбы, рывков, способностей (позиция синхронизируется с сервера)
            self.player.update(self, dt)
        else:
            # Одиночный режим
            self.player.update(self, dt)

        while self.extra_life_timer <= 0:
            self.extra_life_timer += EXTRA_LIFE_SPAWN_TIME
            self.spawn_extra_life()

        while self.coin_spawn_timer <= 0:
            self.coin_spawn_timer += 18.0
            self.spawn_coin_cluster(amount=random.randint(3, 5))

        if self.post_boss_timer > 0:
            self.post_boss_timer -= dt
            if self.post_boss_timer <= 0:
                self.wave += 1
                self.wave_timer = 0.0
                self.floating_texts.append(FloatingText(self.player.pos.copy(), f"ВОЛНА {self.wave}", CYAN, 1.25))
                self.flash = 0.3
        else:
            if not self.boss_alive and self.wave_timer >= self.wave_duration:
                self.wave += 1
                self.wave_timer = 0.0
                self.floating_texts.append(FloatingText(self.player.pos.copy(), f"ВОЛНА {self.wave}", CYAN, 1.25))
                self.flash = 0.3
                if self.wave % 4 == 0:
                    self.spawn_boss()

            if not self.boss_alive:
                self.spawn_timer -= dt
                if self.spawn_timer <= 0:
                    self.spawn_enemy()
                    base = max(0.16, 1.05 - self.wave * 0.05)
                    self.spawn_timer = random.uniform(base * 0.65, base * 1.18)

        for bullet in self.bullets:
            bullet.update(dt)
            if not self.inside_arena(bullet.pos, bullet.radius):
                bullet.dead = True
        for bullet in self.enemy_bullets:
            bullet.update(dt)
            if not self.inside_arena(bullet.pos, bullet.radius):
                bullet.dead = True

        if self.multiplayer_mode != "client_connected":
            for enemy in self.enemies:
                enemy.update(self, dt)

        # Обработка столкновений - хост авторитетен для здоровья, клиент только для визуальных пуль
        if self.multiplayer_mode == "client_connected":
            # Клиент: только визуальная обработка столкновений пуль, здоровье синхронизируется с хоста
            self._handle_client_collisions()
        else:
            # Хост или одиночный режим: полная обработка столкновений
            self.handle_collisions()

        self.bullets = [bullet for bullet in self.bullets if not bullet.dead]
        self.enemy_bullets = [bullet for bullet in self.enemy_bullets if not bullet.dead]
        self.enemies = [enemy for enemy in self.enemies if not enemy.dead]

        if self.multiplayer_mode == "client_connected":
            # Хост авторитетен для подборов и прогресса в мультиплеере.
            # Клиент только анимирует уже синхронизированные подборы.
            for gem in self.gems:
                gem.vel *= 0.92 ** (dt * 60)
                gem.pos += gem.vel * dt
            for coin in self.coins_pickups:
                coin.pulse += dt * 6.0
                coin.vel *= 0.9 ** (dt * 60)
                coin.pos += coin.vel * dt
        else:
            new_gems = []
            for gem in self.gems:
                if self.multiplayer_mode == "host" and self.remote_players:
                    # Логика подбора от хоста для всех игроков (P1 + удалённые игроки)
                    collectors = [(1, self.player.pos, self.player.radius, self.player.magnet_radius)]
                    for pid, p_state in self.remote_players.items():
                        collectors.append((pid, pygame.Vector2(p_state.pos_x, p_state.pos_y), 18, 130))

                    collected_by = None
                    best_magnet_target = None
                    best_magnet_distance = float("inf")
                    for collector_id, collector_pos, collector_radius, magnet_radius in collectors:
                        if gem.pos.distance_to(collector_pos) <= collector_radius + gem.radius + 8:
                            collected_by = collector_id
                            break
                        magnet_range = magnet_radius * 1.5
                        dist = gem.pos.distance_to(collector_pos)
                        if dist < magnet_range and dist < best_magnet_distance:
                            best_magnet_target = collector_pos
                            best_magnet_distance = dist

                    if collected_by is None:
                        if best_magnet_target is not None and best_magnet_distance > 0:
                            direction = (best_magnet_target - gem.pos).normalize()
                            pull_speed = 1200 + self.player.base_speed * 0.8
                            step = min(best_magnet_distance, pull_speed * dt)
                            gem.pos += direction * step
                            gem.vel = direction * pull_speed
                        else:
                            gem.vel *= 0.92 ** (dt * 60)
                            gem.pos += gem.vel * dt
                        new_gems.append(gem)
                    else:
                        if collected_by == 1:
                            gained_levels = self.player.gain_xp(gem.value)
                            if gained_levels:
                                self.pending_levels += gained_levels
                        elif collected_by in self.remote_players:
                            p_state = self.remote_players[collected_by]
                            p_state.xp += gem.value
                            while p_state.xp >= p_state.xp_goal:
                                p_state.xp -= p_state.xp_goal
                                p_state.level += 1
                                if p_state.level <= 15:
                                    p_state.xp_goal = int(p_state.xp_goal * 1.28 + 10)
                                elif p_state.level <= 25:
                                    p_state.xp_goal = int(p_state.xp_goal * 1.15 + 8)
                                else:
                                    p_state.xp_goal = int(p_state.xp_goal * 1.05 + 5)
                        self.spawn_hit_burst(gem.pos, CYAN, 5, 2.8)
                else:
                    if gem.update(dt, self.player):
                        new_gems.append(gem)
                    else:
                        gained_levels = self.player.gain_xp(gem.value)
                        if gained_levels:
                            self.pending_levels += gained_levels
                        self.spawn_hit_burst(gem.pos, CYAN, 5, 2.8)
            self.gems = new_gems

            remaining_coins = []
            for coin in self.coins_pickups:
                if self.multiplayer_mode == "host" and self.remote_players:
                    collectors = [(1, self.player.pos, self.player.radius, self.player.magnet_radius)]
                    for pid, p_state in self.remote_players.items():
                        collectors.append((pid, pygame.Vector2(p_state.pos_x, p_state.pos_y), 18, 130))

                    collected_by = None
                    best_magnet_target = None
                    best_magnet_distance = float("inf")
                    for collector_id, collector_pos, collector_radius, magnet_radius in collectors:
                        if coin.pos.distance_to(collector_pos) <= collector_radius + coin.radius + 8:
                            collected_by = collector_id
                            break
                        dist = coin.pos.distance_to(collector_pos)
                        if dist < magnet_radius and dist < best_magnet_distance:
                            best_magnet_target = collector_pos
                            best_magnet_distance = dist

                    if collected_by is None:
                        coin.pulse += dt * 6.0
                        if best_magnet_target is not None and best_magnet_distance > 0:
                            direction = (best_magnet_target - coin.pos).normalize()
                            pull_speed = 900 + self.player.base_speed * 0.6
                            step = min(best_magnet_distance, pull_speed * dt)
                            coin.pos += direction * step
                            coin.vel = direction * pull_speed
                        else:
                            coin.vel *= 0.9 ** (dt * 60)
                            coin.pos += coin.vel * dt
                        remaining_coins.append(coin)
                    else:
                        if collected_by == 1:
                            self.run_coins += coin.amount
                            self.add_coins(coin.amount)
                        self.floating_texts.append(FloatingText(coin.pos.copy(), f"+{coin.amount} мон.", GOLD, 0.8))
                        self.spawn_hit_burst(coin.pos, GOLD, 6, 3.0)
                else:
                    if coin.update(dt, self.player):
                        remaining_coins.append(coin)
                    else:
                        self.run_coins += coin.amount
                        self.add_coins(coin.amount)
                        self.floating_texts.append(FloatingText(coin.pos.copy(), f"+{coin.amount} мон.", GOLD, 0.8))
                        self.spawn_hit_burst(coin.pos, GOLD, 6, 3.0)
            self.coins_pickups = remaining_coins

        remaining_extra_lives = []
        for pickup in self.extra_life_pickups:
            pickup.update(dt)
            if pickup.pos.distance_to(self.player.pos) <= pickup.radius + self.player.radius + 4:
                self.player.extra_lives += 1
                self.floating_texts.append(FloatingText(pickup.pos.copy(), "ВТОРАЯ ЖИЗНЬ +1", CYAN, 1.4))
                self.spawn_hit_burst(pickup.pos, PURPLE, 18, 5.4)
            else:
                remaining_extra_lives.append(pickup)
        self.extra_life_pickups = remaining_extra_lives

        self.particles = [particle for particle in self.particles if particle.update(dt)]
        self.floating_texts = [text for text in self.floating_texts if text.update(dt)]

        if self.pending_levels > 0 and self.state == "playing":
            self.pending_levels -= 1
            self.upgrade_choices = self.choose_upgrades()
            if self.upgrade_choices:
                self.state = "upgrade"
                if self.multiplayer_mode == "single":
                    self.shake = 0
            else:
                # Все улучшения на максимуме. Даём утешительный приз.
                self.player.health = min(self.player.max_health, self.player.health + 25)
                self.add_coins(50)
                self.floating_texts.append(FloatingText(self.player.pos.copy(), "+25 ОЗ, +50 МОНЕТ", GOLD, 1.5))
                self.spawn_hit_burst(self.player.pos, GOLD, 12, 4.0)

        if self.player.health <= 0 and not self.player.revive(self):
            self.state = "game_over"

        self.update_camera(dt)
        # Обновление эффектов читов
        if self.cheat_manager:
            self.cheat_manager.update(self, dt)

    def update_camera(self, dt):
        target = self.player.pos - CENTER
        self.camera = self.camera.lerp(target, 0.12)
        self.shake = max(0.0, self.shake - dt * 14)
        if self.shake > 0:
            self.camera += pygame.Vector2(random.uniform(-self.shake, self.shake),
                                          random.uniform(-self.shake, self.shake))

    def handle_collisions(self):
        for bullet in self.bullets:
            if bullet.dead:
                continue
            for enemy in self.enemies:
                if enemy.dead:
                    continue
                if bullet.pos.distance_to(enemy.pos) <= bullet.radius + enemy.radius:
                    crit = bullet.color == CYAN
                    enemy.take_damage(self, bullet.damage, crit=crit)
                    bullet.pierce -= 1
                    if bullet.pierce < 0:
                        bullet.dead = True
                    else:
                        bullet.damage *= 0.78
                    break

        for bullet in self.enemy_bullets:
            if bullet.dead:
                continue
            # Безопасность: вражеские пули никогда не должны содержать дружественные снаряды
            if bullet.friendly:
                continue
            if bullet.pos.distance_to(self.player.pos) <= bullet.radius + self.player.radius:
                if self.player.take_damage(bullet.damage):
                    self.shake += 8
                    self.spawn_hit_burst(self.player.pos, RED, 10, 4.8)
                bullet.dead = True
                # Пуля поглощается после попадания в игрока-хоста
                continue
            # Проверка столкновения с удалёнными игроками (только хост)
            if self.multiplayer_mode == "host":
                for p_state in self.remote_players.values():
                    p_pos = pygame.Vector2(p_state.pos_x, p_state.pos_y)
                    if bullet.pos.distance_to(p_pos) <= bullet.radius + 24:
                        p_state.health -= bullet.damage
                        if p_state.health <= 0:
                            if p_state.extra_lives > 0:
                                p_state.extra_lives -= 1
                                p_state.health = p_state.max_health
                            else:
                                p_state.health = 0
                        bullet.dead = True
                        break

    def _handle_client_collisions(self):
        """Клиентская сторона: обработать столкновения пуль только для визуальной обратной связи, без изменения здоровья"""
        # Обработка пуль игрока попадающих во врагов (только визуально - урон на хосте)
        for bullet in self.bullets:
            if bullet.dead or not bullet.friendly:
                continue
            for enemy in self.enemies:
                if enemy.dead:
                    continue
                if bullet.pos.distance_to(enemy.pos) <= bullet.radius + enemy.radius:
                    bullet.dead = True
                    # Только визуальный эффект, без расчёта урона
                    break

        # Обработка вражеских пуль - только визуально, здоровье синхронизируется с хоста
        for bullet in self.enemy_bullets:
            if bullet.dead:
                continue
            if bullet.pos.distance_to(self.player.pos) <= bullet.radius + self.player.radius:
                # Только визуальный эффект - реальный урон на хосте
                bullet.dead = True

    def _get_nearest_player(self, pos):
        """Найти ближайшего игрока к данной позиции (для наведения врагов)"""
        nearest = self.player.pos
        min_dist = pos.distance_to(self.player.pos)

        # Проверка удалённых игроков
        for p_state in self.remote_players.values():
            p_pos = pygame.Vector2(p_state.pos_x, p_state.pos_y)
            dist = pos.distance_to(p_pos)
            if dist < min_dist:
                min_dist = dist
                nearest = p_pos

        return nearest, min_dist

    def _apply_remote_damage(self, p_state, amount):
        """Применить авторитетные правила урона к удалённому игроку."""
        if p_state.invuln > 0:
            return False
        if p_state.shield > 0:
            p_state.shield -= 1
            p_state.invuln = 0.45
            return True
        p_state.health -= amount
        p_state.invuln = 0.6
        if p_state.health <= 0:
            if p_state.extra_lives > 0:
                p_state.extra_lives -= 1
                p_state.health = p_state.max_health
                p_state.invuln = 2.2
            else:
                p_state.health = 0
        return True

    def damage_nearest_player_in_range(self, source_pos, amount, hit_range):
        """Нанести урон ближайшему игроку (хост или удалённый) если в радиусе."""
        nearest_kind = "local"
        nearest_state = None
        min_dist = source_pos.distance_to(self.player.pos)

        for p_state in self.remote_players.values():
            if p_state.health <= 0:
                continue
            p_pos = pygame.Vector2(p_state.pos_x, p_state.pos_y)
            dist = source_pos.distance_to(p_pos)
            if dist < min_dist:
                min_dist = dist
                nearest_kind = "remote"
                nearest_state = p_state

        if min_dist > hit_range:
            return False

        if nearest_kind == "local":
            return self.player.take_damage(amount)
        return self._apply_remote_damage(nearest_state, amount)

    def apply_aoe_damage(self, center_pos, base_damage, radius):
        """Применить радиальный урон локальным и удалённым игрокам."""
        any_hit = False
        local_dist = center_pos.distance_to(self.player.pos)
        if local_dist < radius:
            aoe_damage = base_damage * (1.0 - local_dist / radius)
            if self.player.take_damage(int(aoe_damage)):
                any_hit = True

        for p_state in self.remote_players.values():
            if p_state.health <= 0:
                continue
            p_pos = pygame.Vector2(p_state.pos_x, p_state.pos_y)
            dist = center_pos.distance_to(p_pos)
            if dist < radius:
                aoe_damage = base_damage * (1.0 - dist / radius)
                if self._apply_remote_damage(p_state, int(aoe_damage)):
                    any_hit = True
        return any_hit

    def draw_background(self):
        self.screen.fill(BG_COLOR)
        grid_offset_x = int(self.camera.x * 0.35) % 56
        grid_offset_y = int(self.camera.y * 0.35) % 56
        for x in range(-56, WIDTH + 56, 56):
            pygame.draw.line(self.screen, GRID_COLOR, (x - grid_offset_x, 0), (x - grid_offset_x, HEIGHT), 1)
        for y in range(-56, HEIGHT + 56, 56):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y - grid_offset_y), (WIDTH, y - grid_offset_y), 1)

        for pos, radius, brightness in self.background_stars:
            star = pos - self.camera * 0.08
            sx = int(star.x % (WIDTH + 280) - 140)
            sy = int(star.y % (HEIGHT + 280) - 140)
            color = (brightness, brightness, min(255, brightness + 40))
            pygame.draw.circle(self.screen, color, (sx, sy), radius)

        vignette = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(vignette, (0, 0, 0, 0), vignette.get_rect())
        pygame.draw.circle(vignette, (0, 0, 0, 0), (WIDTH // 2, HEIGHT // 2), 280)
        pygame.draw.circle(vignette, (0, 0, 0, 40), (WIDTH // 2, HEIGHT // 2), 420, 180)
        self.screen.blit(vignette, (0, 0))

    def draw_world(self):
        self.draw_background()

        arena_rect = pygame.Rect(-WORLD_PADDING, -WORLD_PADDING, WIDTH + WORLD_PADDING * 2, HEIGHT + WORLD_PADDING * 2)
        border_rect = pygame.Rect(
            arena_rect.x - self.camera.x,
            arena_rect.y - self.camera.y,
            arena_rect.width,
            arena_rect.height,
        )
        pygame.draw.rect(self.screen, (35, 45, 75), border_rect, 3, border_radius=18)

        for gem in self.gems:
            gem.draw(self.screen, self.camera)
        for coin in self.coins_pickups:
            coin.draw(self.screen, self.camera)
        for pickup in self.extra_life_pickups:
            pickup.draw(self.screen, self.camera)
        for bullet in self.enemy_bullets:
            bullet.draw(self.screen, self.camera)
        for bullet in self.bullets:
            bullet.draw(self.screen, self.camera)
        for enemy in self.enemies:
            enemy.draw(self.screen, self.camera)
        for particle in self.particles:
            particle.draw(self.screen, self.camera)
        self.player.draw(self.screen, self.camera)

        # Отрисовка удалённых игроков в режиме мультиплеера
        if self.multiplayer_mode != "single":
            self.draw_remote_players()

        for text in self.floating_texts:
            text.draw(self.screen, self.camera, self.font_small)

        if self.flash > 0:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((70, 110, 190, int(90 * self.flash)))
            self.screen.blit(overlay, (0, 0))

        if self.wave_cleared_flash > 0:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((80, 255, 210, int(75 * self.wave_cleared_flash)))
            self.screen.blit(overlay, (0, 0))

    def draw_remote_players(self):
        """Отрисовать удалённых игроков в режиме мультиплеера"""
        # Получение ID локального игрока (1 для хоста, или ID клиента)
        local_player_id = 1
        if self.multiplayer_mode == "client_connected" and self.network_client:
            local_player_id = self.network_client.player_id

        # Отладка: показываем какие удалённые игроки существуют
        if self.remote_players:
            print(f"[DEBUG] Drawing remote players: {list(self.remote_players.keys())}, local_id={local_player_id}")

        for player_id, p_state in self.remote_players.items():
            if player_id == local_player_id:
                # Пропускаем локального игрока (отрисован отдельно в draw_world)
                continue

            # Получаем скин для удалённого игрока
            skin = SKINS.get(p_state.skin, SKINS["classic"])

            # Вычисление позиции на экране
            pos = world_to_screen(pygame.Vector2(p_state.pos_x, p_state.pos_y), self.camera)
            print(f"[DEBUG] P{player_id} world: ({p_state.pos_x:.1f}, {p_state.pos_y:.1f}), screen: ({pos.x:.1f}, {pos.y:.1f})")

            # Отрисовка удалённого игрока с немного другим видом
            body_color = skin["invuln"] if p_state.invuln > 0 else skin["body"]

            # Эффект свечения
            glow_circle(self.screen, body_color, pos, 22, alpha=100)

            # Тело
            pygame.draw.circle(self.screen, body_color, (int(pos.x), int(pos.y)), 18)

            # Индикатор направления (пушка)
            facing = pygame.Vector2(p_state.facing_x, p_state.facing_y)
            gun_tip = pos + facing * 20
            pygame.draw.circle(self.screen, skin["core"], (int(gun_tip.x), int(gun_tip.y)), 7)

            # Отрисовка метки игрока сверху
            draw_text(self.screen, self.font_small, f"P{player_id}", CYAN, pos.x, pos.y - 35)

            # Полоса здоровья над игроком
            if p_state.health < p_state.max_health:
                health_ratio = p_state.health / p_state.max_health
                bar_width = 40
                bar_height = 4
                bar_x = pos.x - bar_width // 2
                bar_y = pos.y - 28
                pygame.draw.rect(self.screen, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height), border_radius=2)
                pygame.draw.rect(self.screen, GREEN, (bar_x, bar_y, int(bar_width * health_ratio), bar_height),
                                 border_radius=2)

    def draw_ui(self):
        health_ratio = self.player.health / self.player.max_health
        xp_ratio = self.player.xp / self.player.xp_goal

        pygame.draw.rect(self.screen, (25, 30, 44), (18, 18, 320, 28), border_radius=10)
        pygame.draw.rect(self.screen, (50, 205, 140), (18, 18, 320 * health_ratio, 28), border_radius=10)
        draw_text(self.screen, self.font_small, f"ОЗ {int(self.player.health)}/{self.player.max_health}", WHITE, 178,
                  32)

        pygame.draw.rect(self.screen, (25, 30, 44), (18, 54, 320, 18), border_radius=9)
        pygame.draw.rect(self.screen, CYAN, (18, 54, 320 * xp_ratio, 18), border_radius=9)
        draw_text(self.screen, self.font_small, f"УРОВЕНЬ {self.player.level}", WHITE, WIDTH - 18, 22,
                  anchor="topright")
        draw_text(self.screen, self.font_small, f"ВОЛНА {self.wave}", WHITE, WIDTH - 18, 48, anchor="topright")
        draw_text(self.screen, self.font_small, f"СЧЁТ {self.player.score}", WHITE, WIDTH - 18, 74, anchor="topright")
        draw_text(self.screen, self.font_small, f"МОНЕТЫ В ЗАБЕГЕ {self.run_coins}", GOLD, WIDTH - 18, 100,
                  anchor="topright")

        next_life_seconds = max(0, int(self.extra_life_timer))
        draw_text(
            self.screen,
            self.font_small,
            f"След. вторая жизнь: {next_life_seconds // 60:02d}:{next_life_seconds % 60:02d}",
            (170, 180, 210),
            WIDTH - 18,
            128,
            anchor="topright",
        )

        # Отображение обратного отсчёта босса
        if self.post_boss_timer > 0:
            draw_text(self.screen, self.font_small, "БОСС: ПОБЕЖДЁН", GREEN, WIDTH - 18, 158, anchor="topright")
        else:
            current_wave_mod = self.wave % 4
            is_boss_wave = current_wave_mod == 0

            if self.boss_alive:
                draw_text(self.screen, self.font_small, "БОСС: В БОЮ", RED, WIDTH - 18, 158, anchor="topright")
            elif is_boss_wave:
                seconds_until_boss = int(self.wave_duration - self.wave_timer)
                if seconds_until_boss > 0:
                    draw_text(self.screen, self.font_small, f"БОСС: {seconds_until_boss}с (сейчас волна)", RED,
                              WIDTH - 18, 158, anchor="topright")
                else:  # Не должно произойти если логика верна, но как запасной вариант
                    draw_text(self.screen, self.font_small, "БОСС: В БОЮ", RED, WIDTH - 18, 158, anchor="topright")
            else:
                # Не волна босса
                waves_until_boss = 4 - current_wave_mod
                total_seconds_until_boss = int(
                    (self.wave_duration - self.wave_timer) + (waves_until_boss - 1) * self.wave_duration)
                draw_text(self.screen, self.font_small, f"БОСС: {total_seconds_until_boss}с ({waves_until_boss} волны)",
                          ORANGE, WIDTH - 18, 158, anchor="topright")

        # Отображение дополнительных жизней
        draw_text(self.screen, self.font_small, f"ЖИЗНИ: {self.player.extra_lives}", YELLOW, WIDTH - 18, 182,
                  anchor="topright")

        # Всегда показываем хотя бы один индикатор щита
        shield_count = max(1, self.player.shield_max)
        for i in range(shield_count):
            color = CYAN if i < self.player.shield else (50, 70, 90)
            pygame.draw.circle(self.screen, color, (WIDTH - 28 - i * 24, 230), 8)

        dash_ready = self.player.dash_cooldown <= 0
        dash_color = BLUE if dash_ready else (90, 110, 150)
        pygame.draw.rect(self.screen, (25, 30, 44), (18, HEIGHT - 44, 180, 20), border_radius=8)
        cooldown_ratio = 1 - (self.player.dash_cooldown / self.player.dash_cd_max if self.player.dash_cd_max else 0)
        pygame.draw.rect(self.screen, dash_color, (18, HEIGHT - 44, 180 * clamp(cooldown_ratio, 0, 1), 20),
                         border_radius=8)
        draw_text(self.screen, self.font_small, "ПРОБЕЛ  РЫВОК", WHITE, 108, HEIGHT - 34)

        alive_bosses = [enemy for enemy in self.enemies if enemy.is_boss]
        if alive_bosses:
            for index, boss in enumerate(alive_bosses[:2]):
                ratio = boss.hp / boss.max_hp
                y = 20 + index * 34
                pygame.draw.rect(self.screen, (24, 28, 45), (WIDTH / 2 - 250, y, 500, 20), border_radius=10)
                pygame.draw.rect(self.screen, boss.color, (WIDTH / 2 - 250, y, 500 * ratio, 20), border_radius=10)
                draw_text(self.screen, self.font_small, boss.title.upper(), WHITE, WIDTH / 2, y + 34)

        draw_text(self.screen, self.font_small,
                  "WASD движение  |  ЛКМ стрельба  |  ПРОБЕЛ рывок  |  ESC пауза", (170, 180, 210), WIDTH / 2,
                  HEIGHT - 18)

        # Счётчик FPS
        fps_text = f"FPS: {int(self.clock.get_fps())}"
        draw_text(self.screen, self.font_small, fps_text, (150, 150, 150), WIDTH - 18, HEIGHT - 18,
                  anchor="bottomright")

        # Индикатор статуса сети (только в мультиплеере)
        if self.multiplayer_mode == "host":
            connected_players = len(self.network_host.clients) if self.network_host else 0
            net_text = f"HOST | Игроков: {connected_players + 1}"
            draw_text(self.screen, self.font_small, net_text, GREEN, 18, HEIGHT - 18, anchor="bottomleft")
        elif self.multiplayer_mode in ("client", "client_connected"):
            net_status = "Подключено" if self.network_client and self.network_client.connected else "Подключение..."
            net_color = GREEN if self.network_client and self.network_client.connected else YELLOW
            draw_text(self.screen, self.font_small, f"CLIENT | {net_status}", net_color, 18, HEIGHT - 18,
                      anchor="bottomleft")

        # Отрисовка меню читов если видимо - поверх всего, работает во всех режимах
        if self.cheat_manager and self.cheat_manager.cheat_menu.visible:
            self.cheat_manager.cheat_menu.draw(self.screen, self)

    def draw_player_preview(self, x, y, skin):
        pos = pygame.Vector2(x, y)
        glow_circle(self.screen, skin["body"], pos, 28, alpha=140)
        pygame.draw.circle(self.screen, skin["body"], (int(pos.x), int(pos.y)), 22)
        pygame.draw.circle(self.screen, skin["core"], (int(pos.x + 14), int(pos.y)), 8)

    def draw_accounts(self):
        """Отрисовать экран выбора аккаунта"""
        self.draw_background()
        self.account_buttons = []
        mouse_pos = pygame.mouse.get_pos()

        draw_text(self.screen, self.font_huge, "ВЫБЕРИ АККАУНТ", CYAN, WIDTH / 2, 60)

        # Область списка аккаунтов - подстроена чтобы вместить ввод снизу
        list_x = WIDTH / 2 - 280
        list_y = 130
        account_width = 560
        account_height = 60
        account_gap = 10
        max_visible = 5

        # Обновление анимации прокрутки
        self.account_scroll_offset += (self.account_scroll_target - self.account_scroll_offset) * 0.2
        start_idx = int(self.account_scroll_offset)

        visible_accounts = self.accounts[start_idx:start_idx + max_visible + 1]

        for i, account in enumerate(visible_accounts):
            y_pos = list_y + (i - (self.account_scroll_offset - start_idx)) * (account_height + account_gap)

            # Карточка аккаунта
            rect = pygame.Rect(list_x, y_pos, account_width, account_height)
            hovered = rect.collidepoint(mouse_pos)
            fill = (40, 52, 82) if hovered else (26, 34, 54)
            pygame.draw.rect(self.screen, fill, rect, border_radius=16)
            pygame.draw.rect(self.screen, CYAN if hovered else (60, 75, 110), rect, 3, border_radius=16)

            # Имя аккаунта
            draw_text(self.screen, self.font_ui, account["name"], WHITE, rect.centerx, rect.centery - 6)

            # Загрузка данных аккаунта для отображения
            acc_file = ACCOUNTS_DIR / f"{account['id']}.json"
            coins = 0
            if acc_file.exists():
                try:
                    data = json.loads(acc_file.read_text(encoding="utf-8"))
                    coins = data.get("coins", 0)
                except Exception:
                    pass
            draw_text(self.screen, self.font_small, f"Монет: {coins}", GOLD, rect.centerx, rect.centery + 16)

            # Кнопка удаления (маленький X справа) - ДОБАВЛЯЕМ ПЕРВОЙ чтобы проверялась перед карточкой аккаунта
            delete_rect = pygame.Rect(rect.right - 32, rect.top + 6, 24, 24)
            delete_hovered = delete_rect.collidepoint(mouse_pos)
            pygame.draw.circle(self.screen, RED if delete_hovered else (80, 60, 60), delete_rect.center, 12)
            draw_text(self.screen, self.font_small, "X", WHITE, delete_rect.centerx, delete_rect.centery)
            self.account_buttons.append((delete_rect, ("delete", account["id"])))

            # Карточка аккаунта - добавляем после кнопки удаления
            self.account_buttons.append((rect, ("select", account["id"])))

        # Индикаторы прокрутки
        list_bottom = list_y + max_visible * (account_height + account_gap) - account_gap
        if self.account_scroll_target > 0:
            draw_text(self.screen, self.font_ui, "▲", CYAN, WIDTH / 2, list_y - 20)
        if start_idx + max_visible < len(self.accounts):
            draw_text(self.screen, self.font_ui, "▼", CYAN, WIDTH / 2, list_bottom + 20)

        # Ввод нового аккаунта - фиксированная позиция снизу
        input_y = 530
        input_rect = pygame.Rect(WIDTH / 2 - 200, input_y, 400, 45)
        pygame.draw.rect(self.screen, (40, 50, 75) if self.editing_name else (30, 40, 60), input_rect, border_radius=12)
        pygame.draw.rect(self.screen, CYAN if self.editing_name else (60, 75, 100), input_rect, 2, border_radius=12)

        # Показать плейсхолдер или текст ввода
        if self.new_account_name:
            draw_text(self.screen, self.font_ui, self.new_account_name, WHITE, input_rect.centerx, input_rect.centery)
        else:
            draw_text(self.screen, self.font_small, "Введи имя нового аккаунта...", (120, 140, 170), input_rect.centerx,
                      input_rect.centery)

        self.account_buttons.append((input_rect, ("input", None)))

        # Кнопка создания
        create_rect = pygame.Rect(WIDTH / 2 - 100, input_y + 55, 200, 40)
        create_hovered = create_rect.collidepoint(mouse_pos)
        can_create = self.new_account_name.strip() and len(self.new_account_name) <= 20 and not any(
            acc["name"] == self.new_account_name.strip() for acc in self.accounts)
        create_color = GREEN if can_create else (80, 100, 80)
        fill = (40, 70, 50) if (create_hovered and can_create) else (26, 40, 30)
        pygame.draw.rect(self.screen, fill, create_rect, border_radius=12)
        pygame.draw.rect(self.screen, create_color, create_rect, 3, border_radius=12)
        draw_text(self.screen, self.font_ui, "СОЗДАТЬ", create_color, create_rect.centerx, create_rect.centery)
        self.account_buttons.append((create_rect, ("create", None)))

        # Инструкции
        draw_text(self.screen, self.font_small, "Кликни по аккаунту для входа | X для удаления", (150, 160, 190),
                  WIDTH / 2, HEIGHT - 35)
        draw_text(self.screen, self.font_small, f"v{VERSION}", (120, 130, 150), WIDTH - 12, HEIGHT - 12,
                  anchor="bottomright")

    def draw_menu(self):
        self.draw_background()
        self.menu_buttons = []
        draw_text(self.screen, self.font_huge, "НЕОНОВАЯ АРЕНА", CYAN, WIDTH / 2, HEIGHT / 2 - 120)
        draw_text(self.screen, self.font_big, "ПРОТОКОЛ ЗАТМЕНИЕ", WHITE, WIDTH / 2, HEIGHT / 2 - 46)
        draw_text(self.screen, self.font_ui, "Арена-шутер на pygame", (180, 195, 235), WIDTH / 2, HEIGHT / 2 + 24)
        draw_text(self.screen, self.font_small,
                  "Удерживай ЛКМ для стрельбы, уворачивайся рывком и переживи волны с боссами.", (170, 180, 210),
                  WIDTH / 2, HEIGHT / 2 + 66)
        draw_text(self.screen, self.font_ui, f"ОБЩИЕ МОНЕТЫ: {self.total_coins}", GOLD, WIDTH / 2, HEIGHT / 2 + 104)
        start_rect = pygame.Rect(WIDTH / 2 - 320, HEIGHT / 2 + 140, 190, 60)
        multi_rect = pygame.Rect(WIDTH / 2 - 95, HEIGHT / 2 + 140, 190, 60)
        shop_rect = pygame.Rect(WIDTH / 2 + 130, HEIGHT / 2 + 140, 190, 60)
        for rect, label, color, action in [
            (start_rect, "СТАРТ", YELLOW, "start"),
            (multi_rect, "СЕТЬ", PURPLE, "multiplayer"),
            (shop_rect, "МАГАЗИН", CYAN, "shop"),
        ]:
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            fill = (40, 52, 82) if hovered else (26, 34, 54)
            pygame.draw.rect(self.screen, fill, rect, border_radius=16)
            pygame.draw.rect(self.screen, color, rect, 3, border_radius=16)
            draw_text(self.screen, self.font_ui, label, color, rect.centerx, rect.centery)
            self.menu_buttons.append((rect, action))

        preview_x = WIDTH / 2
        preview_y = HEIGHT / 2 + 240
        self.draw_player_preview(preview_x, preview_y, self.selected_skin_data())
        draw_text(
            self.screen,
            self.font_small,
            f"Выбранный скин: {self.selected_skin_data()['name']}",
            WHITE,
            preview_x,
            preview_y + 46,
        )
        # Показать текущий аккаунт и подсказку переключения
        account_name = next((acc["name"] for acc in self.accounts if acc["id"] == self.current_account), "Аккаунт")
        draw_text(self.screen, self.font_small, f"Аккаунт: {account_name} | TAB для смены", (140, 150, 170), WIDTH / 2,
                  HEIGHT - 45)
        draw_text(self.screen, self.font_small, f"v{VERSION}", (120, 130, 150), WIDTH - 12, HEIGHT - 12,
                  anchor="bottomright")

    def draw_multiplayer_menu(self):
        """Отрисовка меню мультиплеера для создания/подключения к играм"""
        self.draw_background()
        self.multiplayer_menu_buttons = []
        mouse_pos = pygame.mouse.get_pos()

        draw_text(self.screen, self.font_huge, "СЕТЕВАЯ ИГРА", PURPLE, WIDTH / 2, 80)

        if not MULTIPLAYER_AVAILABLE:
            draw_text(self.screen, self.font_big, "Мультиплеер недоступен", RED, WIDTH / 2, HEIGHT / 2)
            draw_text(self.screen, self.font_small, "Проверь, что multiplayer.py в папке с игрой", (180, 195, 225),
                      WIDTH / 2, HEIGHT / 2 + 50)

            back_rect = pygame.Rect(WIDTH / 2 - 100, HEIGHT - 120, 200, 50)
            hovered = back_rect.collidepoint(mouse_pos)
            fill = (40, 52, 82) if hovered else (26, 34, 54)
            pygame.draw.rect(self.screen, fill, back_rect, border_radius=12)
            pygame.draw.rect(self.screen, CYAN, back_rect, 3, border_radius=12)
            draw_text(self.screen, self.font_ui, "НАЗАД", WHITE, back_rect.centerx, back_rect.centery)
            self.multiplayer_menu_buttons.append((back_rect, "back"))
            return

        # Кнопка создания игры
        host_rect = pygame.Rect(WIDTH / 2 - 220, 180, 200, 60)
        hovered = host_rect.collidepoint(mouse_pos)
        fill = (40, 52, 82) if hovered else (26, 34, 54)
        border = GREEN if self.multiplayer_mode == "host" else CYAN
        pygame.draw.rect(self.screen, fill, host_rect, border_radius=12)
        pygame.draw.rect(self.screen, border, host_rect, 3, border_radius=12)
        draw_text(self.screen, self.font_ui, "СОЗДАТЬ ИГРУ", GREEN, host_rect.centerx, host_rect.centery)
        self.multiplayer_menu_buttons.append((host_rect, "host"))

        # Кнопка подключения к игре
        join_rect = pygame.Rect(WIDTH / 2 + 20, 180, 200, 60)
        hovered = join_rect.collidepoint(mouse_pos)
        fill = (40, 52, 82) if hovered else (26, 34, 54)
        border = YELLOW if self.multiplayer_mode == "client" else CYAN
        pygame.draw.rect(self.screen, fill, join_rect, border_radius=12)
        pygame.draw.rect(self.screen, border, join_rect, 3, border_radius=12)
        draw_text(self.screen, self.font_ui, "ПОДКЛЮЧИТЬСЯ", YELLOW, join_rect.centerx, join_rect.centery)
        self.multiplayer_menu_buttons.append((join_rect, "join"))

        # Показать инфо хоста если создаём игру
        if self.multiplayer_mode == "host" and self.network_host:
            draw_text(self.screen, self.font_ui, "ИГРА СОЗДАНА!", GREEN, WIDTH / 2, 280)
            draw_text(self.screen, self.font_small, f"Ждём подключения на порту {DEFAULT_PORT}", WHITE, WIDTH / 2, 320)
            draw_text(self.screen, self.font_small, f"Подключено игроков: {len(self.network_host.clients) + 1}", CYAN,
                      WIDTH / 2, 350)

            # Кнопка старта когда кто-то подключается
            if len(self.network_host.clients) > 0:
                start_mp_rect = pygame.Rect(WIDTH / 2 - 100, 400, 200, 60)
                hovered = start_mp_rect.collidepoint(mouse_pos)
                fill = (40, 70, 50) if hovered else (26, 40, 30)
                pygame.draw.rect(self.screen, fill, start_mp_rect, border_radius=12)
                pygame.draw.rect(self.screen, GREEN, start_mp_rect, 3, border_radius=12)
                draw_text(self.screen, self.font_ui, "НАЧАТЬ", GREEN, start_mp_rect.centerx, start_mp_rect.centery)
                self.multiplayer_menu_buttons.append((start_mp_rect, "start_host"))

        # Показать интерфейс подключения если подключаемся
        elif self.multiplayer_mode == "client":
            draw_text(self.screen, self.font_ui, "ПОДКЛЮЧЕНИЕ", YELLOW, WIDTH / 2, 280)

            # Кнопка поиска
            discover_rect = pygame.Rect(WIDTH / 2 - 220, 320, 200, 50)
            hovered = discover_rect.collidepoint(mouse_pos)
            fill = (40, 52, 82) if hovered else (26, 34, 54)
            pygame.draw.rect(self.screen, fill, discover_rect, border_radius=12)
            pygame.draw.rect(self.screen, CYAN, discover_rect, 3, border_radius=12)
            draw_text(self.screen, self.font_ui, "НАЙТИ ИГРЫ", CYAN, discover_rect.centerx, discover_rect.centery)
            self.multiplayer_menu_buttons.append((discover_rect, "discover"))

            # Ручной ввод IP
            ip_rect = pygame.Rect(WIDTH / 2 + 20, 320, 200, 50)
            pygame.draw.rect(self.screen,
                             (40, 50, 75) if hasattr(self, 'editing_ip') and self.editing_ip else (30, 40, 60), ip_rect,
                             border_radius=12)
            pygame.draw.rect(self.screen, CYAN, ip_rect, 2, border_radius=12)
            ip_text = self.host_ip_input if self.host_ip_input else "Введи IP..."
            color = WHITE if self.host_ip_input else (120, 140, 170)
            draw_text(self.screen, self.font_small, ip_text, color, ip_rect.centerx, ip_rect.centery)
            self.multiplayer_menu_buttons.append((ip_rect, "ip_input"))

            # Показать найденные хосты
            y_pos = 400
            for host in self.available_hosts:
                host_rect = pygame.Rect(WIDTH / 2 - 150, y_pos, 300, 40)
                hovered = host_rect.collidepoint(mouse_pos)
                fill = (40, 52, 82) if hovered else (26, 34, 54)
                pygame.draw.rect(self.screen, fill, host_rect, border_radius=8)
                pygame.draw.rect(self.screen, GREEN, host_rect, 2, border_radius=8)
                draw_text(self.screen, self.font_small, f"{host['ip']} ({host['players']} игроков)", GREEN,
                          host_rect.centerx, host_rect.centery)
                self.multiplayer_menu_buttons.append((host_rect, ("connect", host['ip'])))
                y_pos += 50

            # Кнопка подключения для ручного IP
            if self.host_ip_input:
                connect_rect = pygame.Rect(WIDTH / 2 - 100, y_pos + 10, 200, 50)
                hovered = connect_rect.collidepoint(mouse_pos)
                fill = (40, 70, 50) if hovered else (26, 40, 30)
                pygame.draw.rect(self.screen, fill, connect_rect, border_radius=12)
                pygame.draw.rect(self.screen, GREEN, connect_rect, 3, border_radius=12)
                draw_text(self.screen, self.font_ui, "ПОДКЛЮЧИТЬСЯ", GREEN, connect_rect.centerx, connect_rect.centery)
                self.multiplayer_menu_buttons.append((connect_rect, ("connect_ip", self.host_ip_input)))

        # Кнопка назад
        back_rect = pygame.Rect(WIDTH / 2 - 100, HEIGHT - 80, 200, 50)
        hovered = back_rect.collidepoint(mouse_pos)
        fill = (40, 52, 82) if hovered else (26, 34, 54)
        pygame.draw.rect(self.screen, fill, back_rect, border_radius=12)
        pygame.draw.rect(self.screen, RED, back_rect, 3, border_radius=12)
        draw_text(self.screen, self.font_ui, "НАЗАД", RED, back_rect.centerx, back_rect.centery)
        self.multiplayer_menu_buttons.append((back_rect, "back"))

        # Инструкции
        if self.multiplayer_mode == "single":
            draw_text(self.screen, self.font_small, "Создай игру или подключись к другу по WiFi/LAN", (180, 195, 225),
                      WIDTH / 2, HEIGHT - 130)

    def draw_shop(self):
        self.draw_background()
        self.shop_buttons = []
        draw_text(self.screen, self.font_big, "МАГАЗИН", CYAN, WIDTH / 2, 56)
        draw_text(self.screen, self.font_ui, f"Баланс: {self.total_coins} монет", GOLD, WIDTH / 2, 106)
        draw_text(self.screen, self.font_small,
                  "Кликни по скину, чтобы купить или выбрать его. Кликни по усилению, чтобы купить новый уровень.",
                  (180, 195, 225), WIDTH / 2, 140)

        mouse_pos = pygame.mouse.get_pos()

        skin_width = 180
        skin_height = 180
        skin_gap = 16
        skin_total = len(SKINS) * skin_width + (len(SKINS) - 1) * skin_gap
        skin_start_x = WIDTH / 2 - skin_total / 2
        draw_text(self.screen, self.font_ui, "Скины", WHITE, WIDTH / 2, 190)
        # Показать только видимые скины с прокруткой
        max_visible = 6
        skin_keys = list(SKINS.keys())
        start_idx = int(self.shop_scroll_offset)
        end_idx = min(len(skin_keys), start_idx + max_visible)

        visible_count = end_idx - start_idx
        skin_total = visible_count * skin_width + (visible_count - 1) * skin_gap
        skin_start_x = WIDTH / 2 - skin_total / 2

        for i in range(start_idx, end_idx):
            skin_key = skin_keys[i]
            skin = SKINS[skin_key]
            rect = pygame.Rect(skin_start_x + (i - start_idx) * (skin_width + skin_gap), 220, skin_width, skin_height)
            hovered = rect.collidepoint(mouse_pos)
            fill = (32, 40, 62) if hovered else (22, 30, 48)
            border = skin["body"] if skin_key in self.progress["unlocked_skins"] else (90, 100, 125)
            pygame.draw.rect(self.screen, fill, rect, border_radius=18)
            pygame.draw.rect(self.screen, border, rect, 3, border_radius=18)
            self.draw_player_preview(rect.centerx, rect.y + 58, skin)
            draw_text(self.screen, self.font_small, skin["name"], WHITE, rect.centerx, rect.y + 106)

            if skin_key == self.progress["selected_skin"]:
                status = "Выбран"
                color = CYAN
            elif skin_key in self.progress["unlocked_skins"]:
                status = "Нажми, чтобы выбрать"
                color = GREEN
            else:
                status = f"Купить: {skin['cost']}"
                color = GOLD
            draw_text(self.screen, self.font_small, status, color, rect.centerx, rect.y + 142)
            self.shop_buttons.append((rect, ("skin", skin_key)))

        draw_text(self.screen, self.font_ui, "Стартовые усиления", WHITE, WIDTH / 2, 448)
        upgrade_width = 220
        upgrade_height = 150
        upgrade_gap = 18
        keys = list(SHOP_UPGRADES.keys())

        # Поддержка прокрутки для улучшений
        max_visible = 5
        start_idx = int(self.upgrade_scroll_offset)
        end_idx = min(len(keys), start_idx + max_visible)

        visible_keys = keys[start_idx:end_idx]
        total_width = len(visible_keys) * upgrade_width + (len(visible_keys) - 1) * upgrade_gap
        start_x = WIDTH / 2 - total_width / 2

        for index, key in enumerate(visible_keys):
            meta = SHOP_UPGRADES[key]
            rect = pygame.Rect(start_x + index * (upgrade_width + upgrade_gap), 478, upgrade_width, upgrade_height)
            hovered = rect.collidepoint(mouse_pos)
            fill = (34, 42, 66) if hovered else (24, 30, 50)
            pygame.draw.rect(self.screen, fill, rect, border_radius=18)
            pygame.draw.rect(self.screen, CYAN, rect, 2, border_radius=18)
            draw_text(self.screen, self.font_small, meta["name"], WHITE, rect.centerx, rect.y + 25)
            draw_wrapped_text(self.screen, self.font_small, meta["desc"], (180, 195, 225), rect.centerx, rect.y + 75,
                              upgrade_width - 30)
            level = self.progress["shop_levels"][key]
            max_level = len(meta["costs"])
            draw_text(self.screen, self.font_small, f"Уровень {level}/{max_level}", YELLOW, rect.centerx, rect.y + 95)
            if level < max_level:
                draw_text(self.screen, self.font_small, f"Цена: {meta['costs'][level]}", GOLD, rect.centerx,
                          rect.y + 120)
                self.shop_buttons.append((rect, ("upgrade", key)))  # Добавляем кнопку только если не макс уровень
            else:
                draw_text(self.screen, self.font_small, "Куплено максимум", GREEN, rect.centerx, rect.y + 120)
                # Не добавляем кнопку для улучшений максимального уровня

        draw_text(self.screen, self.font_small, "ESC - назад в меню", (180, 195, 225), WIDTH / 2, HEIGHT - 26)

    def draw_upgrade_screen(self):
        self.draw_world()
        self.draw_ui()
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 10, 18, 180))
        self.screen.blit(overlay, (0, 0))

        draw_text(self.screen, self.font_big, "НОВЫЙ УРОВЕНЬ", CYAN, WIDTH / 2, 100)
        draw_text(self.screen, self.font_ui, "Выбери одно усиление", WHITE, WIDTH / 2, 146)

        card_width = 290
        card_height = 200
        gap = 34
        total_width = len(self.upgrade_choices) * card_width + (len(self.upgrade_choices) - 1) * gap
        start_x = WIDTH / 2 - total_width / 2

        self.upgrade_rects = []
        mouse_pos = pygame.mouse.get_pos()
        for index, key in enumerate(self.upgrade_choices):
            x = start_x + index * (card_width + gap)
            rect = pygame.Rect(x, 220, card_width, card_height)
            hovered = rect.collidepoint(mouse_pos)
            color = (26, 34, 54) if not hovered else (36, 50, 80)
            border = CYAN if hovered else (75, 95, 145)
            pygame.draw.rect(self.screen, color, rect, border_radius=18)
            pygame.draw.rect(self.screen, border, rect, 3, border_radius=18)
            draw_text(self.screen, self.font_ui, UPGRADES[key]["name"], WHITE, rect.centerx, rect.y + 50)
            draw_text(self.screen, self.font_small, UPGRADES[key]["desc"], (180, 195, 225), rect.centerx, rect.y + 98)
            level_now = self.player.upgrade_counts[key]
            max_level = UPGRADES[key]["max"]
            draw_text(self.screen, self.font_small, f"Ранг {level_now}/{max_level}", YELLOW, rect.centerx,
                      rect.y + 138)
            draw_text(self.screen, self.font_small, f"Нажми {index + 1}", CYAN, rect.centerx, rect.y + 172)
            self.upgrade_rects.append((rect, key))

    def draw_game_over(self):
        self.draw_world()
        self.draw_ui()
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((12, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        draw_text(self.screen, self.font_big, "СИСТЕМА РАЗРУШЕНА", RED, WIDTH / 2, HEIGHT / 2 - 84)
        draw_text(self.screen, self.font_ui,
                  f"Волна {self.wave}  |  Счёт {self.player.score}  |  Уровень {self.player.level}", WHITE, WIDTH / 2,
                  HEIGHT / 2 - 18)
        draw_text(self.screen, self.font_small, f"За этот забег собрано монет: {self.run_coins}", GOLD, WIDTH / 2,
                  HEIGHT / 2 + 14)
        draw_text(self.screen, self.font_small, "R/ENTER - рестарт    M - меню    ESC - выход", (210, 200, 200),
                  WIDTH / 2, HEIGHT / 2 + 50)

    def draw_waiting_for_host(self):
        """Отрисовать экран ожидания для клиента ожидающего начала игры хостом"""
        self.draw_background()
        draw_text(self.screen, self.font_huge, "ОЖИДАНИЕ", CYAN, WIDTH / 2, HEIGHT / 2 - 100)
        draw_text(self.screen, self.font_big, "Хост запускает игру...", WHITE, WIDTH / 2, HEIGHT / 2)
        draw_text(self.screen, self.font_small, "ESC - отключиться", (180, 195, 225), WIDTH / 2, HEIGHT / 2 + 80)

    def draw_pause_menu(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))
        draw_text(self.screen, self.font_big, "ПАУЗА", WHITE, WIDTH / 2, HEIGHT / 2 - 80)

        self.pause_buttons = []
        button_width = 200
        button_height = 50
        spacing = 70
        start_y = HEIGHT / 2 - 20

        buttons = [
            ("Продолжить", YELLOW, "resume"),
            ("Заново", CYAN, "restart"),
            ("Выйти в меню", RED, "menu"),
        ]

        for i, (label, color, action) in enumerate(buttons):
            rect = pygame.Rect(WIDTH / 2 - button_width / 2, start_y + i * spacing, button_width, button_height)
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            fill = (40, 52, 82) if hovered else (26, 34, 54)
            pygame.draw.rect(self.screen, fill, rect, border_radius=12)
            pygame.draw.rect(self.screen, color, rect, 3, border_radius=12)
            draw_text(self.screen, self.font_ui, label, WHITE, rect.centerx, rect.centery)
            self.pause_buttons.append((rect, action))
        draw_text(self.screen, self.font_small, f"v{VERSION}", (120, 130, 150), WIDTH - 12, HEIGHT - 12,
                  anchor="bottomright")

    def handle_upgrade_input(self, event):
        if event.type == pygame.KEYDOWN:
            key_map = {
                pygame.K_1: 0,
                pygame.K_2: 1,
                pygame.K_3: 2,
            }
            if event.key in key_map:
                index = key_map[event.key]
                if index < len(self.upgrade_choices):
                    self.pick_upgrade(self.upgrade_choices[index])
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, key in getattr(self, "upgrade_rects", []):
                if rect.collidepoint(event.pos):
                    self.pick_upgrade(key)
                    break

    def pick_upgrade(self, key):
        success = self.player.apply_upgrade(key)
        if success:
            self.floating_texts.append(FloatingText(self.player.pos.copy(), UPGRADES[key]["name"], CYAN, 1.2))
            self.state = "playing"
        else:
            # Если по какой-то причине выбрано максимальное улучшение, убираем его и остаёмся в меню улучшений
            self.upgrade_choices = [c for c in self.upgrade_choices if c != key]
            if not self.upgrade_choices:
                self.state = "playing"
                # Даём утешительный приз если улучшений не осталось
                self.player.health = min(self.player.max_health, self.player.health + 25)
                self.add_coins(50)
                self.floating_texts.append(FloatingText(self.player.pos.copy(), "+25 ОЗ, +50 МОНЕТ", GOLD, 1.5))

    def open_shop(self):
        self.state = "shop"
        self.shop_scroll_offset = 0
        self.shop_scroll_target = 0
        self.upgrade_scroll_offset = 0
        self.upgrade_scroll_target = 0

    def start_run(self):
        self.new_game()
        self.state = "playing"

    def activate_menu_action(self, action):
        if action == "start":
            self.multiplayer_mode = "single"
            self.start_run()
        elif action == "shop":
            self.open_shop()
        elif action == "multiplayer":
            self.state = "multiplayer_menu"
            self.multiplayer_mode = "single"
            self.host_ip_input = ""
            self.available_hosts = []

    def handle_shop_action(self, action):
        kind, key = action
        if kind == "skin":
            if key in self.progress["unlocked_skins"]:
                self.progress["selected_skin"] = key
                self.save_progress()
                return
            cost = SKINS[key]["cost"]
            if self.spend_coins(cost):
                self.progress["unlocked_skins"].append(key)
                self.progress["selected_skin"] = key
                self.save_progress()
        elif kind == "upgrade":
            level = self.progress["shop_levels"][key]
            costs = SHOP_UPGRADES[key]["costs"]
            if level >= len(costs):
                return
            price = costs[level]
            if self.spend_coins(price):
                self.progress["shop_levels"][key] += 1
                self.save_progress()

    def handle_multiplayer_action(self, action):
        """Обработать действия меню мультиплеера"""
        if not MULTIPLAYER_AVAILABLE:
            if action == "back":
                self.state = "menu"
            return

        if action == "back":
            # Очистка любого сетевого состояния
            if self.network_host:
                self.network_host.stop()
                self.network_host = None
            if self.network_client:
                self.network_client.disconnect()
                self.network_client = None
            self.multiplayer_mode = "single"
            self.state = "menu"

        elif action == "host":
            if GameHost is None:
                return
            self.multiplayer_mode = "host"
            self.network_host = GameHost()
            self.network_host.start()

        elif action == "join":
            if GameClient is None:
                return
            self.multiplayer_mode = "client"
            self.network_client = GameClient()

        elif action == "discover":
            if self.network_client and not self.discovering_hosts:
                self.discovering_hosts = True
                self.available_hosts = self.network_client.discover_hosts(timeout=2.0)
                self.discovering_hosts = False

        elif action == "ip_input":
            self.editing_ip = True

        elif isinstance(action, tuple):
            action_type, data = action
            if action_type == "connect":
                # Подключение к найденному хосту
                if self.network_client:
                    if self.network_client.connect(data):
                        self.multiplayer_mode = "client_connected"
                        self.state = "waiting_for_host"  # Ждём пока хост начнёт
            elif action_type == "connect_ip":
                # Подключение к ручному IP
                if self.network_client:
                    if self.network_client.connect(data):
                        self.multiplayer_mode = "client_connected"
                        self.state = "waiting_for_host"  # Ждём пока хост начнёт игру

        elif action == "start_host":
            # Начать игру как хост с подключёнными игроками
            # Уведомить всех клиентов что игра начинается
            if self.network_host:
                self.network_host.broadcast_game_start()
            self.start_multiplayer_game()

    def start_multiplayer_game(self):
        """Начать сессию многопользовательской игры"""
        self.new_game()
        if self.multiplayer_mode == "host":
            # Хост управляет игроком 1, удалённые игроки симулируются
            self._client_shoot_timers = {}  # Отслеживание кулдаунов стрельбы для удалённых игроков
        elif self.multiplayer_mode in ("client", "client_connected"):
            # Клиент получает свой ID игрока от сервера
            if self.network_client and self.network_client.player_id:
                # Клиент не игрок 1
                pass
        self.state = "playing"

    def _send_host_state(self):
        """Хост: сериализовать и отправить состояние игры всем клиентам"""
        if not self.network_host:
            return

        # Создать состояние игрока для локального игрока (игрок 1)
        p1_state = PlayerState(
            player_id=1,
            pos_x=self.player.pos.x,
            pos_y=self.player.pos.y,
            vel_x=self.player.vel.x,
            vel_y=self.player.vel.y,
            facing_x=self.player.facing.x,
            facing_y=self.player.facing.y,
            health=self.player.health,
            max_health=self.player.max_health,
            level=self.player.level,
            xp=self.player.xp,
            xp_goal=self.player.xp_goal,
            shield=self.player.shield,
            shield_max=self.player.shield_max,
            extra_lives=self.player.extra_lives,
            skin=self.progress["selected_skin"],
            invuln=self.player.invuln
        )

        # Собрать список всех игроков включая удалённых
        all_players = [p1_state]

        # Добавить состояния удалённых игроков
        for player_id, p_state in self.remote_players.items():
            if player_id != 1:  # Пропускаем P1 так как уже добавили
                all_players.append(p_state)

        # Сериализовать врагов для клиентов
        enemy_data = []
        for enemy in self.enemies:
            if not enemy.dead:
                enemy_data.append({
                    'type': enemy.kind,
                    'pos_x': enemy.pos.x,
                    'pos_y': enemy.pos.y,
                    'hp': enemy.hp,
                    'max_hp': enemy.max_hp
                })

        # Сериализовать пули (пока только пули игрока)
        bullet_data = []
        for bullet in self.bullets:
            if not bullet.dead and bullet.friendly:
                bullet_data.append({
                    'pos_x': bullet.pos.x,
                    'pos_y': bullet.pos.y,
                    'vel_x': bullet.vel.x,
                    'vel_y': bullet.vel.y,
                    'radius': bullet.radius,
                    'damage': bullet.damage,
                    'color': bullet.color
                })

        gem_data = [{
            'pos_x': gem.pos.x,
            'pos_y': gem.pos.y,
            'vel_x': gem.vel.x,
            'vel_y': gem.vel.y,
            'value': gem.value,
            'radius': gem.radius
        } for gem in self.gems]

        coin_data = [{
            'pos_x': coin.pos.x,
            'pos_y': coin.pos.y,
            'vel_x': coin.vel.x,
            'vel_y': coin.vel.y,
            'amount': coin.amount,
            'radius': coin.radius,
            'pulse': coin.pulse
        } for coin in self.coins_pickups]

        floating_text_data = [{
            'pos_x': text.pos.x,
            'pos_y': text.pos.y,
            'text': text.text,
            'color': list(text.color),
            'life': text.life
        } for text in self.floating_texts]

        # Собрать состояние игры с полными данными мира
        game_state = GameState(
            timestamp=time.time(),
            wave=self.wave,
            wave_timer=self.wave_timer,
            boss_alive=self.boss_alive,
            players=all_players,
            enemies=enemy_data,
            bullets=bullet_data,
            gems=gem_data,
            coins=coin_data,
            particles=[],
            floating_texts=floating_text_data
        )
        self.network_host.broadcast_state(game_state)

    def _process_client_inputs(self, dt):
        """Хост: обработать ввод от подключённых клиентов и обновить их позиции"""
        if not self.network_host:
            return

        # Получить все вводы клиентов
        client_inputs = self.network_host.get_all_client_inputs()

        # Отладка: показать вводы клиентов
        if client_inputs:
            print(f"[DEBUG] Host received inputs from: {list(client_inputs.keys())}")
            for pid, inp in client_inputs.items():
                print(
                    f"[DEBUG] P{pid}: move=({inp.move_x:.1f}, {inp.move_y:.1f}), facing=({inp.facing_x:.2f}, {inp.facing_y:.2f})")

        # Убедиться что словарь таймеров стрельбы существует
        if not hasattr(self, '_client_shoot_timers'):
            self._client_shoot_timers = {}

        for player_id, input_data in client_inputs.items():
            # Получить или создать состояние игрока для этого клиента
            if player_id not in self.remote_players:
                # Создать новое состояние игрока для этого клиента
                from multiplayer import PlayerState
                self.remote_players[player_id] = PlayerState(
                    player_id=player_id,
                    pos_x=WIDTH / 2 + 100,
                    pos_y=HEIGHT / 2,
                    vel_x=0,
                    vel_y=0,
                    facing_x=1,
                    facing_y=0,
                    health=100,
                    max_health=100,
                    level=1,
                    xp=0,
                    xp_goal=35,
                    shield=0,
                    shield_max=0,
                    extra_lives=0,
                    skin="classic",
                    invuln=0,
                    dash_timer=0.0,
                    dash_cooldown=0.0
                )
                # Инициализировать таймер стрельбы для нового игрока
                self._client_shoot_timers[player_id] = 0

            p_state = self.remote_players[player_id]

            # Обновить таймеры рывка
            if hasattr(p_state, 'dash_timer'):
                p_state.dash_timer = max(0.0, p_state.dash_timer - dt)
            if hasattr(p_state, 'dash_cooldown'):
                p_state.dash_cooldown = max(0.0, p_state.dash_cooldown - dt)
            if hasattr(p_state, 'invuln'):
                p_state.invuln = max(0.0, p_state.invuln - dt)

            # Применить движение на основе ввода
            speed = 310  # Базовая скорость
            move = pygame.Vector2(input_data.move_x, input_data.move_y)
            if move.length_squared() > 0:
                move = move.normalize()

            # Обработать ввод рывка
            if input_data.dashing and p_state.dash_cooldown <= 0:
                dash_dir = move if move.length_squared() > 0 else pygame.Vector2(p_state.facing_x, p_state.facing_y)
                if dash_dir.length_squared() > 0:
                    dash_dir = dash_dir.normalize()
                    p_state.vel_x = dash_dir.x * 780  # сила рывка как у P1
                    p_state.vel_y = dash_dir.y * 780
                    p_state.dash_timer = 0.16
                    p_state.dash_cooldown = 3.6  # базовый кулдаун рывка

            # Обновить позицию (рывок использует скорость, обычное движение использует move * speed)
            if p_state.dash_timer > 0:
                # Во время рывка использовать существующую скорость
                p_state.pos_x += p_state.vel_x * dt
                p_state.pos_y += p_state.vel_y * dt
            else:
                # Обычное движение
                p_state.vel_x = move.x * speed
                p_state.vel_y = move.y * speed
                p_state.pos_x += p_state.vel_x * dt
                p_state.pos_y += p_state.vel_y * dt

            # Ограничить границами мира
            p_state.pos_x = max(-WORLD_PADDING, min(WIDTH + WORLD_PADDING, p_state.pos_x))
            p_state.pos_y = max(-WORLD_PADDING, min(HEIGHT + WORLD_PADDING, p_state.pos_y))

            # Отладка: показать обновлённую позицию
            print(f"[DEBUG] P{player_id} position: ({p_state.pos_x:.1f}, {p_state.pos_y:.1f})")

            # Обновить направление взгляда из ввода клиента (клиент вычисляет это правильно со своей камерой)
            if hasattr(input_data, 'facing_x') and hasattr(input_data, 'facing_y'):
                # Использовать вычисленное клиентом направление
                p_state.facing_x = input_data.facing_x
                p_state.facing_y = input_data.facing_y
            elif input_data.aim_x != 0 or input_data.aim_y != 0:
                # Запасной вариант: вычислить из позиции прицела
                aim = pygame.Vector2(input_data.aim_x - p_state.pos_x, input_data.aim_y - p_state.pos_y)
                if aim.length_squared() > 0:
                    aim = aim.normalize()
                    p_state.facing_x = aim.x
                    p_state.facing_y = aim.y

            # Обработать стрельбу из ввода клиента
            if input_data.shooting:
                if self._client_shoot_timers.get(player_id, 0) <= 0:
                    # Создать пулю для удалённого игрока в центре позиции (как у P1)
                    pos = pygame.Vector2(p_state.pos_x, p_state.pos_y)
                    facing = pygame.Vector2(p_state.facing_x, p_state.facing_y)
                    if facing.length_squared() > 0:
                        facing = facing.normalize()
                    bullet_vel = facing * 750
                    bullet = Bullet(pos.copy(), bullet_vel, 5, 12, CYAN)
                    self.bullets.append(bullet)
                    self._client_shoot_timers[player_id] = 0.24  # Кулдаун скорострельности (как базовый у P1)

        # Обновить таймеры стрельбы для всех игроков
        for pid in list(self._client_shoot_timers.keys()):
            self._client_shoot_timers[pid] -= dt
            if self._client_shoot_timers[pid] < 0:
                self._client_shoot_timers[pid] = 0

        # Обработать столкновения врагов с удалёнными игроками (только хост)
        for enemy in self.enemies:
            for p_state in self.remote_players.values():
                if p_state.invuln > 0:
                    continue
                p_pos = pygame.Vector2(p_state.pos_x, p_state.pos_y)
                if enemy.pos.distance_to(p_pos) <= enemy.radius + 24:
                    # Удалённый игрок получает урон от контакта с врагом
                    p_state.health -= enemy.damage * dt  # Урон со временем
                    p_state.invuln = max(p_state.invuln, 0.08)
                    if p_state.health <= 0:
                        if p_state.extra_lives > 0:
                            p_state.extra_lives -= 1
                            p_state.health = p_state.max_health
                            p_state.invuln = 2.2
                        else:
                            p_state.health = 0

    def _send_client_input(self):
        """Клиент: отправить локальный ввод хосту"""
        if not self.network_client or not self.network_client.connected:
            return

        # Получить актуальный player_id от сетевого клиента (может быть 2 для P2)
        player_id = getattr(self.network_client, 'player_id', 1)

        # Захватить локальный ввод с позицией игрока для точного направления
        if LocalPlayerInput is None:
            return
        player_input = LocalPlayerInput.capture(player_id, self.camera, self.player.pos)
        self.network_client.send_input(player_input)

    def _receive_client_state(self):
        """Клиент: получить и применить состояние игры от хоста"""
        if not self.network_client:
            return
        state = self.network_client.get_latest_state()
        if state:
            self.remote_players = {p.player_id: p for p in state.players}
            # Обновить локального игрока из состояния сервера если есть
            for p_state in state.players:
                if p_state.player_id == self.network_client.player_id:
                    previous_level = self.player.level
                    # Держать трансформ клиента синхронизированным с авторитетным состоянием хоста.
                    self.player.pos.x = p_state.pos_x
                    self.player.pos.y = p_state.pos_y
                    self.player.vel.x = p_state.vel_x
                    self.player.vel.y = p_state.vel_y
                    self.player.facing.x = p_state.facing_x
                    self.player.facing.y = p_state.facing_y
                    # Статы здоровья тоже авторитетны на хосте.
                    self.player.health = p_state.health
                    self.player.max_health = p_state.max_health
                    self.player.level = p_state.level
                    self.player.xp = p_state.xp
                    self.player.xp_goal = p_state.xp_goal
                    self.player.shield = p_state.shield
                    self.player.shield_max = p_state.shield_max
                    self.player.extra_lives = p_state.extra_lives
                    self.player.invuln = p_state.invuln
                    if p_state.level > previous_level:
                        self.pending_levels += p_state.level - previous_level
                    break

            # Синхронизировать состояние мира от хоста
            self.wave = state.wave
            self.wave_timer = state.wave_timer
            self.boss_alive = state.boss_alive

            # Синхронизировать врагов (заменить клиентских врагов состоянием хоста)
            if state.enemies:
                self.enemies = []
                for e_data in state.enemies:
                    enemy = Enemy(e_data['type'], pygame.Vector2(e_data['pos_x'], e_data['pos_y']), self.wave)
                    enemy.hp = e_data['hp']
                    enemy.max_hp = e_data['max_hp']
                    self.enemies.append(enemy)

            # Синхронизировать пули (очистить и пересоздать от хоста)
            if state.bullets:
                self.bullets = []
                for b_data in state.bullets:
                    pos = pygame.Vector2(b_data['pos_x'], b_data['pos_y'])
                    vel = pygame.Vector2(b_data['vel_x'], b_data['vel_y'])
                    bullet = Bullet(pos, vel, b_data['radius'], b_data['damage'], tuple(b_data['color']))
                    self.bullets.append(bullet)
            else:
                self.bullets = []

            # Синхронизировать подбираемые предметы от хоста
            self.gems = []
            for g_data in state.gems:
                gem = Gem(
                    pygame.Vector2(g_data['pos_x'], g_data['pos_y']),
                    int(g_data.get('value', 1)),
                    pygame.Vector2(g_data.get('vel_x', 0), g_data.get('vel_y', 0)),
                    int(g_data.get('radius', 7))
                )
                self.gems.append(gem)

            self.coins_pickups = []
            for c_data in state.coins:
                coin = CoinPickup(
                    pygame.Vector2(c_data['pos_x'], c_data['pos_y']),
                    int(c_data.get('amount', 1)),
                    pygame.Vector2(c_data.get('vel_x', 0), c_data.get('vel_y', 0)),
                    int(c_data.get('radius', 8)),
                    float(c_data.get('pulse', 0.0))
                )
                self.coins_pickups.append(coin)

            # Синхронизировать летающие тексты боя/интерфейса от хоста (напр. иммунитет/фаза/итд)
            self.floating_texts = []
            for t_data in getattr(state, 'floating_texts', []):
                self.floating_texts.append(FloatingText(
                    pygame.Vector2(t_data.get('pos_x', 0), t_data.get('pos_y', 0)),
                    t_data.get('text', ''),
                    tuple(t_data.get('color', CYAN)),
                    float(t_data.get('life', 0.9))
                ))

    def update_multiplayer(self, dt):
        """Обновить сетевое взаимодействие мультиплеера"""
        if self.multiplayer_mode == "host" and self.network_host:
            pass
        elif self.multiplayer_mode in ("client", "client_connected") and self.network_client:
            state = self.network_client.get_latest_state()
            if state:
                self.remote_players = {p.player_id: p for p in state.players}

    def run(self):
        while self.running:
            dt = min(0.033, self.clock.tick(FPS) / 1000)
            self.handle_events()

            # Обновить анимации прокрутки
            self.shop_scroll_offset += (self.shop_scroll_target - self.shop_scroll_offset) * 0.2
            self.upgrade_scroll_offset += (self.upgrade_scroll_target - self.upgrade_scroll_offset) * 0.2

            if self.state == "playing" or (self.state == "upgrade" and self.multiplayer_mode != "single"):
                self.update_playing(dt)

            if self.state == "accounts":
                self.draw_accounts()
            elif self.state == "menu":
                self.draw_menu()
            elif self.state == "multiplayer_menu":
                self.draw_multiplayer_menu()
            elif self.state == "shop":
                self.draw_shop()
            elif self.state == "playing":
                self.draw_world()
                self.draw_ui()
            elif self.state == "upgrade":
                self.draw_upgrade_screen()
            elif self.state == "paused":
                self.draw_world()
                self.draw_ui()
                self.draw_pause_menu()
            elif self.state == "game_over":
                self.draw_game_over()
            elif self.state == "waiting_for_host":
                # Проверить начал ли хост игру
                if self.network_client and self.network_client.is_game_started():
                    self.start_multiplayer_game()
                else:
                    self.draw_waiting_for_host()

            pygame.display.flip()

        # Автосохранение перед выходом
        self.save_progress()
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.save_progress()
                self.running = False
                continue
            elif event.type == pygame.KEYDOWN and (
                event.key == pygame.K_F11
                or (event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT))
                or (event.key == pygame.K_KP_ENTER and (event.mod & pygame.KMOD_ALT))
            ):
                # Обработать горячие клавиши полноэкранного режима перед читами
                self.toggle_fullscreen()
                continue

            # Обработать ввод читов после глобальных/системных горячих клавиш
            if self.cheat_manager and self.cheat_manager.handle_input(self, event):
                continue
            elif self.state == "accounts":
                self.handle_accounts_input(event)
            elif self.state == "menu":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self.start_run()
                    elif event.key == pygame.K_s:
                        self.open_shop()
                    elif event.key == pygame.K_TAB:
                        # Переключить аккаунт
                        self.state = "accounts"
                        self.current_account = None
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, action in self.menu_buttons:
                        if rect.collidepoint(event.pos):
                            self.activate_menu_action(action)
                            break
            elif self.state == "multiplayer_menu":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.handle_multiplayer_action("back")
                    elif hasattr(self, 'editing_ip') and self.editing_ip:
                        if event.key == pygame.K_RETURN:
                            self.editing_ip = False
                        elif event.key == pygame.K_BACKSPACE:
                            self.host_ip_input = self.host_ip_input[:-1]
                        else:
                            char = event.unicode
                            if char.isprintable() and len(self.host_ip_input) < 15:
                                self.host_ip_input += char
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, action in self.multiplayer_menu_buttons:
                        if rect.collidepoint(event.pos):
                            self.handle_multiplayer_action(action)
                            break
            elif self.state == "shop":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Левый клик
                        for rect, action in self.shop_buttons:
                            if rect.collidepoint(event.pos):
                                self.handle_shop_action(action)
                                break
                    elif event.button == 4:  # Колесо мыши вверх
                        # Проверить позицию мыши для определения зоны прокрутки
                        mouse_y = event.pos[1]
                        if mouse_y < 420:  # Зона скинов
                            self.shop_scroll_target = max(0, self.shop_scroll_target - 1)
                        else:  # Зона улучшений
                            self.upgrade_scroll_target = max(0, self.upgrade_scroll_target - 1)
                    elif event.button == 5:  # Колесо мыши вниз
                        mouse_y = event.pos[1]
                        if mouse_y < 420:  # Зона скинов
                            self.shop_scroll_target = min(max(0, len(SKINS) - 6), self.shop_scroll_target + 1)
                        else:  # Зона улучшений
                            max_upgrades = max(0, len(SHOP_UPGRADES) - 5)
                            self.upgrade_scroll_target = min(max_upgrades, self.upgrade_scroll_target + 1)
            elif self.state == "playing":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = "paused"
            elif self.state == "paused":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = "playing"
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for rect, action in self.pause_buttons:
                        if rect.collidepoint(event.pos):
                            if action == "resume":
                                self.state = "playing"
                            elif action == "restart":
                                self.start_run()
                            elif action == "menu":
                                self.state = "menu"
                            break
            elif self.state == "upgrade":
                self.handle_upgrade_input(event)
            elif self.state == "game_over":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_r):
                        self.start_run()
                    elif event.key == pygame.K_m:
                        self.state = "menu"
                    elif event.key == pygame.K_ESCAPE:
                        self.running = False
            elif self.state == "waiting_for_host":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Отключиться и вернуться в меню
                        if self.network_client:
                            self.network_client.disconnect()
                            self.network_client = None
                        self.multiplayer_mode = "single"
                        self.state = "menu"

    def handle_accounts_input(self, event):
        """Обработать ввод для экрана выбора аккаунта"""
        if event.type == pygame.KEYDOWN:
            if self.editing_name:
                if event.key == pygame.K_RETURN:
                    # Попробовать создать аккаунт
                    if self.new_account_name.strip():
                        if self.create_account(self.new_account_name):
                            self.new_account_name = ""
                            self.editing_name = False
                elif event.key == pygame.K_ESCAPE:
                    self.editing_name = False
                    self.new_account_name = ""
                elif event.key == pygame.K_BACKSPACE:
                    self.new_account_name = self.new_account_name[:-1]
                else:
                    # Добавить символ если валиден и под лимитом
                    char = event.unicode
                    if char.isprintable() and len(self.new_account_name) < 20:
                        self.new_account_name += char
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Левый клик
                for rect, (action_type, action_data) in self.account_buttons:
                    if rect.collidepoint(event.pos):
                        if action_type == "select":
                            self.select_account(action_data)
                        elif action_type == "delete":
                            # Удалить аккаунт
                            self.delete_account(action_data)
                            # Если аккаунтов не осталось, создать стандартный
                            if not self.accounts:
                                self.create_account("Игрок 1")
                        elif action_type == "input":
                            self.editing_name = True
                        elif action_type == "create":
                            if self.new_account_name.strip():
                                if self.create_account(self.new_account_name):
                                    self.new_account_name = ""
                                    self.editing_name = False
                        break
            elif event.button == 4:  # Колесо мыши вверх
                self.account_scroll_target = max(0, self.account_scroll_target - 1)
            elif event.button == 5:  # Колесо мыши вниз
                max_scroll = max(0, len(self.accounts) - 6)
                self.account_scroll_target = min(max_scroll, self.account_scroll_target + 1)


if __name__ == "__main__":
    # Попробовать загрузить читы
    try:
        from cheats.main_cheat import CheatManager

        CHEATS_AVAILABLE = True
        print("[DEBUG] Читы загружены успешно!")
    except ImportError as e:
        CheatManager = None
        CHEATS_AVAILABLE = False
        print(f"[DEBUG] Читы НЕ загружены: {e}")

    game = Game()
    # Добавить менеджер читов если доступен
    if CHEATS_AVAILABLE:
        game.cheat_manager = CheatManager()
    else:
        game.cheat_manager = None

    game.run()