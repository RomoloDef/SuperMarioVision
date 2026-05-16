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
    Main class del gioco.
    """
    def __init__(self, coda_ai=None):
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
        self.keyFire = False 
        
        self.coda_ai = coda_ai
        self.timer_salto_in_alto = 0
        self.timer_fuoco_ai = 0

    def main_loop(self):
        while self.run:
            self.input()
            self.update()
            self.render()
            self.clock.tick(FPS)

    def input(self):
        """
        Gestisce l'input globale (AI e Tastiera).
        """
        # 1. LETTURA CODA AI (Sempre attiva)
        if self.coda_ai is not None:
            while not self.coda_ai.empty():
                comando = self.coda_ai.get()
                
                # Comando universale: Avvio Gioco
                if comando == "AVVIA_GIOCO":
                    if self.get_mm().currentGameState != 'Game':
                        print(">>> AI: Avvio caricamento livello...")
                        self.get_mm().start_loading()
                
                # Comandi specifici per il gameplay (attivi solo se si sta giocando)
                elif self.get_mm().currentGameState == 'Game':
                    self.gestisci_comandi_gioco_ai(comando)

        # 2. SELEZIONE INPUT TASTIERA IN BASE ALLO STATO
        if self.get_mm().currentGameState == 'Game':
            self.input_player()
        else:
            self.input_menu()

    def gestisci_comandi_gioco_ai(self, comando):
        """
        Logica interna per i comandi AI durante la partita.
        """
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
        
        # Salto
        elif comando == "SALTO":
            self.keyU = True 
            self.timer_salto_in_alto = pg.time.get_ticks()
        
        # Sprint
        elif comando == "SPRINT":
            self.keyShift = True
        elif comando == "CAMMINA":
            self.keyShift = False

        # Fuoco
        elif comando == "FUOCO":
            self.keyFire = True
            self.timer_fuoco_ai = pg.time.get_ticks()

    def input_player(self):
        """
        Gestisce l'input della tastiera durante il gioco.
        """
        for e in pg.event.get():
            if e.type == pg.QUIT:
                self.run = False

            elif e.type == KEYDOWN:
                if e.key == K_RIGHT: self.keyR = True
                elif e.key == K_LEFT: self.keyL = True
                elif e.key == K_DOWN: self.keyD = True
                elif e.key == K_UP: self.keyU = True
                elif e.key == K_LSHIFT: self.keyShift = True
                elif e.key == K_SPACE: self.keyFire = True

            elif e.type == KEYUP:
                if e.key == K_RIGHT: self.keyR = False
                elif e.key == K_LEFT: self.keyL = False
                elif e.key == K_DOWN: self.keyD = False
                elif e.key == K_UP: self.keyU = False
                elif e.key == K_LSHIFT: self.keyShift = False
                elif e.key == K_SPACE: self.keyFire = False

    def input_menu(self):
        """
        Gestisce l'input della tastiera nel menù.
        """
        for e in pg.event.get():
            if e.type == pg.QUIT:
                self.run = False

            elif e.type == KEYDOWN:
                if e.key == K_RETURN:
                    self.get_mm().start_loading()

    def update(self):
        self.get_mm().update(self)
        
        # Gestione timer per rilascio automatico tasti AI
        current_time = pg.time.get_ticks()

        if self.timer_salto_in_alto > 0:
            if current_time - self.timer_salto_in_alto > 300: 
                self.keyU = False
                self.timer_salto_in_alto = 0

        if self.timer_fuoco_ai > 0:
            if current_time - self.timer_fuoco_ai > 200: 
                self.keyFire = False 
                self.timer_fuoco_ai = 0

    def render(self):
        self.get_mm().render(self)

    def get_map(self):
        return self.oWorld

    def get_mm(self):
        return self.oMM

    def get_sound(self):
        return self.oSound