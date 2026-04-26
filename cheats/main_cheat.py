"""
СИСТЕМА ЧИТОВ для Neon Arena: Eclipse Protocol
Нажмите INSERT для открытия/закрытия меню читов
"""

import pygame
import random
from pathlib import Path

from main import VERSION

class CheatMenuUI:
    """Визуальное меню читов с кликабельными кнопками"""

    def __init__(self):
        self.visible = False
        self.font_title = None
        self.font_button = None
        self.font_desc = None
        self.initialized = False

        # Переключаемые читы (вкл/выкл)
        self.toggle_cheats = {
            "god_noclip": {"name": "GOD + NOCLIP", "desc": "Бессмертие + сквозь врагов", "active": False, "color": (255, 50, 50)},
            "one_hit": {"name": "ONE HIT KILL", "desc": "Убивает с одного выстрела", "active": False, "color": (255, 100, 50)},
            "infinite_xp": {"name": "INFINITE XP", "desc": "Постоянный прирост опыта", "active": False, "color": (50, 150, 255)},
            "speed": {"name": "SPEED HACK", "desc": "500 скорость, мгновенный рывок", "active": False, "color": (50, 255, 150)},
            "rapid_fire": {"name": "RAPID FIRE", "desc": "Мгновенная стрельба", "active": False, "color": (255, 200, 50)},
            "no_shake": {"name": "NO VIBRATION", "desc": "Отключить тряску экрана", "active": False, "color": (100, 255, 200)},
            "p2_god": {"name": "P2 GOD MODE", "desc": "Бессмертие для P2 (MP)", "active": False, "color": (100, 255, 255)},
        }

        # Кнопки действий (одноразовые)
        self.action_buttons = [
            {"name": "MAX UPGRADES", "action": "max_upgrades", "color": (150, 100, 255)},
            {"name": "SPAWN BOSS", "action": "spawn_boss", "color": (200, 50, 200)},
            {"name": "KILL ALL", "action": "kill_all", "color": (255, 50, 100)},
            {"name": "SKIP WAVE", "action": "skip_wave", "color": (100, 200, 255)},
            {"name": "+5000 COINS", "action": "add_coins", "color": (255, 215, 0)},
            {"name": "FULL HEAL", "action": "full_heal", "color": (50, 255, 100)},
            {"name": "ALL SKINS", "action": "unlock_all_skins", "color": (255, 100, 255)},
            {"name": "MAX SHOP", "action": "max_shop", "color": (100, 255, 150)},
            {"name": "DISABLE ALL", "action": "disable_all", "color": (150, 150, 150)},
        ]

    def init_fonts(self):
        if not self.initialized:
            self.font_title = pygame.font.SysFont("segoeui", 28, bold=True)
            self.font_button = pygame.font.SysFont("segoeui", 18, bold=True)
            self.font_action = pygame.font.SysFont("segoeui", 13, bold=True)
            self.font_desc = pygame.font.SysFont("segoeui", 14)
            self.initialized = True

    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            self.init_fonts()
        return self.visible

    def handle_click(self, mouse_pos, game, cheat_mgr):
        if not self.visible:
            return False

        width, height = 420, 610
        x = (game.screen.get_width() - width) // 2
        y = (game.screen.get_height() - height) // 2

        # Проверка кнопок переключаемых читов
        btn_w, btn_h = 360, 45
        start_y = y + 60
        gap = 8

        for i, (key, cheat) in enumerate(self.toggle_cheats.items()):
            rect = pygame.Rect(x + 20, start_y + i * (btn_h + gap), btn_w, btn_h)
            if rect.collidepoint(mouse_pos):
                cheat["active"] = not cheat["active"]
                # Обновление менеджера читов
                if key == "god_noclip":
                    cheat_mgr.god_mode_active = cheat["active"]
                    cheat_mgr.noclip_active = cheat["active"]
                    if cheat["active"]:
                        game.player.health = game.player.max_health
                        game.player.shield = 999
                    else:
                        # Сброс при отключении
                        game.player.invuln = 0.0
                        game.player.shield = min(game.player.shield, game.player.shield_max)
                elif key == "one_hit":
                    cheat_mgr.one_hit_kill_active = cheat["active"]
                elif key == "infinite_xp":
                    cheat_mgr.infinite_xp_active = cheat["active"]
                elif key == "speed":
                    cheat_mgr.speed_hack_active = cheat["active"]
                    if not cheat["active"]:
                        # Сброс скорости при отключении
                        game.player.base_speed = 310
                elif key == "rapid_fire":
                    cheat_mgr.rapid_fire_active = cheat["active"]
                    if not cheat["active"]:
                        # Сброс таймера стрельбы при отключении
                        game.player.shoot_timer = 0.0
                elif key == "no_shake":
                    cheat_mgr.no_shake_active = cheat["active"]
                    if cheat["active"]:
                        game.shake = 0.0  # Очистить текущую тряску
                elif key == "p2_god":
                    cheat_mgr.p2_god_active = cheat["active"]
                return True

        # Проверка кнопок действий - 3 колонки
        action_start_y = start_y + len(self.toggle_cheats) * (btn_h + gap) + 15
        action_btn_h = 32
        action_btn_w = 120
        action_gap = 8

        for i, btn in enumerate(self.action_buttons):
            row = i // 3
            col = i % 3
            rect = pygame.Rect(x + 15 + col * (action_btn_w + action_gap), action_start_y + row * (action_btn_h + action_gap), action_btn_w, action_btn_h)
            if rect.collidepoint(mouse_pos):
                self.execute_action(btn["action"], game, cheat_mgr)
                return True

        return False

    def execute_action(self, action, game, cheat_mgr):
        if action == "max_upgrades":
            cheat_mgr._max_all_upgrades(game)
            game.player.level = 99
            game.player.xp = 999999
            cheat_mgr._show_cheat_text(game, "МАКС УЛУЧШЕНИЯ!")
        elif action == "spawn_boss":
            cheat_mgr._spawn_random_boss(game)
        elif action == "kill_all":
            cheat_mgr._kill_all_enemies(game)
        elif action == "skip_wave":
            cheat_mgr._skip_wave(game)
        elif action == "add_coins":
            game.add_coins(5000)
            cheat_mgr._show_cheat_text(game, "+5000 МОНЕТ!")
        elif action == "full_heal":
            game.player.health = game.player.max_health
            game.player.shield = game.player.shield_max
            cheat_mgr._show_cheat_text(game, "ПОЛНОЕ ЛЕЧЕНИЕ!")
        elif action == "unlock_all_skins":
            cheat_mgr._unlock_all_skins(game)
        elif action == "max_shop":
            cheat_mgr._max_shop_upgrades(game)
        elif action == "disable_all":
            cheat_mgr._disable_all_cheats(game)
            for cheat in self.toggle_cheats.values():
                cheat["active"] = False
            cheat_mgr._show_cheat_text(game, "ВСЕ ЧИТЫ ВЫКЛЮЧЕНЫ")

    def draw(self, surface, game):
        if not self.visible or not self.initialized:
            return

        width, height = 420, 610
        x = (surface.get_width() - width) // 2
        y = (surface.get_height() - height) // 2

        # Затемнение фона
        overlay = pygame.Surface((surface.get_width(), surface.get_height()), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        # Фон меню
        pygame.draw.rect(surface, (20, 24, 35), (x, y, width, height), border_radius=16)
        pygame.draw.rect(surface, (100, 150, 255), (x, y, width, height), 3, border_radius=16)

        # Заголовок
        title = self.font_title.render("МЕНЮ ЧИТОВ", True, (100, 200, 255))
        title_rect = title.get_rect(centerx=x + width // 2, top=y + 15)
        surface.blit(title, title_rect)

        # Переключаемые читы
        btn_w, btn_h = 360, 45
        start_y = y + 60
        gap = 8

        for i, (key, cheat) in enumerate(self.toggle_cheats.items()):
            rect = pygame.Rect(x + 20, start_y + i * (btn_h + gap), btn_w, btn_h)

            # Цвет кнопки в зависимости от состояния
            if cheat["active"]:
                color = cheat["color"]
                bg_color = tuple(min(255, c + 40) for c in color)
            else:
                bg_color = (45, 50, 65)

            # Рисуем кнопку
            pygame.draw.rect(surface, bg_color, rect, border_radius=8)
            if cheat["active"]:
                pygame.draw.rect(surface, cheat["color"], rect, 3, border_radius=8)
            else:
                pygame.draw.rect(surface, (80, 90, 110), rect, 2, border_radius=8)

            # Название
            name_text = self.font_button.render(cheat["name"], True, (255, 255, 255) if cheat["active"] else (180, 180, 180))
            surface.blit(name_text, (rect.x + 10, rect.y + 6))

            # Описание
            desc_text = self.font_desc.render(cheat["desc"], True, (150, 150, 150) if not cheat["active"] else (200, 200, 200))
            surface.blit(desc_text, (rect.x + 10, rect.y + 26))

            # Индикатор статуса
            status = "ВКЛ" if cheat["active"] else "ВЫКЛ"
            status_color = (50, 255, 100) if cheat["active"] else (150, 150, 150)
            status_text = self.font_button.render(status, True, status_color)
            surface.blit(status_text, (rect.right - status_text.get_width() - 10, rect.centery - status_text.get_height() // 2))

        # Кнопки действий - 3 колонки
        action_start_y = start_y + len(self.toggle_cheats) * (btn_h + gap) + 15
        action_btn_h = 32
        action_btn_w = 120
        action_gap = 8

        for i, btn in enumerate(self.action_buttons):
            row = i // 3
            col = i % 3
            rect = pygame.Rect(x + 15 + col * (action_btn_w + action_gap), action_start_y + row * (action_btn_h + action_gap), action_btn_w, action_btn_h)

            pygame.draw.rect(surface, btn["color"], rect, border_radius=6)
            pygame.draw.rect(surface, tuple(min(255, c + 50) for c in btn["color"]), rect, 2, border_radius=6)

            text = self.font_action.render(btn["name"], True, (255, 255, 255))
            text_rect = text.get_rect(center=rect.center)
            surface.blit(text, text_rect)

        # Инструкции
        inst_text = self.font_desc.render("Нажми INSERT чтобы закрыть | Кликни для вкл/выкл", True, (150, 150, 150))
        inst_rect = inst_text.get_rect(centerx=x + width // 2, bottom=y + height - 25)
        surface.blit(inst_text, inst_rect)

        # Версия
        version_text = self.font_desc.render(VERSION, True, (100, 100, 100))
        version_rect = version_text.get_rect(centerx=x + width // 2, bottom=y + height - 8)
        surface.blit(version_text, version_rect)


class CheatManager:
    """Управляет всей функциональностью читов в игре"""

    def __init__(self):
        self.cheat_cooldown = 0.0
        self.god_mode_active = False
        self.one_hit_kill_active = False
        self.infinite_xp_active = False
        self.speed_hack_active = False
        self.rapid_fire_active = False
        self.noclip_active = False
        self.no_shake_active = False
        self.p2_god_active = False
        self.cheat_menu = CheatMenuUI()

    def handle_input(self, game, event):
        """Обработка ввода читов - только INSERT для открытия меню"""
        if event.type == pygame.KEYDOWN and event.key == pygame.K_INSERT:
            self.cheat_menu.toggle()
            return True
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Обработка кликов меню
            if self.cheat_menu.visible:
                return self.cheat_menu.handle_click(event.pos, game, self)
        return False

    def update(self, game, dt):
        """Обновление эффектов читов - вызывать каждый кадр в update_playing"""
        # Режим бога: макс здоровье и щиты, неуязвимость
        if self.god_mode_active:
            game.player.health = game.player.max_health
            game.player.shield = 999
            game.player.invuln = 999.0  # Постоянная неуязвимость

        # Чит скорости: супер скорость и мгновенный рывок
        if self.speed_hack_active:
            game.player.base_speed = 800  # Супер скорость
            game.player.dash_cooldown = 0.0  # Мгновенный рывок готов
            game.player.dash_timer = 0.0

        # Быстрая стрельба: без задержки, макс многоствольность
        if self.rapid_fire_active:
            game.player.shoot_timer = 0.0  # Мгновенный выстрел
            # Временно максимум скорострельности и многоствольности
            if game.player.upgrade_counts["fire_rate"] < 8:
                game.player.upgrade_counts["fire_rate"] = 8
            if game.player.upgrade_counts["multishot"] < 4:
                game.player.upgrade_counts["multishot"] = 4

        # Без вибрации: отключить тряску экрана
        if self.no_shake_active:
            game.shake = 0.0  # Постоянный сброс тряски в ноль

        # Бесконечный опыт: постоянный прирост
        if self.infinite_xp_active:
            game.player.gain_xp(1000)  # Постоянный прирост опыта

        # Режим бога P2: макс здоровье для 2-го игрока
        if getattr(self, 'p2_god_active', False):
            if hasattr(game, 'remote_players'):
                for p_state in game.remote_players.values():
                    p_state.health = p_state.max_health

    def modify_damage_dealt(self, game, base_damage):
        """Изменение урона игрока - вызывать при расчёте урона пули"""
        if self.one_hit_kill_active:
            return 999999  # Мгновенно убить что угодно
        return base_damage

    def should_take_damage(self, game, amount):
        """Проверка должен ли игрок получить урон - вызывать в take_damage"""
        if self.god_mode_active or self.noclip_active:
            return False  # Урон не получен
        return True

    def _show_cheat_text(self, game, text):
        """Показать всплывающее уведомление чита"""
        try:
            from main import FloatingText, CYAN, CENTER
            game.floating_texts.append(FloatingText(CENTER, text, (255, 50, 255), 2.0))
        except ImportError:
            pass

    def _max_all_upgrades(self, game):
        """Максимальная прокачка всех улучшений игрока"""
        for key in game.player.upgrade_counts:
            max_level = 8  # Максимум по умолчанию
            if key == "max_health":
                max_level = 5
            elif key == "shield":
                max_level = 4
            elif key == "drone":
                max_level = 4
            elif key == "dash":
                max_level = 6
            game.player.upgrade_counts[key] = max_level

        # Применение улучшений здоровья
        game.player.max_health = 100 + 20 * game.player.upgrade_counts["max_health"]
        game.player.health = game.player.max_health
        game.player.magnet_radius = 130 + 50 * game.player.upgrade_counts["magnet"]
        game.player.crit_chance = 0.08 + 0.08 * game.player.upgrade_counts["crit"]
        game.player.crit_bonus = 0.45 + 0.25 * game.player.upgrade_counts["crit"]
        game.player.shield_max = game.player.upgrade_counts["shield"]
        game.player.shield = game.player.shield_max
        game.player.drone_count = game.player.upgrade_counts["drone"]
        game.player.rebuild_drones()

    def _spawn_random_boss(self, game):
        """Заспавнить случайного босса"""
        boss_types = ["boss_core", "boss_blade", "boss_hive", "boss_tempest",
                      "boss_void", "boss_omega", "boss_overlord", "boss_crystal",
                      "boss_time", "boss_flame"]
        boss_kind = random.choice(boss_types)
        from main import Enemy, WIDTH, HEIGHT, FloatingText, CYAN
        boss = Enemy(boss_kind, pygame.Vector2(WIDTH / 2, -120), game.wave)
        game.enemies.append(boss)
        game.boss_alive = True
        game.floating_texts.append(FloatingText(
            pygame.Vector2(WIDTH / 2, HEIGHT / 2),
            boss.title.upper(),
            CYAN, 1.8
        ))
        game.shake += 12

    def _kill_all_enemies(self, game):
        """Убить всех врагов на экране"""
        # Правильное убийство каждого врага через метод kill() для корректной обработки смерти
        for enemy in game.enemies[:]:
            enemy.kill(game)  # Это обрабатывает очки, эффекты, флаг босса и т.д.
        # Список будет очищен автоматически в цикле обновления игры
        self._show_cheat_text(game, "ALL ENEMIES KILLED!")

    def _skip_wave(self, game):
        """Пропустить текущую волну"""
        game.wave += 1
        game.wave_timer = game.wave_duration - 1.0  # Почти завершено
        game.spawn_timer = 0.0

    def _disable_all_cheats(self, game):
        """Отключить все активные читы и сбросить статы игрока"""
        self.god_mode_active = False
        self.one_hit_kill_active = False
        self.infinite_xp_active = False
        self.speed_hack_active = False
        self.rapid_fire_active = False
        self.noclip_active = False
        self.no_shake_active = False
        self.p2_god_active = False

        # Сброс статов игрока к норме
        game.player.base_speed = 310
        game.player.invuln = 0.0
        game.player.shield = min(game.player.shield, game.player.shield_max)
        # Сброс таймера стрельбы чтобы предотвратить мгновенный выстрел после отключения скорострельности
        game.player.shoot_timer = 0.0

    def _unlock_all_skins(self, game):
        """Разблокировать все скины в игре"""
        from main import SKINS
        unlocked = game.progress["unlocked_skins"]
        for skin_key in SKINS.keys():
            if skin_key not in unlocked:
                unlocked.append(skin_key)
        game.save_progress()
        self._show_cheat_text(game, "ALL SKINS UNLOCKED!")

    def _max_shop_upgrades(self, game):
        """Максимальная прокачка всех улучшений магазина"""
        from main import SHOP_UPGRADES
        for key in game.progress["shop_levels"]:
            max_level = len(SHOP_UPGRADES[key]["costs"])
            game.progress["shop_levels"][key] = max_level
        game.save_progress()
        self._show_cheat_text(game, "MAX SHOP UPGRADES!")


def patch_game_for_cheats():
    """
    Вызовите эту функцию в конце main.py для автоматической инъекции обработки читов.
    Изменяет методы класса Game для включения функциональности читов.
    """
    try:
        import __main__ as main  # Получаем главный модуль когда он __main__
        import sys

        # Сохранение оригинальных методов
        original_handle_events = main.Game.handle_events
        original_update_playing = main.Game.update_playing
        original_player_take_damage = main.Player.take_damage

        # Создание экземпляра менеджера читов
        main.cheats = CheatManager()

        # Модифицированный handle_events для включения ввода читов
        def patched_handle_events(self):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.save_progress()
                    self.running = False

                # Обработка переключения меню читов (клавиша INSERT)
                if event.type == pygame.KEYDOWN and event.key == pygame.K_INSERT:
                    if hasattr(main, 'cheats'):
                        main.cheats.cheat_menu.toggle()
                    continue

                # Если меню читов открыто, обрабатываем только клики для него и INSERT для закрытия
                if hasattr(main, 'cheats') and main.cheats.cheat_menu.visible:
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        main.cheats.cheat_menu.handle_click(event.pos, self, main.cheats)
                    continue  # Пропускаем другую обработку событий пока меню открыто

                if self.state == "accounts":
                    self.handle_accounts_input(event)
                elif self.state == "menu":
                    if event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            self.start_run()
                        elif event.key == pygame.K_s:
                            self.open_shop()
                        elif event.key == pygame.K_TAB:
                            # Переключение аккаунта
                            self.state = "accounts"
                            self.current_account = None
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        for rect, action in self.menu_buttons:
                            if rect.collidepoint(event.pos):
                                self.activate_menu_action(action)
                                break
                elif self.state == "shop":
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.state = "menu"
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:
                            for rect, action in self.shop_buttons:
                                if rect.collidepoint(event.pos):
                                    self.handle_shop_action(action)
                                    break
                        elif event.button == 4:
                            mouse_y = event.pos[1]
                            if mouse_y < 420:
                                self.shop_scroll_target = max(0, self.shop_scroll_target - 1)
                            else:
                                self.upgrade_scroll_target = max(0, self.upgrade_scroll_target - 1)
                        elif event.button == 5:
                            mouse_y = event.pos[1]
                            if mouse_y < 420:
                                import __main__ as m
                                self.shop_scroll_target = min(max(0, len(m.SKINS) - 6), self.shop_scroll_target + 1)
                            else:
                                import __main__ as m
                                max_upgrades = max(0, len(m.SHOP_UPGRADES) - 5)
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

        # Модифицированный update_playing для включения обновлений читов
        def patched_update_playing(self, dt):
            self.time += dt
            if self.post_boss_timer <= 0:
                self.wave_timer += dt
            self.extra_life_timer -= dt
            self.coin_spawn_timer -= dt
            self.flash = max(0.0, self.flash - dt)
            self.wave_cleared_flash = max(0.0, self.wave_cleared_flash - dt)

            # Обновление читов
            main.cheats.update(self, dt)

            # Остальная часть оригинальной логики update_playing
            original_update_playing(self, dt)

        # Модифицированный take_damage игрока для режима бога
        def patched_take_damage(self, amount):
            if main.cheats.god_mode_active or main.cheats.noclip_active:
                return False
            return original_player_take_damage(self, amount)

        # Применение патчей
        main.Game.handle_events = patched_handle_events
        main.Game.update_playing = patched_update_playing
        main.Player.take_damage = patched_take_damage

        # Патч главного цикла run чтобы рисовать меню читов последним (поверх всего)
        original_run = main.Game.run

        def patched_run(self):
            while self.running:
                dt = min(0.033, self.clock.tick(main.FPS) / 1000)
                self.handle_events()

                # Обновление анимаций прокрутки
                self.shop_scroll_offset += (self.shop_scroll_target - self.shop_scroll_offset) * 0.2
                self.upgrade_scroll_offset += (self.upgrade_scroll_target - self.upgrade_scroll_offset) * 0.2
                if hasattr(self, 'account_scroll_offset'):
                    self.account_scroll_offset += (self.account_scroll_target - self.account_scroll_offset) * 0.2

                if self.state == "playing":
                    self.update_playing(dt)

                if self.state == "accounts":
                    self.draw_accounts()
                elif self.state == "menu":
                    self.draw_menu()
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

                # Отрисовка меню читов ПОСЛЕДНИМ (поверх всего)
                if hasattr(main, 'cheats') and main.cheats.cheat_menu.visible:
                    main.cheats.cheat_menu.draw(self.screen, self)

                pygame.display.flip()

            # Автосохранение перед выходом
            self.save_progress()
            pygame.quit()
            import sys
            sys.exit()

        main.Game.run = patched_run

        print("[CHEATS] Cheat system injected successfully!")
        print("[CHEATS] Press INSERT to open cheat menu")

    except Exception as e:
        import traceback
        print(f"[CHEATS] Failed to inject cheats: {e}")
        traceback.print_exc()


# Простая автономная чит-система которую можно импортировать
if __name__ == "__main__":
    print("Cheat System for Neon Arena: Eclipse Protocol")
    print("Import this module in main.py and call patch_game_for_cheats()")
    print("")
    print("=== HOW TO USE ===")
    print("Press INSERT during gameplay to open/close the cheat menu")
    print("")
    print("TOGGLE CHEATS (вкл/выкл кнопками в меню):")
    print("  GOD + NOCLIP    - Бессмертие + прохождение сквозь врагов")
    print("  ONE HIT KILL    - Убивает с одного выстрела")
    print("  INFINITE XP     - Постоянный прирост опыта")
    print("  SPEED HACK      - 800 скорость, мгновенный рывок")
    print("  RAPID FIRE      - Мгновенная стрельба")
    print("")
    print("ACTION BUTTONS (одноразовые действия):")
    print("  MAX UPGRADES    - Макс улучшения + 99 уровень")
    print("  SPAWN BOSS      - Заспавнить случайного босса")
    print("  KILL ALL        - Убить всех врагов")
    print("  SKIP WAVE       - Пропустить волну")
    print("  +5000 COINS     - Добавить 5000 монет")
    print("  FULL HEAL       - Полное лечение + щиты")
    print("  ALL SKINS       - Разблокировать все скины")
    print("  MAX SHOP        - Макс уровни всех усилений в магазине")
    print("  DISABLE ALL     - Выключить все читы")
