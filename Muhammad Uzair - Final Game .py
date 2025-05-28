import pygame
import random
import math

pygame.init()
WIDTH, HEIGHT = 800, 480
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Quantum Pong with Gate Power-Ups")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 24)
small_font = pygame.font.SysFont("Arial", 16)

# Colors
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
BLUE, CYAN = (0, 102, 255), (0, 255, 255)
RED, YELLOW, GREEN = (255, 0, 0), (255, 255, 0), (0, 255, 0)
PURPLE, ORANGE = (128, 0, 128), (255, 165, 0)
DARK_BLUE = (0, 20, 40)
NEON_CYAN = (0, 255, 255)
NEON_PINK = (255, 20, 147)

# Constants
BALL_RADIUS, PADDLE_WIDTH, PADDLE_HEIGHT = 10, 10, 80
BASE_SPEED = 7
MAX_SPEED = 12
JERK_SPEED = 16
JERK_DURATION = 20
SPEED_INCREMENT = 0.5
DELAY_FRAMES = 60
Z_NOISE_INTERVAL = 240
GATE_DROP_INTERVAL = 240
MEASUREMENT_TIMEOUT = 360
GATE_TYPES = ['X', 'Z', 'H']

# Game objects
player = pygame.Rect(20, HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
opponent = pygame.Rect(WIDTH - 30, HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
ball_0 = pygame.Rect(WIDTH // 2, HEIGHT // 3, BALL_RADIUS * 2, BALL_RADIUS * 2)
ball_1 = pygame.Rect(WIDTH // 2, 2 * HEIGHT // 3, BALL_RADIUS * 2, BALL_RADIUS * 2)

# Ball dynamics
ball_speed = BASE_SPEED
angle = random.uniform(-0.6, 0.6)
ball_dx = ball_speed * random.choice([-1, 1])
ball_dy = ball_speed * math.sin(angle)
ball_dy_1 = -ball_dy

# State variables
ball_state = "superposition"
state_label = "|+>"
ball_1_visible = False
delay_counter = 0
measurement_timer = 0
collapse_message = ""
player_score = 0
opponent_score = 0
has_collapsed = False
z_noise_timer = 0
jerk_timer = 0

# Visual effects
flash_opacity = 0
glow_on = False
glow_timer = 0

# Power-ups
powerups = pygame.sprite.Group()
powerup_timer = 0
powerup_message = ""
powerup_msg_timer = 0


# Enhanced Visual Effects
class Particle:
    def __init__(self, x, y, color=CYAN, lifetime=60):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = random.uniform(2, 6)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.98
        self.vy *= 0.98
        self.lifetime -= 1
        return self.lifetime > 0

    def draw(self, surface):
        if self.max_lifetime <= 0:
            return
        alpha = int(255 * max(0, min(1, self.lifetime / self.max_lifetime)))
        color_with_alpha = (*self.color[:3], alpha)
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, color_with_alpha, (self.size, self.size), self.size)
        surface.blit(s, (self.x - self.size, self.y - self.size))


class Trail:
    def __init__(self, max_length=8):
        self.positions = []
        self.max_length = max_length

    def add_position(self, x, y):
        self.positions.append((x, y))
        if len(self.positions) > self.max_length:
            self.positions.pop(0)

    def clear(self):
        """Clear all trail positions"""
        self.positions.clear()

    def draw(self, surface, color):
        for i, pos in enumerate(self.positions):
            if len(self.positions) > 0:
                alpha = int(255 * (i / len(self.positions)))
                size = int(BALL_RADIUS * (i / len(self.positions)))
                if size > 0:
                    s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    pygame.draw.circle(s, (*color[:3], alpha), (size, size), size)
                    surface.blit(s, (pos[0] - size, pos[1] - size))


# Visual effect objects
particles = []
ball_0_trail = Trail()
ball_1_trail = Trail()
background_particles = []

# Initialize background particles (reduced for performance)
for _ in range(20):  # Reduced from 50 to 20
    background_particles.append(Particle(
        random.randint(0, WIDTH),
        random.randint(0, HEIGHT),
        color=(random.randint(20, 80), random.randint(20, 80), random.randint(100, 255)),
        lifetime=1000  # Use a large finite number instead of infinity
    ))


class PowerUp(pygame.sprite.Sprite):
    def __init__(self, gate_type):
        super().__init__()
        self.gate = gate_type
        self.surf = pygame.Surface((48, 48), pygame.SRCALPHA)

        # Enhanced power-up visuals
        colors = {'X': (255, 100, 100), 'Z': (255, 255, 100), 'H': (100, 255, 100)}
        color = colors[gate_type]

        # Draw glowing border
        pygame.draw.rect(self.surf, color, (0, 0, 48, 48), 3)
        pygame.draw.rect(self.surf, (*color, 100), (3, 3, 42, 42))

        self.rect = self.surf.get_rect(center=(random.randint(100, WIDTH - 100), -20))
        self.text = font.render(gate_type, True, BLACK)
        self.glow_timer = 0
        self.original_y = self.rect.y

    def update(self):
        self.rect.y += 3
        self.glow_timer += 0.2

        # Floating effect
        self.rect.y = self.original_y + int(math.sin(self.glow_timer) * 3)
        self.original_y += 3

        if self.rect.top > HEIGHT:
            self.kill()


def create_explosion(x, y, color=NEON_CYAN, count=8):  # Reduced from 15 to 8
    for _ in range(count):
        particles.append(Particle(x, y, color, random.randint(20, 40)))  # Shorter lifetime


def draw_gradient_background():
    # Simplified gradient - draw fewer lines for better performance
    for y in range(0, HEIGHT, 4):  # Skip every 4th line
        color_ratio = y / HEIGHT
        r = int(DARK_BLUE[0] * (1 - color_ratio))
        g = int(DARK_BLUE[1] * (1 - color_ratio))
        b = int(DARK_BLUE[2] + (100 * color_ratio))
        pygame.draw.rect(screen, (r, g, b), (0, y, WIDTH, 4))


def draw_enhanced_paddle(paddle_rect, is_player=True):
    # Main paddle body
    color = NEON_CYAN if is_player else NEON_PINK
    pygame.draw.rect(screen, color, paddle_rect)

    # Glow effect
    glow_rect = paddle_rect.inflate(6, 6)
    s = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color[:3], 50), (0, 0, glow_rect.width, glow_rect.height))
    screen.blit(s, glow_rect.topleft)

    # Energy core
    core_rect = pygame.Rect(paddle_rect.centerx - 2, paddle_rect.centery - 10, 4, 20)
    pygame.draw.rect(screen, WHITE, core_rect)


def draw_quantum_ball(ball_rect, state, is_ball_1=False):
    center_x, center_y = ball_rect.center

    if state == "superposition":
        # Simplified quantum superposition visual
        colors = [NEON_CYAN, NEON_PINK] if not is_ball_1 else [NEON_PINK, NEON_CYAN]

        # Reduced glow layers for performance
        for i in range(2):  # Reduced from 5 to 2
            alpha = 80 - i * 30
            radius = BALL_RADIUS + i * 4
            s = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*colors[0][:3], alpha), (radius * 2, radius * 2), radius)
            screen.blit(s, (center_x - radius * 2, center_y - radius * 2))

        # Core
        pygame.draw.circle(screen, colors[0], (center_x, center_y), BALL_RADIUS)
        pygame.draw.circle(screen, colors[1], (center_x, center_y), BALL_RADIUS - 3)

        # Simplified quantum pattern - only 1 dot instead of 3
        angle = (pygame.time.get_ticks() * 0.01) % (2 * math.pi)
        px = center_x + math.cos(angle) * (BALL_RADIUS - 2)
        py = center_y + math.sin(angle) * (BALL_RADIUS - 2)
        pygame.draw.circle(screen, WHITE, (int(px), int(py)), 2)
    else:
        # Classical state
        color = BLUE if state == "0" else RED
        pygame.draw.circle(screen, color, (center_x, center_y), BALL_RADIUS)
        pygame.draw.circle(screen, WHITE, (center_x, center_y), BALL_RADIUS - 3)

        # State indicator
        text = small_font.render(state, True, WHITE)
        screen.blit(text, (center_x - 5, center_y - 8))


def draw_hud():
    # Background for HUD
    hud_surface = pygame.Surface((WIDTH, 80), pygame.SRCALPHA)
    pygame.draw.rect(hud_surface, (0, 0, 0, 150), (0, 0, WIDTH, 80))
    screen.blit(hud_surface, (0, 0))

    # Score with glow effect
    score_text = font.render(f"Player: {player_score}  Opponent: {opponent_score}", True, WHITE)
    screen.blit(score_text, (WIDTH // 2 - 100, 10))

    # Quantum state with enhanced styling
    state_bg = pygame.Surface((140, 30), pygame.SRCALPHA)
    pygame.draw.rect(state_bg, (0, 255, 255, 50), (0, 0, 140, 30))
    screen.blit(state_bg, (WIDTH - 150, 5))

    state_text = font.render(f"State: {state_label}", True, NEON_CYAN)
    screen.blit(state_text, (WIDTH - 145, 10))

    # Controls hint
    controls_text = small_font.render("Controls: ↑↓ Move | X Z H Gates", True, (150, 150, 150))
    screen.blit(controls_text, (10, HEIGHT - 25))


def reset_round():
    global ball_state, state_label, ball_dx, ball_dy, ball_dy_1, ball_speed
    global ball_1_visible, delay_counter, measurement_timer, collapse_message
    global has_collapsed, z_noise_timer, jerk_timer

    ball_state = "superposition"
    state_label = "|+>"
    ball_0.topleft = (WIDTH // 2, HEIGHT // 3)
    ball_1.topleft = (WIDTH // 2, 2 * HEIGHT // 3)

    angle = random.uniform(-0.6, 0.6)
    ball_speed = BASE_SPEED
    ball_dx = ball_speed * random.choice([-1, 1])
    ball_dy = ball_speed * math.sin(angle)
    ball_dy_1 = -ball_dy

    ball_1_visible = False
    delay_counter = 0
    measurement_timer = 0
    collapse_message = ""
    has_collapsed = False
    z_noise_timer = 0
    jerk_timer = 0
    powerups.empty()

    # Clear trails
    ball_0_trail.clear()
    ball_1_trail.clear()


def apply_hadamard(source="manual"):
    global ball_state, state_label, ball_1_visible, delay_counter
    global measurement_timer, has_collapsed, ball_dy_1
    current_pos = ball_1.topleft if ball_state == "1" else ball_0.topleft
    ball_state = "superposition"
    state_label = "|+>"
    ball_0.topleft = current_pos

    offset_x = 40 if current_pos[0] < WIDTH // 2 else -40
    offset_y = 30 if current_pos[1] < HEIGHT // 2 else -30
    ball_1.topleft = (
        max(0, min(WIDTH - BALL_RADIUS * 2, current_pos[0] + offset_x)),
        max(0, min(HEIGHT - BALL_RADIUS * 2, current_pos[1] + offset_y))
    )

    ball_dy_1 = -ball_dy
    ball_1_visible = True
    delay_counter = DELAY_FRAMES
    measurement_timer = 0
    has_collapsed = False

    # Clear trails when transitioning to superposition
    ball_0_trail.clear()
    ball_1_trail.clear()

    # Visual effects
    create_explosion(current_pos[0], current_pos[1], GREEN, 20)

    print(f"H gate applied ({source}): Ball_0={ball_0.topleft}, Ball_1={ball_1.topleft}")


def apply_x(source="manual"):
    global ball_state, state_label, ball_dx, jerk_timer
    if ball_state == "0":
        ball_state = "1"
        ball_1.topleft = ball_0.topleft
        # Clear the old trail and start fresh for state 1
        ball_0_trail.clear()
        ball_1_trail.clear()
        create_explosion(ball_0.centerx, ball_0.centery, RED, 15)
    elif ball_state == "1":
        ball_state = "0"
        ball_0.topleft = ball_1.topleft
        # Clear the old trail and start fresh for state 0
        ball_0_trail.clear()
        ball_1_trail.clear()
        create_explosion(ball_1.centerx, ball_1.centery, RED, 15)
    ball_dx *= -1  # Flip direction on state change
    jerk_timer = JERK_DURATION  # Apply speed jerk
    state_label = f"|{ball_state}>"
    print(f"X gate ({source}): switched to state {ball_state}")


def check_powerup_collision(ball_rect):
    global ball_state, state_label, powerup_message, powerup_msg_timer, ball_dy
    for pu in powerups:
        if ball_rect.colliderect(pu.rect.inflate(10, 10)):
            create_explosion(pu.rect.centerx, pu.rect.centery, YELLOW, 10)
            if pu.gate == 'X' and ball_state in ['0', '1']:
                apply_x(source="powerup")
                powerup_message = "X-gate applied (Power-Up)"
            elif pu.gate == 'Z' and ball_state == 'superposition':
                ball_dy *= -1
                powerup_message = "Z-gate applied (Power-Up)"
            elif pu.gate == 'H':
                apply_hadamard(source="powerup")
                powerup_message = "H-gate applied (Power-Up)"
            pu.kill()
            powerup_msg_timer = pygame.time.get_ticks()


# Game loop
running = True
while running:
    # Enhanced background
    draw_gradient_background()

    # Update background particles
    for particle in background_particles[:]:  # Create a copy to iterate over
        if not particle.update():
            # Respawn background particle
            background_particles.remove(particle)
            background_particles.append(Particle(
                random.randint(0, WIDTH),
                random.randint(0, HEIGHT),
                color=(random.randint(20, 80), random.randint(20, 80), random.randint(100, 255)),
                lifetime=1000
            ))
        particle.draw(screen)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_UP] and player.top > 0:
        player.move_ip(0, -6)
    if keys[pygame.K_DOWN] and player.bottom < HEIGHT:
        player.move_ip(0, 6)
    if keys[pygame.K_x] and ball_state in ["0", "1"]:
        apply_x(source="manual")
        powerup_message = "X-gate manually applied"
        powerup_msg_timer = pygame.time.get_ticks()
    if keys[pygame.K_z] and ball_state == "superposition":
        ball_dy *= -1
        powerup_message = "Z-gate manually applied"
        powerup_msg_timer = pygame.time.get_ticks()
    if keys[pygame.K_h]:
        apply_hadamard(source="manual")
        powerup_message = "H-gate manually applied"
        powerup_msg_timer = pygame.time.get_ticks()

    # Opponent AI tracks the active ball
    active_ball = ball_0 if ball_state != "1" else ball_1
    if opponent.centery < active_ball.centery and opponent.bottom < HEIGHT:
        opponent.move_ip(0, 4)
    elif opponent.centery > active_ball.centery and opponent.top > 0:
        opponent.move_ip(0, -4)

    # Spawn and update powerups
    powerup_timer += 1
    if powerup_timer > GATE_DROP_INTERVAL:
        powerups.add(PowerUp(random.choice(GATE_TYPES)))
        powerup_timer = 0
    powerups.update()

    # Ball movement and quantum logic
    if ball_state == "superposition":
        ball_0.x += ball_dx
        ball_0.y += ball_dy
        ball_0_trail.add_position(ball_0.centerx, ball_0.centery)

        if ball_0.top <= 0 or ball_0.bottom >= HEIGHT:
            ball_dy *= -1
            create_explosion(ball_0.centerx, ball_0.centery, CYAN, 8)
        if ball_0.colliderect(player) or ball_0.colliderect(opponent):
            ball_dx *= -1
            create_explosion(ball_0.centerx, ball_0.centery, WHITE, 12)

        if ball_1_visible:
            ball_1.x += ball_dx
            ball_1.y += ball_dy_1
            ball_1_trail.add_position(ball_1.centerx, ball_1.centery)

            if ball_1.top <= 0 or ball_1.bottom >= HEIGHT:
                ball_dy_1 *= -1
                create_explosion(ball_1.centerx, ball_1.centery, CYAN, 8)
            if ball_1.colliderect(player) or ball_1.colliderect(opponent):
                ball_dx *= -1
                create_explosion(ball_1.centerx, ball_1.centery, WHITE, 12)
        else:
            delay_counter += 1
            if delay_counter > DELAY_FRAMES:
                ball_1_visible = True

        check_powerup_collision(ball_0)
        if ball_1_visible:
            check_powerup_collision(ball_1)

        measurement_timer += 1
        if player.colliderect(ball_0) or opponent.colliderect(ball_0):
            ball_state = "0"
            state_label = "|0>"
            collapse_message = "Measured: collapsed to |0>"
            has_collapsed = True
            flash_opacity = 255
            jerk_timer = JERK_DURATION
            ball_1_visible = False
            # Clear trail of the collapsed ball
            ball_1_trail.clear()
            create_explosion(ball_0.centerx, ball_0.centery, BLUE, 25)
        elif ball_1_visible and (player.colliderect(ball_1) or opponent.colliderect(ball_1)):
            ball_state = "1"
            state_label = "|1>"
            collapse_message = "Measured: collapsed to |1>"
            has_collapsed = True
            flash_opacity = 255
            jerk_timer = JERK_DURATION
            ball_0.topleft = ball_1.topleft
            ball_1_visible = False
            # Clear old trail and transfer to new state trail
            ball_0_trail.clear()
            create_explosion(ball_1.centerx, ball_1.centery, RED, 25)
        elif measurement_timer > MEASUREMENT_TIMEOUT:
            choice = random.choice(["0", "1"])
            ball_state = choice
            state_label = f"|{choice}>"
            collapse_message = f"Auto-measured: collapsed to |{choice}>"
            has_collapsed = True
            flash_opacity = 255
            jerk_timer = JERK_DURATION
            if choice == "1":
                ball_0.topleft = ball_1.topleft
                ball_0_trail.clear()
            else:
                ball_1_trail.clear()
            ball_1_visible = False
            create_explosion(ball_0.centerx, ball_0.centery, PURPLE, 20)

    else:
        # Classical state - single ball
        active_ball = ball_0 if ball_state == "0" else ball_1
        active_ball.x += ball_dx
        active_ball.y += ball_dy

        # Add to appropriate trail based on current state
        if ball_state == "0":
            ball_0_trail.add_position(active_ball.centerx, active_ball.centery)
        else:  # ball_state == "1"
            ball_1_trail.add_position(active_ball.centerx, active_ball.centery)

        check_powerup_collision(active_ball)

        if active_ball.top <= 0 or active_ball.bottom >= HEIGHT:
            ball_dy *= -1
            create_explosion(active_ball.centerx, active_ball.centery, WHITE, 8)
        if active_ball.colliderect(player) or active_ball.colliderect(opponent):
            ball_dx *= -1
            create_explosion(active_ball.centerx, active_ball.centery, YELLOW, 12)

        if jerk_timer > 0:
            current_speed = JERK_SPEED
            jerk_timer -= 1
        else:
            current_speed = BASE_SPEED
        ball_speed = max(BASE_SPEED, min(ball_speed, MAX_SPEED))

        # Normalize dx, dy with current speed
        angle = math.atan2(ball_dy, ball_dx)
        ball_dx = current_speed * math.cos(angle)
        ball_dy = current_speed * math.sin(angle)

        z_noise_timer += 1
        if z_noise_timer > Z_NOISE_INTERVAL:
            if random.random() < 0.3:
                ball_dy *= -1
                collapse_message = "Z-noise: vertical flip!"
                create_explosion(active_ball.centerx, active_ball.centery, PURPLE, 15)
            z_noise_timer = 0

        if active_ball.right >= WIDTH:
            player_score += 1
            collapse_message = "You scored!"
            create_explosion(WIDTH - 50, active_ball.centery, GREEN, 30)
            pygame.time.wait(1000)
            reset_round()
        elif active_ball.left <= 0:
            opponent_score += 1
            collapse_message = "You missed!"
            create_explosion(50, active_ball.centery, RED, 30)
            pygame.time.wait(1000)
            reset_round()

    # Draw trails - only draw the trail for the currently active state
    if ball_state == "superposition":
        ball_0_trail.draw(screen, NEON_CYAN)
        if ball_1_visible:
            ball_1_trail.draw(screen, NEON_PINK)
    elif ball_state == "0":
        ball_0_trail.draw(screen, BLUE)
    elif ball_state == "1":
        ball_1_trail.draw(screen, RED)

    # Draw enhanced paddles
    draw_enhanced_paddle(player, True)
    draw_enhanced_paddle(opponent, False)

    # Draw quantum balls
    if ball_state == "superposition":
        draw_quantum_ball(ball_0, ball_state)
        if ball_1_visible:
            draw_quantum_ball(ball_1, ball_state, True)
    else:
        active_ball = ball_0 if ball_state == "0" else ball_1
        draw_quantum_ball(active_ball, ball_state)

    # Draw power-ups with enhanced effects
    for pu in powerups:
        # Glow effect for power-ups
        glow_surface = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.rect(glow_surface, (255, 255, 255, 30), (6, 6, 48, 48))
        screen.blit(glow_surface, (pu.rect.x - 6, pu.rect.y - 6))

        screen.blit(pu.surf, pu.rect)
        screen.blit(pu.text, pu.rect.move(16, 14))

    # Update and draw particles (limit particle count for performance)
    particles = [p for p in particles if p.update()]
    if len(particles) > 100:  # Limit max particles
        particles = particles[-100:]
    for particle in particles:
        particle.draw(screen)

    # Draw white flash effect on collapse
    if flash_opacity > 0:
        flash_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        flash_surface.fill((255, 255, 255, flash_opacity))
        screen.blit(flash_surface, (0, 0))
        flash_opacity = max(0, flash_opacity - 10)

    # Enhanced HUD
    draw_hud()

    # Messages with enhanced styling
    if collapse_message:
        msg_surface = pygame.Surface((400, 40), pygame.SRCALPHA)
        pygame.draw.rect(msg_surface, (0, 0, 0, 150), (0, 0, 400, 40))
        screen.blit(msg_surface, (WIDTH // 2 - 200, 35))

        msg_text = font.render(collapse_message, True, WHITE)
        screen.blit(msg_text, (WIDTH // 2 - msg_text.get_width() // 2, 45))

    if powerup_message and pygame.time.get_ticks() - powerup_msg_timer < 2000:
        msg_bg = pygame.Surface((300, 30), pygame.SRCALPHA)
        pygame.draw.rect(msg_bg, (255, 255, 0, 100), (0, 0, 300, 30))
        screen.blit(msg_bg, (WIDTH // 2 - 150, HEIGHT - 50))

        pu_text = font.render(powerup_message, True, BLACK)
        screen.blit(pu_text, (WIDTH // 2 - pu_text.get_width() // 2, HEIGHT - 45))

    # Refresh screen
    pygame.display.flip()
    clock.tick(60)

pygame.quit()