import math
import random
import sys
import pygame

pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

# =========================
# 9-Ball Pro
# =========================
WIDTH, HEIGHT = 1100, 680
TABLE = pygame.Rect(55, 75, 990, 500)
PLAY = pygame.Rect(TABLE.left + 30, TABLE.top + 30, TABLE.width - 60, TABLE.height - 60)
BALL_R = 13
POCKET_R = 27
FPS = 120
FRICTION = 0.991
STOP_SPEED = 0.055
MAX_POWER = 17.0
MIN_SHOT = 0.25

WOOD = (94, 53, 25)
FELT = (17, 103, 57)
FELT2 = (13, 82, 44)
RAIL = (31, 31, 31)
GOLD = (225, 183, 74)
WHITE = (245, 245, 245)
TEXT = (235, 235, 235)
RED = (205, 38, 45)
YELLOW = (240, 200, 35)
BLUE = (38, 90, 205)
PURPLE = (120, 55, 165)
ORANGE = (235, 112, 25)
GREEN = (25, 135, 65)
MAROON = (125, 35, 38)

BALL_COLORS = {1:YELLOW,2:BLUE,3:RED,4:PURPLE,5:ORANGE,6:GREEN,7:MAROON,8:(18,18,18),9:YELLOW}
POCKETS = [
    (PLAY.left, PLAY.top), (PLAY.centerx, PLAY.top), (PLAY.right, PLAY.top),
    (PLAY.left, PLAY.bottom), (PLAY.centerx, PLAY.bottom), (PLAY.right, PLAY.bottom)
]

font = pygame.font.SysFont("Arial", 20, bold=True)
small = pygame.font.SysFont("Arial", 16)
small_bold = pygame.font.SysFont("Arial", 16, bold=True)
big = pygame.font.SysFont("Arial", 28, bold=True)


def clamp(v, a, b):
    return max(a, min(b, v))


def make_sound(freq, duration, decay):
    try:
        import numpy as np
        rate = 44100
        n = int(rate * duration)
        t = np.arange(n) / rate
        wave = np.sin(2 * np.pi * freq * t) * np.exp(-decay * t)
        arr = (wave * 22000).astype(np.int16)
        return pygame.sndarray.make_sound(np.column_stack((arr, arr)))
    except Exception:
        return None

HIT_SOUND = make_sound(650, .055, 65)
POCKET_SOUND = make_sound(150, .22, 15)


class Ball:
    def __init__(self, x, y, number=0, cue=False):
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.number = number
        self.cue = cue
        self.pocketed = False
        self.color = WHITE if cue else BALL_COLORS[number]

    @property
    def speed(self):
        return math.hypot(self.vx, self.vy)

    def update(self):
        if self.pocketed:
            return
        self.x += self.vx
        self.y += self.vy
        self.vx *= FRICTION
        self.vy *= FRICTION
        if self.speed < STOP_SPEED:
            self.vx = self.vy = 0

    def draw(self, surf):
        if self.pocketed:
            return
        p = (round(self.x), round(self.y))
        # shadow
        pygame.draw.circle(surf, (5, 30, 18), (p[0]+2, p[1]+3), BALL_R+1)
        pygame.draw.circle(surf, self.color, p, BALL_R)
        pygame.draw.circle(surf, (235,235,235), (p[0]-4,p[1]-5), 3)
        pygame.draw.circle(surf, (8,8,8), p, BALL_R, 1)
        if not self.cue:
            # stripes for 9-ball
            if self.number == 9:
                pygame.draw.circle(surf, WHITE, p, 7)
            elif self.number >= 1:
                pygame.draw.circle(surf, WHITE, p, 7)
            s = small_bold.render(str(self.number), True, (12,12,12))
            surf.blit(s, s.get_rect(center=p))


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.balls = []
        self.cue = Ball(PLAY.left + 205, PLAY.centery, cue=True)
        self.balls.append(self.cue)
        # official-ish 9-ball diamond: 1 front, 9 center, random others
        nums = [2,3,4,5,6,7,8]
        random.shuffle(nums)
        layout = [(0,0,1), (1,-.5,nums[0]), (1,.5,nums[1]),
                  (2,-1,nums[2]), (2,0,9), (2,1,nums[3]),
                  (3,-.5,nums[4]), (3,.5,nums[5]), (4,0,nums[6])]
        spacing_x = math.sqrt(3) * BALL_R + 0.8
        spacing_y = 2 * BALL_R + 0.8
        sx, sy = PLAY.right - 280, PLAY.centery
        for col,row,num in layout:
            self.balls.append(Ball(sx + col*spacing_x, sy + row*spacing_y, num))
        self.turn = 1
        self.shot_no = 0
        self.fouls = 0
        self.message = "PLAYER 1 - BREAK"
        self.aiming = False
        self.drag_start = None
        self.aim_angle = 0
        self.power = 0
        self.spin_x = 0
        self.spin_y = 0
        self.shot_start_positions = {}
        self.shot_first_hit = None
        self.shot_pocketed = []
        self.shot_moved = False
        self.game_over = False
        self.winner = None

    def moving(self):
        return any(b.speed > 0 for b in self.balls if not b.pocketed)

    def lowest_ball(self):
        live = [b.number for b in self.balls if not b.cue and not b.pocketed]
        return min(live) if live else None

    def ball_at(self, n):
        return next((b for b in self.balls if b.number == n), None)

    def start_shot(self):
        self.shot_start_positions = {id(b):(b.x,b.y,b.pocketed) for b in self.balls}
        self.shot_first_hit = None
        self.shot_pocketed = []
        self.shot_moved = False

    def shoot(self, angle, power):
        if self.game_over or self.moving() or self.cue.pocketed or power < MIN_SHOT:
            return
        self.start_shot()
        self.aim_angle = angle
        # spin changes initial cue direction slightly and affects cushion behavior below
        self.cue.vx = math.cos(angle) * power
        self.cue.vy = math.sin(angle) * power
        self.cue.spin_x = self.spin_x
        self.cue.spin_y = self.spin_y
        self.shot_no += 1
        self.aiming = False
        self.message = f"PLAYER {self.turn} - SHOOT"

    def finish_shot(self):
        if self.game_over:
            return
        lowest = self.lowest_ball()
        foul = False
        if self.cue.pocketed:
            foul = True
        elif self.shot_first_hit is None:
            foul = True
        elif lowest is not None and self.shot_first_hit != lowest:
            foul = True

        pocketed9 = 9 in self.shot_pocketed
        if pocketed9 and not foul:
            self.game_over = True
            self.winner = self.turn
            self.message = f"PLAYER {self.turn} WINS!  9-BALL"
            return

        if foul:
            self.fouls += 1
            self.turn = 2 if self.turn == 1 else 1
            self.message = f"FOUL! PLAYER {self.turn}: BALL IN HAND"
            self.place_cue_for_ball_in_hand()
        else:
            # In 9-ball, continue if any ball was pocketed; otherwise switch.
            if not self.shot_pocketed:
                self.turn = 2 if self.turn == 1 else 1
            self.message = f"PLAYER {self.turn} - {('CONTINUE' if self.shot_pocketed else 'YOUR TURN')}"

        self.shot_pocketed = []

    def place_cue_for_ball_in_hand(self):
        self.cue.pocketed = False
        self.cue.vx = self.cue.vy = 0
        self.cue.x, self.cue.y = PLAY.left + 160, PLAY.centery
        # push away from occupied balls
        for _ in range(100):
            if all(math.hypot(self.cue.x-b.x,self.cue.y-b.y) > BALL_R*2+2 for b in self.balls if b is not self.cue and not b.pocketed):
                break
            self.cue.x = random.uniform(PLAY.left+60, PLAY.centerx-50)
            self.cue.y = random.uniform(PLAY.top+50, PLAY.bottom-50)

    def pocket_check(self):
        for b in self.balls:
            if b.pocketed:
                continue
            for px,py in POCKETS:
                if math.hypot(b.x-px,b.y-py) < POCKET_R:
                    b.pocketed = True
                    b.vx = b.vy = 0
                    if b.cue:
                        self.message = "SCRATCH!"
                    else:
                        self.shot_pocketed.append(b.number)
                    if POCKET_SOUND:
                        POCKET_SOUND.play()
                    break

    def cushions(self):
        for b in self.balls:
            if b.pocketed:
                continue
            # Slightly rounded pocket zones: let balls enter pockets near rails.
            margin = BALL_R
            bounced = False
            if b.x - margin < PLAY.left and abs(b.y-PLAY.top) > POCKET_R and abs(b.y-PLAY.bottom) > POCKET_R:
                b.x = PLAY.left + margin; b.vx = abs(b.vx); bounced=True
            elif b.x + margin > PLAY.right and abs(b.y-PLAY.top) > POCKET_R and abs(b.y-PLAY.bottom) > POCKET_R:
                b.x = PLAY.right - margin; b.vx = -abs(b.vx); bounced=True
            if b.y - margin < PLAY.top and abs(b.x-PLAY.left) > POCKET_R and abs(b.x-PLAY.right) > POCKET_R:
                b.y = PLAY.top + margin; b.vy = abs(b.vy); bounced=True
            elif b.y + margin > PLAY.bottom and abs(b.x-PLAY.left) > POCKET_R and abs(b.x-PLAY.right) > POCKET_R:
                b.y = PLAY.bottom - margin; b.vy = -abs(b.vy); bounced=True
            if bounced and HIT_SOUND and b.speed > 1:
                HIT_SOUND.play()

    def collisions(self):
        for i in range(len(self.balls)):
            for j in range(i+1,len(self.balls)):
                a,b = self.balls[i],self.balls[j]
                if a.pocketed or b.pocketed: continue
                dx,dy=b.x-a.x,b.y-a.y
                d=math.hypot(dx,dy)
                if d == 0 or d >= BALL_R*2: continue
                nx,ny=dx/d,dy/d
                overlap=BALL_R*2-d
                a.x-=nx*overlap/2; a.y-=ny*overlap/2
                b.x+=nx*overlap/2; b.y+=ny*overlap/2
                rv=(a.vx-b.vx)*nx+(a.vy-b.vy)*ny
                if rv <= 0: continue
                # equal masses, restitution ~1
                a.vx-=rv*nx; a.vy-=rv*ny
                b.vx+=rv*nx; b.vy+=rv*ny
                if self.shot_first_hit is None and (a.cue or b.cue):
                    other = b if a.cue else a
                    if not other.cue:
                        self.shot_first_hit=other.number
                if HIT_SOUND and abs(rv) > .35:
                    HIT_SOUND.set_volume(clamp(abs(rv)/12,.08,.55)); HIT_SOUND.play()

    def update(self):
        was_moving = self.moving()
        for b in self.balls: b.update()
        self.collisions()
        self.cushions()
        self.pocket_check()
        now_moving = self.moving()
        if was_moving and not now_moving:
            self.finish_shot()

    def draw(self,surf):
        surf.fill((18,18,22))
        # table frame
        pygame.draw.rect(surf, WOOD, TABLE, border_radius=18)
        pygame.draw.rect(surf, (35,20,10), TABLE, 4, border_radius=18)
        pygame.draw.rect(surf, RAIL, PLAY.inflate(12,12), border_radius=10)
        pygame.draw.rect(surf, FELT, PLAY, border_radius=7)
        # subtle cloth lines
        pygame.draw.line(surf, FELT2, (PLAY.centerx,PLAY.top+8),(PLAY.centerx,PLAY.bottom-8),1)
        # diamonds
        for x in [PLAY.left+105, PLAY.left+210, PLAY.centerx, PLAY.right-210, PLAY.right-105]:
            for y in [PLAY.top-17, PLAY.bottom+17]:
                if PLAY.left < x < PLAY.right:
                    pygame.draw.polygon(surf,GOLD,[(x,y-5),(x+5,y),(x,y+5),(x-5,y)])
        for y in [PLAY.top+105, PLAY.top+210, PLAY.centery, PLAY.bottom-210, PLAY.bottom-105]:
            for x in [PLAY.left-17, PLAY.right+17]:
                if PLAY.top < y < PLAY.bottom:
                    pygame.draw.polygon(surf,GOLD,[(x-5,y),(x,y-5),(x+5,y),(x,y+5)])
        # pockets
        for px,py in POCKETS:
            pygame.draw.circle(surf,(4,4,4),(px,py),POCKET_R+4)
            pygame.draw.circle(surf,(1,1,1),(px,py),POCKET_R)
        for b in self.balls: b.draw(surf)

        # Aim guide and power
        if self.aiming and not self.moving() and not self.game_over:
            mx,my=pygame.mouse.get_pos()
            dx,dy=mx-self.cue.x,my-self.cue.y
            dist=max(1,math.hypot(dx,dy))
            # mouse position is behind cue -> shot direction is opposite
            ax,ay=-dx/dist,-dy/dist
            guide=240
            pygame.draw.line(surf,(245,245,245),(self.cue.x,self.cue.y),(self.cue.x+ax*guide,self.cue.y+ay*guide),2)
            pygame.draw.circle(surf,(255,255,255),(round(self.cue.x+ax*80),round(self.cue.y+ay*80)),BALL_R,1)
            pygame.draw.line(surf,(230,190,40),(self.cue.x,self.cue.y),(mx,my),3)

        self.draw_ui(surf)

    def draw_ui(self,surf):
        # header
        pygame.draw.rect(surf,(28,28,34),(0,0,WIDTH,62))
        title=big.render("9-BALL PRO",True,GOLD); surf.blit(title,(24,17))
        msg=font.render(self.message,True,TEXT); surf.blit(msg,msg.get_rect(center=(WIDTH//2,31)))
        info=small.render(f"Shot {self.shot_no}   Fouls {self.fouls}   Target: {self.lowest_ball() or '-'}",True,(190,190,195))
        surf.blit(info,(WIDTH-300,22))
        # power meter
        x,y,w,h=55,610,430,24
        pygame.draw.rect(surf,(45,45,50),(x,y,w,h),border_radius=8)
        pygame.draw.rect(surf,GOLD,(x+2,y+2,int((w-4)*self.power/MAX_POWER),h-4),border_radius=6)
        surf.blit(small_bold.render("POWER",True,TEXT),(x+8,y+3))
        # spin control
        sx,sy=560,610
        pygame.draw.circle(surf,(50,50,55),(sx,sy),25)
        pygame.draw.circle(surf,WHITE,(round(sx+self.spin_x*18),round(sy+self.spin_y*18)),6)
        surf.blit(small_bold.render("SPIN",True,TEXT),(sx-23,sy+30))
        helptext="Drag from cue ball to aim / power   •   Release to shoot   •   R = rack reset   •   ESC = quit"
        surf.blit(small.render(helptext,True,(165,165,170)),(55,650))
        if self.game_over:
            overlay=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
            overlay.fill((0,0,0,100)); surf.blit(overlay,(0,0))
            t=big.render(self.message,True,GOLD); surf.blit(t,t.get_rect(center=(WIDTH//2,HEIGHT//2-15)))
            s=font.render("Press R to play again",True,WHITE); surf.blit(s,s.get_rect(center=(WIDTH//2,HEIGHT//2+30)))


def main():
    screen=pygame.display.set_mode((WIDTH,HEIGHT))
    pygame.display.set_caption("9-Ball Pro - Python / Pygame")
    clock=pygame.time.Clock()
    game=Game()
    running=True
    while running:
        clock.tick(FPS)
        for e in pygame.event.get():
            if e.type==pygame.QUIT: running=False
            elif e.type==pygame.KEYDOWN:
                if e.key==pygame.K_ESCAPE: running=False
                elif e.key==pygame.K_r: game.reset()
            elif e.type==pygame.MOUSEBUTTONDOWN and e.button==1:
                if not game.moving() and not game.game_over:
                    mx,my=pygame.mouse.get_pos()
                    # cue-ball drag anywhere near cue
                    if math.hypot(mx-game.cue.x,my-game.cue.y)<55:
                        game.aiming=True
                        game.drag_start=(mx,my)
            elif e.type==pygame.MOUSEBUTTONUP and e.button==1:
                if game.aiming:
                    mx,my=pygame.mouse.get_pos()
                    dx,dy=game.cue.x-mx,game.cue.y-my
                    power=clamp(math.hypot(dx,dy)*0.075,0,MAX_POWER)
                    angle=math.atan2(dy,dx)
                    game.shoot(angle,power)
                    game.power=0
            elif e.type==pygame.MOUSEMOTION and game.aiming:
                mx,my=pygame.mouse.get_pos()
                game.power=clamp(math.hypot(game.cue.x-mx,game.cue.y-my)*0.075,0,MAX_POWER)
            elif e.type==pygame.MOUSEBUTTONDOWN and e.button==3:
                # Right-click spin: place spin point based on click position around indicator
                mx,my=pygame.mouse.get_pos()
                sx,sy=560,610
                if math.hypot(mx-sx,my-sy)<40:
                    game.spin_x=clamp((mx-sx)/18,-1,1)
                    game.spin_y=clamp((my-sy)/18,-1,1)

        game.update()
        game.draw(screen)
        pygame.display.flip()
    pygame.quit(); sys.exit()

if __name__=="__main__":
    main()
