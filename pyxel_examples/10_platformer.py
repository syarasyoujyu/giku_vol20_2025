# title: Pyxel Platformer
# author: Takashi Kitao
# desc: A Pyxel platformer example
# site: https://github.com/kitao/pyxel
# license: MIT
# version: 1.0

import pyxel
import time
import sounddevice as sd
import numpy as np
import tempfile
import wave
from get_direction_from_audio import get_text, closest_direction
# 録音設定
SAMPLE_RATE = 44100  # サンプルレート（44.1kHz）
DURATION = 5       # 録音時間（1秒）

TRANSPARENT_COLOR = 2
SCROLL_BORDER_X = 80
TILE_FLOOR = (1, 0)
TILE_SPAWN1 = (0, 1)
TILE_SPAWN2 = (1, 1)
TILE_SPAWN3 = (2, 1)
GOAL = (0, 8)
WALL_TILE_X = 4

scroll_x = 0
player = None
enemies = []
goal = None

timer = 0
stage_list = ["assets/platformer.pyxres", "assets/platformer2.pyxres", "assets/platformer3.pyxres"]
stage_num = 0

def record_audio():
    """マイクから音声を1秒録音"""
    print("録音中...")
    audio_data = sd.rec(int(SAMPLE_RATE * DURATION), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()  # 録音終了まで待機
    print("録音完了")
    audio_16bit=audio_data / audio_data.max() * np.iinfo(np.int16).max
    return audio_16bit.astype(np.int16)

def get_most_similar_direction(audio_data):
    # 一時ファイルに保存
    with tempfile.NamedTemporaryFile(delete=True, suffix=".wav", mode="wb") as temp_file:
        # WAV ファイルを書き込み
        with wave.open(temp_file.name, 'wb') as wav_file:
            wav_file.setnchannels(1)  # モノラル
            wav_file.setsampwidth(2)  # サンプル幅（2バイト = 16ビット）
            wav_file.setframerate(SAMPLE_RATE)  # サンプルレート
            wav_file.writeframes(audio_data.tobytes())  # データを書き込み
        input_text=get_text(temp_file.name)
        print(f"入力テキスト: '{input_text}'")
        return closest_direction(input_text)

def get_tile(tile_x, tile_y):
    return pyxel.tilemaps[0].pget(tile_x, tile_y)


def is_colliding(x, y, is_falling):
    x1 = pyxel.floor(x) // 8
    y1 = pyxel.floor(y) // 8
    x2 = (pyxel.ceil(x) + 7) // 8
    y2 = (pyxel.ceil(y) + 7) // 8
    for yi in range(y1, y2 + 1):
        for xi in range(x1, x2 + 1):
            if get_tile(xi, yi)[0] >= WALL_TILE_X:
                return True
    if is_falling and y % 8 == 1:
        for xi in range(x1, x2 + 1):
            if get_tile(xi, y1 + 1) == TILE_FLOOR:
                return True
    return False


def push_back(x, y, dx, dy):
    for _ in range(pyxel.ceil(abs(dy))):
        step = max(-1, min(1, dy))
        if is_colliding(x, y + step, dy > 0):
            break
        y += step
        dy -= step
    for _ in range(pyxel.ceil(abs(dx))):
        step = max(-1, min(1, dx))
        if is_colliding(x + step, y, dy > 0):
            break
        x += step
        dx -= step
    return x, y


def is_wall(x, y):
    tile = get_tile(x // 8, y // 8)
    return tile == TILE_FLOOR or tile[0] >= WALL_TILE_X


def spawn_enemy(left_x, right_x):
    left_x = pyxel.ceil(left_x / 8)
    right_x = pyxel.floor(right_x / 8)
    for x in range(left_x, right_x + 1):
        for y in range(16):
            tile = get_tile(x, y)
            if tile == TILE_SPAWN1:
                enemies.append(Enemy1(x * 8, y * 8))
            elif tile == TILE_SPAWN2:
                enemies.append(Enemy2(x * 8, y * 8))
            elif tile == TILE_SPAWN3:
                enemies.append(Enemy3(x * 8, y * 8))

def spawn_goal(left_x, right_x):
    left_x = pyxel.ceil(left_x / 8)
    right_x = pyxel.floor(right_x / 8)
    for x in range(left_x, right_x + 1):
        for y in range(16):
            tile = get_tile(x, y)
            if tile == TILE_SPAWN1:
                global goal
                goal == Goal(x * 8, y * 8)


def cleanup_entities(entities):
    for i in range(len(entities) - 1, -1, -1):
        if not entities[i].is_alive:
            del entities[i]


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.dx = 0
        self.dy = 0
        self.jump_start = 0
        self.direction = 1
        self.is_falling = False
        self.is_moving_left = False
        self.is_moving_right = False


    def update(self,direction,presed_r):
        audio_direction=direction if presed_r else None
        global scroll_x
        last_y = self.y
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_LEFT) or audio_direction == "左":
            self.is_moving_right = True
            self.is_moving_left = False
            self.dx = -2
            self.direction = -1
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_RIGHT) or audio_direction == "右":
            self.is_moving_left = True
            self.is_moving_right = False
            self.dx = 2
            self.direction = 1
        self.dy = min(self.dy + 1, 3)

        if pyxel.btnp(pyxel.KEY_DOWN) or pyxel.btn(pyxel.GAMEPAD1_BUTTON_DPAD_DOWN):
            self.is_moving_right = False
            self.is_moving_left = False
            self.dx = 0

        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.GAMEPAD1_BUTTON_A) or audio_direction == "上":
            current_time = time.time()
            if (current_time - self.jump_start > 0.5):
                self.dy = -9
                pyxel.play(3, 8)
                self.jump_start = current_time
        self.x, self.y = push_back(self.x, self.y, self.dx, self.dy)


        if self.is_moving_right:
            self.dx = -3
        elif self.is_moving_left:
            self.dx = 3
        if self.x < scroll_x:
            self.x = scroll_x
        if self.y < 0:
            self.y = 0
        self.dx = int(self.dx * 0.8)
        self.is_falling = self.y > last_y

        if self.x > scroll_x + SCROLL_BORDER_X:
            last_scroll_x = scroll_x
            scroll_x = min(self.x - SCROLL_BORDER_X, 240 * 8)
            spawn_enemy(last_scroll_x + 128, scroll_x + 127)
            spawn_goal(last_scroll_x + 128, scroll_x + 127)
        if self.y >= pyxel.height:
            game_over()

    def draw(self):
        u = (2 if self.is_falling else pyxel.frame_count // 3 % 2) * 8
        w = 8 if self.direction > 0 else -8
        pyxel.blt(self.x, self.y, 0, u, 16, w, 8, TRANSPARENT_COLOR)


class Enemy1:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.dx = 0
        self.dy = 0
        self.direction = -1
        self.is_alive = True

    def update(self):
        self.dx = self.direction
        self.dy = min(self.dy + 1, 3)
        if self.direction < 0 and is_wall(self.x - 1, self.y + 4):
            self.direction = 1
        elif self.direction > 0 and is_wall(self.x + 8, self.y + 4):
            self.direction = -1
        self.x, self.y = push_back(self.x, self.y, self.dx, self.dy)

    def draw(self):
        u = pyxel.frame_count // 4 % 2 * 8
        w = 8 if self.direction > 0 else -8
        pyxel.blt(self.x, self.y, 0, u, 24, w, 8, TRANSPARENT_COLOR)


class Enemy2:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.dx = 0
        self.dy = 0
        self.direction = 1
        self.is_alive = True

    def update(self):
        self.dx = self.direction
        self.dy = min(self.dy + 1, 3)
        if is_wall(self.x, self.y + 8) or is_wall(self.x + 7, self.y + 8):
            if self.direction < 0 and (
                is_wall(self.x - 1, self.y + 4) or not is_wall(self.x - 1, self.y + 8)
            ):
                self.direction = 1
            elif self.direction > 0 and (
                is_wall(self.x + 8, self.y + 4) or not is_wall(self.x + 7, self.y + 8)
            ):
                self.direction = -1
        self.x, self.y = push_back(self.x, self.y, self.dx, self.dy)

    def draw(self):
        u = pyxel.frame_count // 4 % 2 * 8 + 16
        w = 8 if self.direction > 0 else -8
        pyxel.blt(self.x, self.y, 0, u, 24, w, 8, TRANSPARENT_COLOR)


class Enemy3:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.time_to_fire = 0
        self.is_alive = True

    def update(self):
        self.time_to_fire -= 1
        if self.time_to_fire <= 0:
            dx = player.x - self.x
            dy = player.y - self.y
            sq_dist = dx * dx + dy * dy
            if sq_dist < 60**2:
                dist = pyxel.sqrt(sq_dist)
                enemies.append(Enemy3Bullet(self.x, self.y, dx / dist, dy / dist))
                self.time_to_fire = 60

    def draw(self):
        u = pyxel.frame_count // 8 % 2 * 8
        pyxel.blt(self.x, self.y, 0, u, 32, 8, 8, TRANSPARENT_COLOR)


class Enemy3Bullet:
    def __init__(self, x, y, dx, dy):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.is_alive = True

    def update(self):
        self.x += self.dx
        self.y += self.dy

    def draw(self):
        u = pyxel.frame_count // 2 % 2 * 8 + 16
        pyxel.blt(self.x, self.y, 0, u, 32, 8, 8, TRANSPARENT_COLOR)
class Goal:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def draw(self):
        u = pyxel.frame_count // 2 % 2 * 8 + 16
        pyxel.blt(self.x, self.y, 0, u, 32, 8, 8, TRANSPARENT_COLOR)




class Stage:
    def __init__(self):
        pyxel.load(stage_list[stage_num])

        # Change enemy spawn tiles invisible
        pyxel.images[0].rect(0, 8, 24, 8, TRANSPARENT_COLOR)

        global player
        player = Player(0, 0)
        spawn_enemy(0, 127)
        self.direction=None
        self.pressed_r=False
        pyxel.playm(0, loop=True)
        pyxel.run(self.update, self.draw)
    def update(self):
        self.pressed_r=False
        if pyxel.btnp(pyxel.KEY_R):  # 'R'キーを押したら録音
            self.pressed_r=True
            audio_data = record_audio()
            self.direction = get_most_similar_direction(audio_data)
            print(f"最も近い方向: '{self.direction}'")

        if pyxel.btn(pyxel.KEY_Q):
            pyxel.quit()

        player.update(self.direction,self.pressed_r)
        for enemy in enemies:
            if abs(player.x - enemy.x) < 6 and -2 < player.y - enemy.y < 6:
                game_over()
                return
            enemy.update()
            if abs(player.x - enemy.x) < 6  and -6 <= player.y - enemy.y  <= -2:
                pyxel.play(3, 8)
                enemies.remove(enemy)
                enemy.is_alive = False
                player.x, player.y = push_back(player.x, player.y, player.dx, -10)
            if enemy.x < scroll_x - 8 or enemy.x > scroll_x + 160 or enemy.y > 160:
                enemy.is_alive = False
        cleanup_entities(enemies)
        global timer
        timer += 1
        if goal != None:
            if abs(player.x- goal.x) < 6:
                clear()


    def draw(self):
        pyxel.cls(0)

        # Draw level
        pyxel.camera()
        pyxel.bltm(0, 0, 0, (scroll_x // 4) % 128, 128, 128, 128)
        pyxel.bltm(0, 0, 0, scroll_x, 0, 128, 128, TRANSPARENT_COLOR)

        pyxel.text(79, 2, "TIME:" + str(timer//30), 0)
        pyxel.text(80, 3, "TIME:" + str(timer//30), 10)
        pyxel.text(5, 3, "STAGE:" + str(stage_num + 1), 10)
        english_direction = "UP" if self.direction == "上" else "LEFT" if self.direction == "左" else "RIGHT" if self.direction == "右" else None
        pyxel.text(5, 10, f"DIRECTION (AUDIO):{english_direction}", 10)
        # Draw characters
        pyxel.camera(scroll_x, 0)
        player.draw()
        for enemy in enemies:
            enemy.draw()


def game_over():
    #ゲームオーバーになったら変数を初期化
    global timer, enemies, player, scroll_x
    pyxel.play(3, 9)
    restart_x = (pyxel.width - len("Press SPACE to Restart") * 4) // 2
    while True:
        pyxel.cls(0)
        pyxel.camera(scroll_x, 0)
        pyxel.bltm(0, 0, 0, scroll_x, 0, 128, 128, TRANSPARENT_COLOR)
        player.draw()
        for enemy in enemies:
            enemy.draw()
        pyxel.camera()
        pyxel.rect(34, 48, 60, 32, 0)
        pyxel.text(44, 56, "GAME OVER", pyxel.frame_count % 16)
        pyxel.text(restart_x, 68, "Press SPACE to Restart", 7)
        pyxel.flip()
        if pyxel.btnp(pyxel.KEY_SPACE):
            break
    scroll_x = 0
    player.x = 0
    player.y = 0
    player.dx = 0
    player.dy = 0
    global timer
    timer = 0
    enemies = []
    spawn_enemy(0, 127)

def clear():
    #  ここにクリア画面を置く
    #ステージを進める
    stage_num += 1


def App():
    pyxel.init(128, 128, title="Pyxel Platformer")
    #3ステージ終わるまでループ処理
    while stage_num < 3:
        global stage
        stage = Stage()
    pyxel.cls(0)
    pyxel.text(55, 41, "コンプリートおめでとう！", 5)

App()


