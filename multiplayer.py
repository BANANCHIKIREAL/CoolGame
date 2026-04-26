"""
Модуль сетевой игры (мультиплеера) для Neon Arena.
Поддерживает LAN мультиплеер с одним хостом и несколькими клиентами.
"""

import socket
import json
import threading
import time
import struct
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Callable
import pygame

DEFAULT_PORT = 5555      # Стандартный порт для игры
BROADCAST_PORT = 5556    # Порт для обнаружения серверов (broadcast)
NETWORK_FPS = 60         # Частота обновления сети


@dataclass
class PlayerInput:
    """Данные ввода игрока - отправляются от клиента к хосту"""
    player_id: int
    move_x: float
    move_y: float
    aim_x: float
    aim_y: float
    shooting: bool = False
    dashing: bool = False
    timestamp: float = 0.0
    facing_x: float = 0.0  # Нормализованное направление взгляда (вычисляется клиентом)
    facing_y: float = 1.0


@dataclass
class PlayerState:
    """Состояние игрока - отправляется от хоста к клиентам"""
    player_id: int
    pos_x: float
    pos_y: float
    vel_x: float
    vel_y: float
    facing_x: float
    facing_y: float
    health: float
    max_health: float
    level: int
    xp: int
    xp_goal: int
    shield: int
    shield_max: int
    extra_lives: int
    skin: str
    invuln: float
    dash_timer: float = 0.0
    dash_cooldown: float = 0.0


@dataclass
class GameState:
    """Полное состояние игры для синхронизации между клиентами"""
    timestamp: float
    wave: int
    wave_timer: float
    boss_alive: bool
    players: List[PlayerState]
    enemies: List[dict]
    bullets: List[dict]
    gems: List[dict]
    coins: List[dict]
    particles: List[dict]
    floating_texts: List[dict]


class NetworkBase:
    """Базовый класс для сетевого взаимодействия"""

    def __init__(self, port=DEFAULT_PORT):
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setblocking(False)
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.callbacks: List[Callable] = []

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._network_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        self.socket.close()

    def _network_loop(self):
        """Переопределить в подклассах"""
        pass

    def send_message(self, data: dict, addr: tuple):
        """Отправить JSON сообщение на адрес"""
        try:
            message = json.dumps(data).encode('utf-8')
            # Простое кадрирование с префиксом длины
            prefix = struct.pack('!I', len(message))
            self.socket.sendto(prefix + message, addr)
        except Exception as e:
            print(f"[NETWORK] Send error: {e}")

    def receive_message(self, max_size=65535) -> Optional[tuple]:
        """Получить сообщение из сокета"""
        try:
            data, addr = self.socket.recvfrom(max_size)
            if len(data) < 4:
                return None
            msg_len = struct.unpack('!I', data[:4])[0]
            message = json.loads(data[4:4+msg_len].decode('utf-8'))
            return message, addr
        except BlockingIOError:
            return None
        except Exception as e:
            print(f"[NETWORK] Receive error: {e}")
            return None


class GameHost(NetworkBase):
    """Хост/сервер для мультиплеерных игр - управляет игровой логикой"""

    def __init__(self, port=DEFAULT_PORT):
        super().__init__(port)
        self.socket.bind(('0.0.0.0', port))
        self.clients: Dict[int, tuple] = {}  # player_id -> (ip, порт)
        self.client_inputs: Dict[int, PlayerInput] = {}
        self.client_upgrade_choices: Dict[int, List[str]] = {}
        self.next_player_id = 2  # Хост всегда игрок 1
        self.broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.game_state: Optional[GameState] = None

    def start(self):
        super().start()
        # Запуск потока широковещательной рассылки для обнаружения
        self.broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self.broadcast_thread.start()
        print(f"[HOST] Game server started on port {self.port}")

    def _broadcast_loop(self):
        """Рассылка широковещательных сообщений о доступности игры в LAN"""
        while self.running:
            try:
                broadcast_data = json.dumps({
                    'type': 'discover',
                    'port': self.port,
                    'players': len(self.clients) + 1
                }).encode('utf-8')
                # Используем кадрирование с префиксом длины
                prefix = struct.pack('!I', len(broadcast_data))
                self.broadcast_socket.sendto(prefix + broadcast_data, ('<broadcast>', BROADCAST_PORT))
            except Exception as e:
                print(f"[HOST] Broadcast error: {e}")
            time.sleep(2.0)

    def _network_loop(self):
        """Обработка входящих сообщений"""
        while self.running:
            result = self.receive_message()
            if result:
                message, addr = result
                self._handle_message(message, addr)
            time.sleep(0.001)  # 1мс чтобы не грузить CPU

    def _handle_message(self, message: dict, addr: tuple):
        """Обработать сообщение от клиента"""
        msg_type = message.get('type')

        if msg_type == 'join':
            # Новый клиент хочет присоединиться
            player_id = self.next_player_id
            self.next_player_id += 1
            self.clients[player_id] = addr
            self.send_message({
                'type': 'joined',
                'player_id': player_id,
                'your_addr': addr
            }, addr)
            print(f"[HOST] Player {player_id} joined from {addr}")

        elif msg_type == 'input':
            # Клиент отправляет ввод (нажатия клавиш)
            player_id = message.get('player_id')
            if player_id in self.clients:
                self.client_inputs[player_id] = PlayerInput(
                    player_id=player_id,
                    move_x=message.get('move_x', 0),
                    move_y=message.get('move_y', 0),
                    aim_x=message.get('aim_x', 0),
                    aim_y=message.get('aim_y', 0),
                    shooting=message.get('shooting', False),
                    dashing=message.get('dashing', False),
                    timestamp=message.get('timestamp', time.time()),
                    facing_x=message.get('facing_x', 0),
                    facing_y=message.get('facing_y', 1)
                )

        elif msg_type == 'leave':
            # Клиент отключился
            player_id = message.get('player_id')
            if player_id in self.clients:
                del self.clients[player_id]
                if player_id in self.client_inputs:
                    del self.client_inputs[player_id]
                if player_id in self.client_upgrade_choices:
                    del self.client_upgrade_choices[player_id]
                print(f"[HOST] Player {player_id} left")
        elif msg_type == 'upgrade_choice':
            player_id = message.get('player_id')
            upgrade_key = message.get('upgrade_key')
            if player_id in self.clients and isinstance(upgrade_key, str):
                if player_id not in self.client_upgrade_choices:
                    self.client_upgrade_choices[player_id] = []
                self.client_upgrade_choices[player_id].append(upgrade_key)

    def broadcast_state(self, game_state: GameState):
        """Отправить состояние игры всем клиентам"""
        state_data = {
            'type': 'state',
            'timestamp': game_state.timestamp,
            'wave': game_state.wave,
            'wave_timer': game_state.wave_timer,
            'boss_alive': game_state.boss_alive,
            'players': [asdict(p) for p in game_state.players],
            'enemies': game_state.enemies,
            'bullets': game_state.bullets,
            'gems': game_state.gems,
            'coins': game_state.coins,
            'particles': game_state.particles,
            'floating_texts': game_state.floating_texts,
        }

        for player_id, addr in self.clients.items():
            try:
                self.send_message(state_data, addr)
            except Exception as e:
                print(f"[HOST] Failed to send state to player {player_id}: {e}")

    def get_client_input(self, player_id: int) -> Optional[PlayerInput]:
        """Получить последний ввод от клиента"""
        return self.client_inputs.get(player_id)

    def get_all_client_inputs(self) -> Dict[int, PlayerInput]:
        """Получить ввод от всех клиентов"""
        return self.client_inputs.copy()

    def pop_client_upgrade_choices(self, player_id: int) -> List[str]:
        """Получить и очистить выбор улучшений клиента"""
        choices = self.client_upgrade_choices.get(player_id, [])
        self.client_upgrade_choices[player_id] = []
        return choices

    def broadcast_game_start(self):
        """Уведомить всех клиентов о начале игры"""
        start_data = {
            'type': 'game_start',
            'timestamp': time.time()
        }
        for player_id, addr in self.clients.items():
            try:
                self.send_message(start_data, addr)
                print(f"[HOST] Sent game_start to player {player_id}")
            except Exception as e:
                print(f"[HOST] Failed to send game_start to player {player_id}: {e}")


class GameClient(NetworkBase):
    """Клиент для подключения к хосту мультиплеера"""

    def __init__(self):
        super().__init__()
        self.host_addr: Optional[tuple] = None
        self.player_id: Optional[int] = None
        self.connected = False
        self.last_state: Optional[GameState] = None
        self.pending_inputs: List[PlayerInput] = []
        self.game_started = False  # Ждём пока хост начнёт игру

    def discover_hosts(self, timeout=3.0) -> List[dict]:
        """Найти доступные игры в LAN"""
        hosts = []
        # Привязка к порту широковещательной рассылки
        discover_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discover_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        discover_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        discover_socket.bind(('0.0.0.0', BROADCAST_PORT))
        discover_socket.settimeout(timeout)

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                data, addr = discover_socket.recvfrom(1024)
                # Обработка кадрирования с префиксом длины
                if len(data) < 4:
                    continue
                msg_len = struct.unpack('!I', data[:4])[0]
                message = json.loads(data[4:4+msg_len].decode('utf-8'))
                if message.get('type') == 'discover':
                    host_info = {
                        'ip': addr[0],
                        'port': message.get('port', DEFAULT_PORT),
                        'players': message.get('players', 1)
                    }
                    # Избегаем дубликатов
                    if not any(h['ip'] == host_info['ip'] for h in hosts):
                        hosts.append(host_info)
                        print(f"[CLIENT] Found host at {addr[0]}:{host_info['port']}")
            except socket.timeout:
                break
            except Exception:
                continue

        discover_socket.close()
        return hosts

    def connect(self, host_ip: str, port=DEFAULT_PORT) -> bool:
        """Подключиться к хосту"""
        try:
            self.host_addr = (host_ip, port)
            # Отправка запроса на присоединение с кадрированием префикса длины
            join_data = json.dumps({'type': 'join'}).encode('utf-8')
            prefix = struct.pack('!I', len(join_data))
            self.socket.sendto(prefix + join_data, self.host_addr)

            # Ждём ответа
            self.socket.settimeout(5.0)
            try:
                data, addr = self.socket.recvfrom(1024)
                # Обработка ответа с префиксом длины
                if len(data) >= 4:
                    msg_len = struct.unpack('!I', data[:4])[0]
                    message = json.loads(data[4:4+msg_len].decode('utf-8'))
                else:
                    message = json.loads(data.decode('utf-8'))

                if message.get('type') == 'joined':
                    self.player_id = message.get('player_id')
                    self.connected = True
                    self.start()
                    print(f"[CLIENT] Connected as player {self.player_id}")
                    return True
            except socket.timeout:
                print("[CLIENT] Connection timed out")
                return False

        except Exception as e:
            print(f"[CLIENT] Connection error: {e}")
            return False

    def _network_loop(self):
        """Получение состояния игры от хоста"""
        while self.running:
            result = self.receive_message()
            if result:
                message, addr = result
                msg_type = message.get('type')
                if msg_type == 'state':
                    self._handle_state(message)
                elif msg_type == 'game_start':
                    self.game_started = True
                    print("[CLIENT] Game started by host!")
            time.sleep(0.001)  # 1мс чтобы не грузить CPU

    def _handle_state(self, message: dict):
        """Обработать состояние игры от хоста"""
        try:
            players = [PlayerState(**p) for p in message.get('players', [])]
            self.last_state = GameState(
                timestamp=message.get('timestamp', 0),
                wave=message.get('wave', 1),
                wave_timer=message.get('wave_timer', 0),
                boss_alive=message.get('boss_alive', False),
                players=players,
                enemies=message.get('enemies', []),
                bullets=message.get('bullets', []),
                gems=message.get('gems', []),
                coins=message.get('coins', []),
                particles=message.get('particles', []),
                floating_texts=message.get('floating_texts', [])
            )
        except Exception as e:
            print(f"[CLIENT] Error parsing state: {e}")

    def send_input(self, player_input: PlayerInput):
        """Отправить ввод игрока на хост"""
        if not self.connected or not self.host_addr:
            return

        input_data = {
            'type': 'input',
            'player_id': self.player_id,
            'move_x': player_input.move_x,
            'move_y': player_input.move_y,
            'aim_x': player_input.aim_x,
            'aim_y': player_input.aim_y,
            'facing_x': player_input.facing_x,
            'facing_y': player_input.facing_y,
            'shooting': player_input.shooting,
            'dashing': player_input.dashing,
            'timestamp': time.time()
        }
        self.send_message(input_data, self.host_addr)

    def disconnect(self):
        """Отключиться от хоста"""
        if self.connected and self.host_addr:
            self.send_message({
                'type': 'leave',
                'player_id': self.player_id
            }, self.host_addr)
        self.connected = False
        self.stop()

    def send_upgrade_choice(self, player_id: int, upgrade_key: str):
        """Отправить выбранное улучшение на хост"""
        if not self.connected or not self.host_addr:
            return
        self.send_message({
            'type': 'upgrade_choice',
            'player_id': player_id,
            'upgrade_key': upgrade_key,
            'timestamp': time.time()
        }, self.host_addr)

    def get_latest_state(self) -> Optional[GameState]:
        """Получить последнее полученное состояние игры"""
        return self.last_state

    def is_game_started(self) -> bool:
        """Проверить начал ли хост игру"""
        return self.game_started


class LocalPlayerInput:
    """Помощник для захвата локального ввода игрока"""

    @staticmethod
    def capture(player_id: int, camera: pygame.Vector2, player_pos: pygame.Vector2 = None) -> PlayerInput:
        """Захватить текущий ввод для игрока"""
        keys = pygame.key.get_pressed()

        # В онлайн-мультиплеере каждый клиент управляет только своим локальным игроком.
        # Используем те же управление что и в локальном Player.update() для синхронизации клиента и сервера.
        move_x = keys[pygame.K_d] - keys[pygame.K_a]
        move_y = keys[pygame.K_s] - keys[pygame.K_w]

        # Прицеливание - мышь относительно камеры
        mouse_pos = pygame.mouse.get_pos()
        aim_x = mouse_pos[0] + camera.x
        aim_y = mouse_pos[1] + camera.y

        shooting = pygame.mouse.get_pressed()[0]
        dashing = keys[pygame.K_SPACE]

        # Вычисление направления взгляда от игрока к точке прицела
        facing_x, facing_y = 1.0, 0.0  # По умолчанию смотрит вправо
        if player_pos is not None:
            aim_vec = pygame.Vector2(aim_x, aim_y)
            to_aim = aim_vec - player_pos
            if to_aim.length_squared() > 0:
                to_aim = to_aim.normalize()
                facing_x, facing_y = to_aim.x, to_aim.y

        return PlayerInput(
            player_id=player_id,
            move_x=float(move_x),
            move_y=float(move_y),
            aim_x=float(aim_x),
            aim_y=float(aim_y),
            facing_x=facing_x,
            facing_y=facing_y,
            shooting=shooting,
            dashing=dashing,
            timestamp=time.time()
        )
