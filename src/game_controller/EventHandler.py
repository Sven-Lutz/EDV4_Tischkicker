import logging
import numpy as np


class EventHandler:
    """Verarbeitet Events wie Tastatur-Eingaben, Tore und Spielende."""
    
    def __init__(self, game_controller):
        """
        :param game_controller: Referenz auf die GameController-Instanz
        """
        self.game_controller = game_controller
        logging.info("[EventHandler] Event-Handler initialisiert.")
    
    def on_goal(self, team: str, frame: np.ndarray = None) -> None:
        """
        Wird aufgerufen wenn ein Tor fällt.
        
        :param team: Name des Teams, das getroffen hat
        :param frame: Aktueller Frame (für Snapshot)
        """
        gc = self.game_controller
        print(f"[EventHandler] TOR für {team}! Neuer Stand: {gc.scoreboard.get_score_string()}")
        
        # Snapshot mit Trajektorie speichern
        if frame is not None:
            gc.snapshot_manager.save_snapshot(frame, team, gc.scoreboard)
    
    def on_game_over(self, winner: str) -> None:
        """
        Wird aufgerufen wenn ein Team gewonnen hat.
        
        :param winner: Name des Gewinnerteams
        """
        gc = self.game_controller
        print(f"\n[EventHandler] Spiel vorbei! Gewinner: {winner}")
        print(gc.statistics.summary(gc.scoreboard))
        gc.state = gc.STATE_FINISHED
    
    def handle_key_press(self, key: int) -> None:
        """
        Verarbeitet Tastatur-Eingaben.
        
        :param key: Gedrückte Taste (von cv2.waitKey())
        """
        gc = self.game_controller
        
        if key == ord('q'):
            print("[EventHandler] Beenden durch User.")
            gc.state = gc.STATE_FINISHED
        
        elif key == ord('p'):
            if gc.state == gc.STATE_RUNNING:
                gc.state = gc.STATE_PAUSED
                print("[EventHandler] Pausiert.")
            elif gc.state == gc.STATE_PAUSED:
                gc.state = gc.STATE_RUNNING
                print("[EventHandler] Fortgesetzt.")
        
        elif key == ord('r'):
            gc.scoreboard.reset()
            gc.statistics.reset()
            print("[EventHandler] Spielstand und Statistiken zurückgesetzt.")
