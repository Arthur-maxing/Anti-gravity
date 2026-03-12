import asyncio
from pyodide.ffi import create_proxy
from js import document, window, Image, requestAnimationFrame

# Game Constants
CANVAS_WIDTH = 960
CANVAS_HEIGHT = 540
TILE_SIZE = 40

# Tile Types
EMPTY = 0
BLOCK = 1
FRAGILE = 2 # Only Bould can break
SPIKE = 3   # Danger (Reset character)
WIN = 4      # Goal

class Character:
    def __init__(self, name, x, y, sprite_path):
        self.name = name
        self.spawn_x = x
        self.spawn_y = y
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.width = 32
        self.height = 48
        self.on_ground = False
        
        # Physics Defaults
        self.gravity = 0.5
        self.jump_force = -10
        self.speed = 5
        self.double_jump_ready = False
        
        # Load Sprite
        self.sprite = Image.new()
        self.sprite.src = sprite_path
        self.loaded = False
        
        def on_load(e):
            self.loaded = True
        
        self.sprite.onload = create_proxy(on_load)

    def reset(self):
        self.x = self.spawn_x
        self.y = self.spawn_y
        self.vx = 0
        self.vy = 0

class Aero(Character):
    def __init__(self, x, y):
        super().__init__("Aero", x, y, "./assets/aero.png")
        self.gravity = 0.3  # Low gravity
        self.jump_force = -9
        self.speed = 4
        self.can_double_jump = True

class Bould(Character):
    def __init__(self, x, y):
        super().__init__("Bould", x, y, "./assets/bould.png")
        self.gravity = 1.0  # Heavy
        self.jump_force = -11
        self.speed = 6
        self.is_heavy = True

class Flux(Character):
    def __init__(self, x, y):
        super().__init__("Flux", x, y, "./assets/flux.png")
        self.gravity = 0.6
        self.energy = 100
        self.is_inverted = False

class Game:
    def __init__(self):
        self.canvas = document.getElementById("game-canvas")
        self.ctx = self.canvas.getContext("2d")
        
        # Level data - Expanded for Phase 1, 2, 3
        # 1 = Wall, 2 = Fragile, 3 = Spike, 4 = Win
        self.map = [
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,0,0,0,0,0,0,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,0,1],
            [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1],
            [1,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,1,1,1,1],
            [1,1,1,0,0,0,0,1,1,1,1,1,1,2,2,1,0,0,0,0,1,1,1,1],
            [1,0,0,0,0,0,0,0,0,0,1,1,1,2,2,1,0,0,0,0,1,1,1,1],
            [1,0,0,0,0,1,1,0,0,0,1,1,1,2,2,1,0,0,0,0,1,1,1,1],
            [1,0,0,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1],
            [1,0,3,3,3,3,3,3,0,0,0,0,0,0,0,0,0,0,0,0,1,1,1,1],
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
        ]
        
        self.characters = [
            Aero(60, 400),
            Bould(60, 400),
            Flux(60, 400)
        ]
        self.active_index = 0
        self.keys = {}
        self.win_state = False
        
        # Audio icon setup
        self.bg_img = Image.new()
        self.bg_img.src = "./assets/background.png"
        
        # Register inputs
        window.addEventListener("keydown", create_proxy(self.on_keydown))
        window.addEventListener("keyup", create_proxy(self.on_keyup))
        
        # Start display
        document.getElementById("loading-screen").style.display = "none"

    def active_char(self):
        return self.characters[self.active_index]

    def on_keydown(self, e):
        self.keys[e.code] = True
        if e.code == "Digit1": self.switch_char(0)
        if e.code == "Digit2": self.switch_char(1)
        if e.code == "Digit3": self.switch_char(2)
        
        if e.code in ["ArrowUp", "KeyW", "Space"]:
            char = self.active_char()
            if char.on_ground:
                char.vy = char.jump_force
                char.on_ground = False
                if char.name == "Aero": char.double_jump_ready = True
            elif char.name == "Aero" and char.double_jump_ready:
                char.vy = char.jump_force * 0.9
                char.double_jump_ready = False

    def on_keyup(self, e):
        self.keys[e.code] = False

    def switch_char(self, index):
        prev_char = self.active_char()
        new_char = self.characters[index]
        new_char.x = prev_char.x
        new_char.y = prev_char.y
        new_char.vx = prev_char.vx
        new_char.vy = prev_char.vy
        self.active_index = index
        
        # Update UI
        for i in range(1, 4):
            document.getElementById(f"icon-{i}").classList.remove("active")
        document.getElementById(f"icon-{index+1}").classList.add("active")
        
        ability_text = {0: "AERO: PLANAGEM", 1: "BOULD: PESADO", 2: "FLUX: ANTIGRAV"}[index]
        document.getElementById("ability-name").innerText = ability_text

    def update(self):
        if self.win_state: return
        
        char = self.active_char()
        
        # Horizontal Movement
        if self.keys.get("ArrowLeft") or self.keys.get("KeyA"):
            char.vx = -char.speed
        elif self.keys.get("ArrowRight") or self.keys.get("KeyD"):
            char.vx = char.speed
        else:
            char.vx *= 0.7 # Low friction for better control
            if abs(char.vx) < 0.1: char.vx = 0
            
        # Flux Gravity Inversion
        is_flux = char.name == "Flux"
        if is_flux and self.keys.get("KeyF") and char.energy > 0:
            char.is_inverted = True
            char.energy -= 1.5
            current_gravity = -char.gravity
        else:
            char.is_inverted = False
            if is_flux: char.energy = min(100, char.energy + 0.3)
            current_gravity = char.gravity

        # Apply Physics
        char.vy += current_gravity
        
        # Limit terminal velocity
        if char.vy > 15: char.vy = 15
        if char.vy < -15: char.vy = -15

        char.x += char.vx
        self.check_collisions(char, True) # X axis
        
        char.y += char.vy
        self.check_collisions(char, False) # Y axis
        
        # HUD Updates
        energy_fill = document.getElementById("energy-fill")
        if is_flux:
            energy_fill.style.width = f"{char.energy}%"
            energy_fill.style.background = "var(--primary-purple)"
        else:
            energy_fill.style.width = "100%"
            energy_fill.style.background = "var(--primary-blue)" if char.name == "Aero" else "var(--primary-orange)"

    def check_collisions(self, char, is_x):
        # Grid boundaries
        grid_x1 = int(char.x // TILE_SIZE)
        grid_x2 = int((char.x + char.width) // TILE_SIZE)
        grid_y1 = int(char.y // TILE_SIZE)
        grid_y2 = int((char.y + char.height) // TILE_SIZE)
        
        char.on_ground = False
        
        for r in range(grid_y1, grid_y2 + 1):
            for c in range(grid_x1, grid_x2 + 1):
                if 0 <= r < len(self.map) and 0 <= c < len(self.map[0]):
                    tile = self.map[r][c]
                    if tile == EMPTY: continue
                    
                    tx = c * TILE_SIZE
                    ty = r * TILE_SIZE
                    
                    # Basic AABB
                    if (char.x < tx + TILE_SIZE and
                        char.x + char.width > tx and
                        char.y < ty + TILE_SIZE and
                        char.y + char.height > ty):
                        
                        if tile == WIN:
                            self.win_state = True
                            window.alert("MISSÃO CUMPRIDA! Trindade sincronizada.")
                            return

                        if tile == SPIKE:
                            char.reset()
                            return

                        if tile == BLOCK or tile == FRAGILE:
                            if is_x:
                                if char.vx > 0: # Moving right
                                    char.x = tx - char.width
                                elif char.vx < 0: # Moving left
                                    char.x = tx + TILE_SIZE
                                char.vx = 0
                            else:
                                if char.vy > 0: # Falling
                                    char.y = ty - char.height
                                    char.vy = 0
                                    char.on_ground = True
                                    if tile == FRAGILE and char.name == "Bould" and char.vy > 2:
                                         self.map[r][c] = EMPTY
                                elif char.vy < 0: # Jumping
                                    char.y = ty + TILE_SIZE
                                    char.vy = 0
                                    
                                # Special for Bould: smash blocks if falling fast
                                if tile == FRAGILE and char.name == "Bould":
                                    self.map[r][c] = EMPTY

    def draw(self):
        self.ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
        
        # Draw Map
        for r in range(len(self.map)):
            for c in range(len(self.map[0])):
                tile = self.map[r][c]
                if tile == BLOCK:
                    self.ctx.fillStyle = "rgba(20, 20, 30, 0.9)"
                    self.ctx.fillRect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    self.ctx.strokeStyle = "rgba(0, 210, 255, 0.2)"
                    self.ctx.strokeRect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                elif tile == FRAGILE:
                    self.ctx.fillStyle = "rgba(100, 60, 20, 0.7)"
                    self.ctx.fillRect(c * TILE_SIZE + 4, r * TILE_SIZE + 4, TILE_SIZE - 8, TILE_SIZE - 8)
                    self.ctx.strokeStyle = "rgba(255, 140, 0, 0.5)"
                    self.ctx.strokeRect(c * TILE_SIZE, r * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                elif tile == SPIKE:
                    self.ctx.fillStyle = "#ff4b2b"
                    self.ctx.beginPath()
                    self.ctx.moveTo(c * TILE_SIZE, (r + 1) * TILE_SIZE)
                    self.ctx.lineTo(c * TILE_SIZE + TILE_SIZE/2, r * TILE_SIZE)
                    self.ctx.lineTo((c + 1) * TILE_SIZE, (r + 1) * TILE_SIZE)
                    self.ctx.fill()
                elif tile == WIN:
                    # Pulsing glow for the goal
                    glow = (window.performance.now() % 1000) / 1000
                    self.ctx.shadowBlur = 10 + 10 * glow
                    self.ctx.shadowColor = "rgba(146, 70, 255, 0.8)"
                    self.ctx.fillStyle = "white"
                    self.ctx.beginPath()
                    self.ctx.arc(c * TILE_SIZE + TILE_SIZE/2, r * TILE_SIZE + TILE_SIZE/2, TILE_SIZE/3, 0, 6.28)
                    self.ctx.fill()
                    self.ctx.shadowBlur = 0

        # Draw Active Character
        char = self.active_char()
        if char.loaded:
            if char.name == "Flux" and char.is_inverted:
                self.ctx.save()
                self.ctx.translate(char.x + char.width/2, char.y + char.height/2)
                self.ctx.scale(1, -1)
                self.ctx.drawImage(char.sprite, -char.width/2, -char.height/2, char.width, char.height)
                self.ctx.restore()
            else:
                self.ctx.drawImage(char.sprite, char.x, char.y, char.width, char.height)
        else:
            self.ctx.fillStyle = "white"
            self.ctx.fillRect(char.x, char.y, char.width, char.height)

async def main():
    game = Game()
    
    def loop(time):
        game.update()
        game.draw()
        requestAnimationFrame(create_proxy(loop))
    
    requestAnimationFrame(create_proxy(loop))

asyncio.ensure_future(main())
