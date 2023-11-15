from pico2d import *

import random
import math
import game_framework
import game_world
from behavior_tree import BehaviorTree, Action, Sequence, Condition, Selector
import play_mode


# zombie Run Speed
PIXEL_PER_METER = (10.0 / 0.3)  # 10 pixel 30 cm
RUN_SPEED_KMPH = 10.0  # Km / Hour
RUN_SPEED_MPM = (RUN_SPEED_KMPH * 1000.0 / 60.0)
RUN_SPEED_MPS = (RUN_SPEED_MPM / 60.0)
RUN_SPEED_PPS = (RUN_SPEED_MPS * PIXEL_PER_METER)

# zombie Action Speed
TIME_PER_ACTION = 0.5
ACTION_PER_TIME = 1.0 / TIME_PER_ACTION
FRAMES_PER_ACTION = 10.0

animation_names = ['Walk', 'Idle']


class Zombie:
    images = None

    def load_images(self):
        if Zombie.images == None:
            Zombie.images = {}
            for name in animation_names:
                Zombie.images[name] = [load_image("./zombie/" + name + " (%d)" % i + ".png") for i in range(1, 11)]
            Zombie.font = load_font('ENCR10B.TTF', 40)
            Zombie.marker_image = load_image('hand_arrow.png')


    def __init__(self, x=None, y=None):
        self.x = x if x else random.randint(100, 1180)
        self.y = y if y else random.randint(100, 924)
        self.load_images()
        self.dir = 0.0      # radian 값으로 방향을 표시
        self.speed = 0.0
        self.frame = random.randint(0, 9)
        self.state = 'Idle'
        self.ball_count = 0

        self.tx, self.ty = 1000, 1000 # 목적지
        self.build_behavior_tree()
        self.patrol_locations = [
            (43, 274), (1118, 274), (1050, 494), (575, 804), (235, 991), (575, 804), (1050, 494)
        ]
        self.location_n = 0


    def get_bb(self):
        return self.x - 50, self.y - 50, self.x + 50, self.y + 50


    def update(self):
        self.frame = (self.frame + FRAMES_PER_ACTION * ACTION_PER_TIME * game_framework.frame_time) % FRAMES_PER_ACTION
        # fill here
        self.bt.run()

    def draw(self):
        if math.cos(self.dir) < 0:
            Zombie.images[self.state][int(self.frame)].composite_draw(0, 'h', self.x, self.y, 100, 100)
        else:
            Zombie.images[self.state][int(self.frame)].draw(self.x, self.y, 100, 100)
        self.font.draw(self.x - 10, self.y + 60, f'{self.ball_count}', (0, 0, 255))
        Zombie.marker_image.draw(self.tx + 25, self.ty - 25)
        draw_rectangle(*self.get_bb())

    def handle_event(self, event):
        pass

    def handle_collision(self, group, other):
        if group == 'zombie:ball':
            self.ball_count += 1


    def set_target_location(self, x=None, y=None):
        if not x or not y:
            raise ValueError('위치 지정을 해야 합니다.')
        self.tx, self.ty = x, y
        return BehaviorTree.SUCCESS
        pass

    def distance_less_than(self, x1, y1, x2, y2, r):
        distance2 = (x1 - x2) ** 2 + (y1 - y2) ** 2
        return distance2 < (r * PIXEL_PER_METER) ** 2

    def move_slightly_to(self, tx, ty): # 목표지점으로 좀비를 살짝 움직이는 함수 ?
        self.dir = math.atan2(ty - self.y, tx - self.x) # 현재 위치에서 목적지까지의 각도가 나옴(라디안?)
        self.speed = RUN_SPEED_PPS
        self.x += self.speed * math.cos(self.dir) * game_framework.frame_time
        self.y += self.speed * math.sin(self.dir) * game_framework.frame_time

    def move_to(self, r=0.5):
        self.state = 'Walk'
        self.move_slightly_to(self.tx, self.ty)
        if self.distance_less_than(self.tx, self.ty, self.x, self.y, r): # 목적지에 근접했는지 확인하고
            return BehaviorTree.SUCCESS # 근접했으면 success를 리턴
        else:
            return BehaviorTree.RUNNING # 아니면 계속 진행

    def set_random_location(self):
        self.tx, self.ty = random.randint(100, 1200 - 100), random.randint(100, 1024 - 100)
        return BehaviorTree.SUCCESS

    def is_boy_nearby(self, distance):
        if self.distance_less_than(play_mode.boy.x, play_mode.boy.y, self.x, self.y, distance):
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def move_to_boy(self, r=0.5):
        self.state = 'Walk'
        self.move_slightly_to(play_mode.boy.x, play_mode.boy.y)
        if self.distance_less_than(play_mode.boy.x, play_mode.boy.y, self.x, self.y, r):  # 목적지에 근접했는지 확인하고
            return BehaviorTree.SUCCESS  # 근접했으면 success를 리턴
        else:
            return BehaviorTree.RUNNING  # 아니면 계속 진행

    def is_boys_ball(self): # 내가 boy보다 공이 적은가
        if self.ball_count < play_mode.boy.ball_count:
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def is_zombies_ball(self): # 내가 boy보다 공이 많은가
        if self.ball_count >= play_mode.boy.ball_count:
            return BehaviorTree.SUCCESS
        else:
            return BehaviorTree.FAIL

    def runaway_to_boy(self):
        self.state = 'Walk'
        self.move_slightly_to(-(play_mode.boy.x - self.x) + self.x, -(play_mode.boy.y - self.y) + self.y)
        if not self.is_boy_nearby(7):
            return BehaviorTree.SUCCESS  # 멀어졌으면 SUCCESS 리턴
        else:
            return BehaviorTree.RUNNING  # 아니면 계속 진행
        pass

    def get_patrol_location(self):
        self.tx, self.ty = self.patrol_locations[self.location_n]
        self.location_n = (self.location_n + 1) % len(self.patrol_locations)
        return BehaviorTree.SUCCESS

    def build_behavior_tree(self):
        a2 = Action('Move to', self.move_to, 0.5)
        a3 = Action('Set random location', self.set_random_location)

        SEQ_wander = Sequence('Wander', a3, a2) # 랜덤 로케이션을 설정한 후 거기로 이동

        c1 = Condition('소년이 근처에 있나요?', self.is_boy_nearby, 7) # 몇 미터 거리까지 쫓아오는지
        a4 = Action('소년을 향해 이동', self.move_to_boy, 0.5)

        a6 = Action('소년 반대 방향으로 이동', self.runaway_to_boy)

        c2 = Condition('소년의 공이 더 많나요?', self.is_boys_ball)
        c3 = Condition('좀비의 공이 더 많나요?', self.is_zombies_ball)

        SEQ_runaway_boy = Sequence('소년에게서 도망치기', c2, c1, a6 )
        SEQ_chase_boy = Sequence('소년을 쫓아가기', c3, c1, a4)

        root = SEL_chase_or_runaway_or_wander = Selector('쫓아가거나 도망가거나 배회하거나', SEQ_chase_boy, SEQ_runaway_boy, SEQ_wander)

        self.bt = BehaviorTree(root)
        pass
