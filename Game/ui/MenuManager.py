import pygame as pg
from ui.LoadingMenu import LoadingMenu
from ui.MainMenu import MainMenu

class MenuManager(object):
    """

    Questa classe gestisce i menu del gioco, come il menu principale e il menu di caricamento. 
    Si occupa di aggiornare e renderizzare i menu in base allo stato attuale del gioco.

    """
    def __init__(self, core):

        self.currentGameState = 'MainMenu'

        self.oMainMenu = MainMenu()
        self.oLoadingMenu = LoadingMenu(core)

    def update(self, core):
        if self.currentGameState == 'MainMenu':
            pass

        elif self.currentGameState == 'Loading':
            self.oLoadingMenu.update(core)

        elif self.currentGameState == 'Game':
            core.get_map().update(core)

    def render(self, core):
        if self.currentGameState == 'MainMenu':
            core.get_map().render_map(core)
            self.oMainMenu.render(core)

        elif self.currentGameState == 'Loading':
            self.oLoadingMenu.render(core)

        elif self.currentGameState == 'Game':
            core.get_map().render(core)
            core.get_map().get_ui().render(core)
            if getattr(core, 'is_paused', False):
                core.pause_text.render(core)

        pg.display.update()

    def start_loading(self):
            # Inizia il processo di caricamento del gioco, passando dallo stato del menu principale allo stato di caricamento.
            self.currentGameState = 'Loading'
            self.oLoadingMenu.update_time()
