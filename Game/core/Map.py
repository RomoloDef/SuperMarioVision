import pygame as pg
from pytmx.util_pygame import load_pygame

from ui.GameUI import GameUI
from entities.environment.BGObject import BGObject
from core.Camera import Camera
from core.Event import Event
from entities.environment.Flag import Flag
from core.Const import *
from entities.environment.Platform import Platform
from entities.Player import Player
from entities.enemies.Goombas import Goombas
from entities.items.Mushroom import Mushroom
from entities.items.Flower import Flower
from entities.enemies.Koopa import Koopa
from entities.items.Tube import Tube
from entities.environment.PlatformDebris import PlatformDebris
from entities.environment.CoinDebris import CoinDebris
from entities.items.Fireball import Fireball
from ui.Text import Text


class Map(object):
    """

    Questa classe rappresenta la mappa. Contiene tutti i blocchi, i nemici, i proiettili, i tubi e tutto ciò che
    c'è nella mappa. Contiene anche il player, la camera e l'evento (morte o vittoria). Ha funzioni per aggiornaree
    e renderizzare tutto ciò che c'è nella mappa. Contiene anche funzioni per spawnare i nemici, i proiettili, il testo e così via.

    """

    def __init__(self, world_num):
        self.obj = []
        self.obj_bg = []
        self.tubes = []
        self.debris = []
        self.mobs = []
        self.projectiles = []
        self.text_objects = []
        self.map = 0
        self.flag = None

        self.mapSize = (0, 0)
        self.sky = 0

        self.textures = {}
        self.worldNum = world_num
        self.loadWorld_11()

        self.is_mob_spawned = [False, False]
        self.score_for_killing_mob = 100
        self.score_time = 0

        self.in_event = False
        self.tick = 0
        self.time = 400

        self.oPlayer = Player(x_pos=128, y_pos=351)
        self.oCamera = Camera(self.mapSize[0] * 32, 14)
        self.oEvent = Event()
        self.oGameUI = GameUI()

    def loadWorld_11(self):
        tmx_data = load_pygame("Game/assets/worlds/1-1/W11.tmx")
        self.mapSize = (tmx_data.width, tmx_data.height)

        self.sky = pg.Surface((WINDOW_W, WINDOW_H))
        self.sky.fill((pg.Color('#5c94fc')))

        # 2D List
        self.map = [[0] * tmx_data.height for i in range(tmx_data.width)]

        layer_num = 0
        for layer in tmx_data.visible_layers:
            for y in range(tmx_data.height):
                for x in range(tmx_data.width):

                    # Otteniamo l'immagine del tile in quella posizione
                    image = tmx_data.get_tile_image(x, y, layer_num)

                    # Se non c'è nessun tile, sarà None, quindi controlliamo questo prima di creare un oggetto.
                    if image is not None:
                        tileID = tmx_data.get_tile_gid(x, y, layer_num)

                        if layer.name == 'Foreground':

                            # Il tile con ID 22 è un blocco "question". Quando il player lo attiva, cambia immagine. Per questo motivo
                            if tileID == 22:
                                image = (
                                    image,                                      # 1
                                    tmx_data.get_tile_image(0, 15, layer_num),   # 2
                                    tmx_data.get_tile_image(1, 15, layer_num),   # 3
                                    tmx_data.get_tile_image(2, 15, layer_num)    # activated
                                )

                            # Creiamo un oggetto Platform e lo aggiungiamo alla lista degli oggetti. 
                            # Inoltre, aggiungiamo questo oggetto alla mappa, così possiamo controllare le collisioni.
                            self.map[x][y] = Platform(x * tmx_data.tileheight, y * tmx_data.tilewidth, image, tileID)
                            self.obj.append(self.map[x][y])

                        elif layer.name == 'Background':
                            self.map[x][y] = BGObject(x * tmx_data.tileheight, y * tmx_data.tilewidth, image)
                            self.obj_bg.append(self.map[x][y])
            layer_num += 1

        # Tubi
        self.spawn_tube(28, 10)
        self.spawn_tube(37, 9)
        self.spawn_tube(46, 8)
        self.spawn_tube(55, 8)
        self.spawn_tube(163, 10)
        self.spawn_tube(179, 10)

        # Moba
        self.mobs.append(Goombas(736, 352, False))
        self.mobs.append(Goombas(1295, 352, True))
        self.mobs.append(Goombas(1632, 352, False))
        self.mobs.append(Goombas(5570, 352, False))

        self.map[21][8].bonus = 'mushroom'
        self.map[78][8].bonus = 'mushroom'
        self.map[109][4].bonus = 'mushroom'

        self.flag = Flag(6336, 48)

    def reset(self, reset_all):
        self.obj = []
        self.obj_bg = []
        self.tubes = []
        self.debris = []
        self.mobs = []
        self.is_mob_spawned = [False, False]

        self.in_event = False
        self.flag = None
        self.sky = None
        self.map = None

        self.tick = 0
        self.time = 400

        self.mapSize = (0, 0)
        self.textures = {}
        self.loadWorld_11()

        self.get_event().reset()
        self.get_player().reset(reset_all)
        self.get_camera().reset()

    def get_name(self):
        if self.worldNum == '1-1':
            return '1-1'

    def get_player(self):
        return self.oPlayer

    def get_camera(self):
        return self.oCamera

    def get_event(self):
        return self.oEvent

    def get_ui(self):
        return self.oGameUI

    def get_blocks_for_collision(self, x, y):
        """

        Ritorna i blocchi intorno al player per controllare le collisioni. 
        Controlliamo solo i blocchi intorno al player per ottimizzare il gioco, 
        così non dobbiamo controllare ogni blocco della mappa.

        """
        return (
            self.map[x][y - 1],
            self.map[x][y + 1],
            self.map[x][y],
            self.map[x - 1][y],
            self.map[x + 1][y],
            self.map[x + 2][y],
            self.map[x + 1][y - 1],
            self.map[x + 1][y + 1],
            self.map[x][y + 2],
            self.map[x + 1][y + 2],
            self.map[x - 1][y + 1],
            self.map[x + 2][y + 1],
            self.map[x][y + 3],
            self.map[x + 1][y + 3]
        )

    def get_blocks_below(self, x, y):
        """

        Ritorna i blocchi sotto il player per controllare se è a terra o no.
        Controlliamo solo i blocchi sotto il player per ottimizzare il gioco,
        così non dobbiamo controllare ogni blocco della mappa.

        """
        return (
            self.map[x][y + 1],
            self.map[x + 1][y + 1]
        )

    def get_mobs(self):
        return self.mobs

    def spawn_tube(self, x_coord, y_coord):
        self.tubes.append(Tube(x_coord, y_coord))

        # Adding tube's collision just by spawning tiles inside the tube.
        # They will not render because we are adding them to "collision" list.
        for y in range(y_coord, 12): # 12 because it's ground level.
            for x in range(x_coord, x_coord + 2):
                self.map[x][y] = Platform(x * 32, y * 32, image=None, type_id=0)

    def spawn_mushroom(self, x, y):
        self.get_mobs().append(Mushroom(x, y, True))

    def spawn_goombas(self, x, y, move_direction):
        self.get_mobs().append(Goombas(x, y, move_direction))

    def spawn_koopa(self, x, y, move_direction):
        self.get_mobs().append(Koopa(x, y, move_direction))

    def spawn_flower(self, x, y):
        self.mobs.append(Flower(x, y))

    def spawn_debris(self, x, y, type):
        if type == 0:
            self.debris.append(PlatformDebris(x, y))
        elif type == 1:
            self.debris.append(CoinDebris(x, y))

    def spawn_fireball(self, x, y, move_direction):
        self.projectiles.append(Fireball(x, y, move_direction))

    def spawn_score_text(self, x, y, score=None):
        """

        This text appears when you, for example, kill a mob. It shows how many points
        you got.

        """

        # Score is none only when you kill a mob. If you got a killstreak,
        # amount of points for killing a mob will increase: 100, 200, 400, 800...
        # So you don't know how many points you should add.
        if score is None:
            self.text_objects.append(Text(str(self.score_for_killing_mob), 16, (x, y)))

            # Next score will be bigger
            self.score_time = pg.time.get_ticks()
            if self.score_for_killing_mob < 1600:
                self.score_for_killing_mob *= 2

        # That case for all other situations.
        else:
            self.text_objects.append(Text(str(score), 16, (x, y)))

    def remove_object(self, object):
        self.obj.remove(object)
        self.map[object.rect.x // 32][object.rect.y // 32] = 0

    def remove_whizbang(self, whizbang):
        self.projectiles.remove(whizbang)

    def remove_text(self, text_object):
        self.text_objects.remove(text_object)

    def update_player(self, core):
        self.get_player().update(core)

    def update_entities(self, core):
        for mob in self.mobs:
            mob.update(core)
            if not self.in_event:
                self.entity_collisions(core)

    def update_time(self, core):
        """

        Updating a map time.

        """

        # Time updates only if map not in event
        if not self.in_event:
            self.tick += 1
            if self.tick % 40 == 0:
                self.time -= 1
                self.tick = 0
            if self.time == 100 and self.tick == 1:
                core.get_sound().start_fast_music(core)
            elif self.time == 0:
                self.player_death(core)

    def update_score_time(self):
        """

        When player kill mobs in a row, score for each mob
        will increase. When player stops kill mobs, points
        will reset to 100. This function updates these points.

        """
        if self.score_for_killing_mob != 100:

            # Delay is 750 ms
            if pg.time.get_ticks() > self.score_time + 750:
                self.score_for_killing_mob //= 2

    def entity_collisions(self, core):
        if not core.get_map().get_player().unkillable:
            for mob in self.mobs:
                mob.check_collision_with_player(core)

    def try_spawn_mobs(self, core):
        """

        These mobs will appear when player will reach the certain x-coordinate

        """
        if self.get_player().rect.x > 2080 and not self.is_mob_spawned[0]:
            self.spawn_goombas(2495, 224, False)
            self.spawn_goombas(2560, 96, False)
            self.is_mob_spawned[0] = True

        elif self.get_player().rect.x > 2460 and not self.is_mob_spawned[1]:
            self.spawn_goombas(3200, 352, False)
            self.spawn_koopa(3400, 352, False)
            self.spawn_goombas(3700, 352, False)
            self.spawn_goombas(4060, 352, False)
            self.spawn_goombas(4190, 352, False)
            self.is_mob_spawned[1] = True

    def player_death(self, core):
        self.in_event = True
        self.get_player().reset_jump()
        self.get_player().reset_move()
        self.get_player().numOfLives -= 1

        if self.get_player().numOfLives == 0:
            self.get_event().start_kill(core, game_over=True)
        else:
            self.get_event().start_kill(core, game_over=False)

    def player_win(self, core):
        self.in_event = True
        self.get_player().reset_jump()
        self.get_player().reset_move()
        self.get_event().start_win(core)

    def update(self, core):

        # All mobs
        self.update_entities(core)

        if not core.get_map().in_event:

            # When player eats a mushroom
            if self.get_player().inLevelUpAnimation:
                self.get_player().change_powerlvl_animation()

            # Unlike the level up animation, player can move there
            elif self.get_player().inLevelDownAnimation:
                self.get_player().change_powerlvl_animation()
                self.update_player(core)

            # Common case
            else:
                self.update_player(core)

        else:
            self.get_event().update(core)

        # Debris is 1) Particles which appears when player destroy a brick block
        # 2) Coins which appears when player activate a "question" platform
        for debris in self.debris:
            debris.update(core)

        # Player's fireballs
        for whizbang in self.projectiles:
            whizbang.update(core)

        # Text which represent how mapy points player get
        for text_object in self.text_objects:
            text_object.update(core)

        # Camera stops moving when player dies or touches a flag
        if not self.in_event:
            self.get_camera().update(core.get_map().get_player().rect)

        self.try_spawn_mobs(core)

        self.update_time(core)
        self.update_score_time()

    def render_map(self, core):
        """

        Rendering only tiles. It's used in main menu.

        """
        core.screen.blit(self.sky, (0, 0))

        for obj_group in (self.obj_bg, self.obj):
            for obj in obj_group:
                obj.render(core)

        for tube in self.tubes:
            tube.render(core)

    def render(self, core):
        """

        Renders every object.

        """
        core.screen.blit(self.sky, (0, 0))

        for obj in self.obj_bg:
            obj.render(core)

        for mob in self.mobs:
            mob.render(core)

        for obj in self.obj:
            obj.render(core)

        for tube in self.tubes:
            tube.render(core)

        for whizbang in self.projectiles:
            whizbang.render(core)

        for debris in self.debris:
            debris.render(core)

        self.flag.render(core)

        for text_object in self.text_objects:
            text_object.render_in_game(core)

        self.get_player().render(core)

        self.get_ui().render(core)
