from os import environ

import pygame as pg
from pygame.locals import *

from core.Const import *
from core.Map import Map
from core.Camera import Camera
from core.Sound import Sound
from core.Event import Event
from ui.MenuManager import MenuManager


class Core(object):
    """

    Main class.

    """
    def __init__(self, coda_ai = None):
        environ['SDL_VIDEO_CENTERED'] = '1'
        pg.mixer.pre_init(44100, -16, 2, 1024)
        pg.init()
        pg.display.set_caption('SuperVisionBros')
        pg.display.set_mode((WINDOW_W, WINDOW_H))

        self.screen = pg.display.set_mode((WINDOW_W, WINDOW_H))
        self.clock = pg.time.Clock()

        self.oWorld = Map('1-1')
        self.oSound = Sound()
        self.oMM = MenuManager(self)

        self.run = True
        self.keyR = False
        self.keyL = False
        self.keyU = False
        self.keyD = False
        self.keyShift = False
        
        self.coda_ai = coda_ai
        self.timer_salto_in_alto = 0

    def main_loop(self):
        while self.run:
            self.input()
            self.update()
            self.render()
            self.clock.tick(FPS)

    def input(self):
        if self.get_mm().currentGameState == 'Game':
            self.input_player()
        else:
            self.input_menu()

    def input_player(self):
        for e in pg.event.get():

            if e.type == pg.QUIT:
                self.run = False

            elif e.type == KEYDOWN:
                if e.key == K_RIGHT:
                    self.keyR = True
                elif e.key == K_LEFT:
                    self.keyL = True
                elif e.key == K_DOWN:
                    self.keyD = True
                elif e.key == K_UP:
                    self.keyU = True
                elif e.key == K_LSHIFT:
                    self.keyShift = True

            elif e.type == KEYUP:
                if e.key == K_RIGHT:
                    self.keyR = False
                elif e.key == K_LEFT:
                    self.keyL = False
                elif e.key == K_DOWN:
                    self.keyD = False
                elif e.key == K_UP:
                    self.keyU = False
                elif e.key == K_LSHIFT:
                    self.keyShift = False
                    
        if self.coda_ai is not None:
            # Svuotiamo la coda per leggere i comandi
            while not self.coda_ai.empty():
                comando = self.coda_ai.get()
                
                # Movimento X
                if comando == "SINISTRA":
                    self.keyL = True
                    self.keyR = False
                elif comando == "DESTRA":
                    self.keyR = True
                    self.keyL = False
                elif comando == "FERMO_X":
                    self.keyR = False
                    self.keyL = False
                
                # Salto (Simuliamo la pressione veloce)
                elif comando == "SALTO":
                    self.keyU = True 
                    # Per il salto, bisogna dover resettare il tasto nel frame successivo
                    # altrimenti Mario continuerà a saltare all'infinito.
                    self.timer_salto_in_alto = pg.time.get_ticks()
                
                # Sprint
                elif comando == "SPRINT":
                    self.keyShift = True
                elif comando == "CAMMINA":
                    self.keyShift = False

    def input_menu(self):
        for e in pg.event.get():
            if e.type == pg.QUIT:
                self.run = False

            elif e.type == KEYDOWN:
                if e.key == K_RETURN:
                    self.get_mm().start_loading()

    def update(self):
        self.get_mm().update(self)
        # --- GESTIONE SALTO CV ---
        # Se il timer è partito (maggiore di 0), calcoliamo quanto tempo è passato
        if self.timer_salto_in_alto > 0:
            tempo_passato = pg.time.get_ticks() - self.timer_salto_in_alto
            
            # Se sono passati 300 millisecondi, "rilasciamo" il pulsante
            if tempo_passato > 300: 
                self.keyU = False
                self.timer_salto_in_alto = 0 # Resettiamo il cronometro

    def render(self):
        self.get_mm().render(self)

    def get_map(self):
        return self.oWorld

    def get_mm(self):
        return self.oMM

    def get_sound(self):
        return self.oSound
