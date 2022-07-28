# minqlx - A Quake Live server administrator bot.
# Copyright (C) 2015 Mino <mino@minomino.org>
# Copyright (C) 2022 Lauri Räsänen

# This file is part of minqlx.

# minqlx is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# minqlx is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with minqlx. If not, see <http://www.gnu.org/licenses/>.

"""
A sample plugin for hooking ClientThink and modifying client_cmd.
"""

# minqlx
import minqlx

# python
import time
import math
import random
from enum import IntEnum
from pprint import pprint


class Actions(IntEnum):
    LEFT_DIAG = 0
    RIGHT_DIAG = 1
    LEFT = 2
    RIGHT = 3
    MAX_ACTION = 4


TURN_SPEED_MAX = 180
INPUT_FRAME_INTERVAL = 25


class bot_test(minqlx.Plugin):
    bot = None

    def __init__(self):
        super().__init__()
        self.add_hook("client_think", self.handle_client_think)
        self.add_hook("frame", self.handle_frame)
        self.add_command("testbot", self.cmd_add)

    def handle_client_think(self, player, client_cmd):
        return client_cmd

    def cmd_add(self, player, msg, channel):
        self.bot = StrafeBot(minqlx.bot_add())

    def handle_frame(self):
        if self.bot is not None:
            if self.bot.run_frame() == False:
                self.bot = None


class StrafeBot(minqlx.Player):
    actions = []
    current_action = -1

    def __init__(self, client_id):
        super().__init__(client_id)
        self.reset()

    def reset(self):
        # test
        self.current_action = -1
        for i in range(20 * int(125 / INPUT_FRAME_INTERVAL)):
            act = Actions(random.randint(0, int(Actions.MAX_ACTION) - 1))
            if act in [Actions.LEFT, Actions.RIGHT]:
                act = [act, random.randint(0, TURN_SPEED_MAX)]
            else:
                act = [act]
            for x in range(INPUT_FRAME_INTERVAL):
                self.actions.append(act)

    def run_frame(self):
        self.current_action += 1

        if self.current_action > len(self.actions) - 1:
            # don't timeout bot
            return self.run_action([Actions.MAX_ACTION])

        return self.run_action(self.actions[self.current_action])

    def run_action(self, action):
        grounded = self.state.grounded
        max_ground_speed = 320.0
        velocity = self.state.velocity
        vel_len = MathHelper.vec2_len(velocity)
        jump = (
            grounded and vel_len > max_ground_speed and action[0] != Actions.MAX_ACTION
        )
        current_yaw = self.state.viewangles[1]
        new_yaw = current_yaw
        wishmove = None
        frametime = 1.0 / 125.0

        # don't walkmove for 1 frame,
        # jump will return early and call airmove instead.
        # (or watermove)
        if jump:
            grounded = False

        if grounded:
            if action[0] == Actions.LEFT:
                action[0] = Actions.LEFT_DIAG
            elif action[0] == Actions.RIGHT:
                action[0] = Actions.RIGHT_DIAG

            accel = 10.0

            wishmove = self.get_wishmove(action[0], jump)
        else:
            wishmove = self.get_wishmove(action[0], jump)

            # Acceleration
            if action[0] in [Actions.LEFT_DIAG, Actions.RIGHT_DIAG]:
                if MathHelper.vec2_len(wishmove) > 0.1 and vel_len > 0.1:
                    forward = MathHelper.get_forward(current_yaw)
                    right = [forward[1], -forward[0], 0]

                    wishvel = [0.0, 0.0, 0.0]
                    for i in range(3):
                        wishvel[i] = forward[i] * wishmove[0] + right[i] * wishmove[1]
                    wishvel[2] += wishmove[2]
                    wishspeed = MathHelper.vec2_len(wishvel)

                    accel = 1.0

                    vel_to_optimal_yaw = MathHelper.get_optimal_strafe_angle(
                        wishspeed, accel, velocity, frametime
                    )
                    vel_to_optimal_yaw = MathHelper.rad_to_deg(vel_to_optimal_yaw)
                    if vel_to_optimal_yaw > 0:
                        vel_to_optimal_yaw -= 45.0
                        if action[0] in [Actions.RIGHT_DIAG, Actions.RIGHT]:
                            vel_to_optimal_yaw = -vel_to_optimal_yaw
                    vel_yaw = MathHelper.get_yaw(
                        [velocity[0], velocity[1], velocity[2]]
                    )
                    new_yaw = vel_yaw + vel_to_optimal_yaw
            # Turning
            elif action[0] in [Actions.LEFT, Actions.RIGHT]:
                yaw_change = action[1] * frametime
                if action[0] == Actions.RIGHT:
                    yaw_change = -yaw_change
                vel_yaw = MathHelper.get_yaw([velocity[0], velocity[1], velocity[2]])
                new_yaw = vel_yaw + yaw_change

        # delta required here for bot
        new_yaw = MathHelper.wrap_yaw(new_yaw - self.state.delta_angles[1])

        cmd = {
            "pitch": 0,
            "yaw": new_yaw,
            "roll": 0,
            "buttons": 0,
            "weapon": 5,
            "weapon_primary": 5,
            "fov": 100,
            "forwardmove": wishmove[0],
            "rightmove": wishmove[1],
            "upmove": wishmove[2],
        }
        return minqlx.client_think(self.id, cmd)

    def get_wishmove(self, action, jump):
        speed = 127
        wishdir = [0, 0, 0]
        if action == Actions.LEFT_DIAG:
            wishdir = [speed, -speed, 0]
        elif action == Actions.LEFT:
            wishdir = [0, -speed, 0]
        elif action == Actions.RIGHT_DIAG:
            wishdir = [speed, speed, 0]
        elif action == Actions.RIGHT:
            wishdir = [0, speed, 0]
        if jump:
            wishdir[2] = speed
        return wishdir


class MathHelper:
    @staticmethod
    def wrap_yaw(yaw):
        while yaw > 180.0:
            yaw -= 360.0
        while yaw < -180.0:
            yaw += 360.0
        return yaw

    @staticmethod
    def rad_to_deg(a):
        return a * 180.0 / math.pi

    @staticmethod
    def deg_to_rad(a):
        return a * math.pi / 180.0

    @staticmethod
    def get_yaw(vec):
        norm = MathHelper.vec3_norm(vec)
        rad = math.acos(norm[0])
        deg = 180.0 * rad / math.pi  # 0-180
        if norm[1] < 0:
            return -deg
        return deg

    @staticmethod
    def get_forward(yaw):
        rad = yaw * math.pi * 2.0 / 360.0
        a = math.sin(rad)
        b = math.cos(rad)
        return [b, a, 0]

    @staticmethod
    def sign(x):
        if x < 0:
            return -1.0
        elif x > 0:
            return 1.0
        return 0.0

    @staticmethod
    def vec2_angle_sign(v, w):
        return MathHelper.sign(v[0] * w[1] - v[1] * w[0])

    @staticmethod
    def vec_dot(v, w, i):
        dot = 0.0
        for i in range(i):
            dot += v[i] * w[i]
        return dot

    @staticmethod
    def vec2_len(v):
        return math.sqrt(MathHelper.vec_dot(v, v, 2))

    @staticmethod
    def vec3_len(v):
        return math.sqrt(MathHelper.vec_dot(v, v, 3))

    @staticmethod
    def vec3_norm(v):
        len = MathHelper.vec3_len(v)
        v[0] /= len
        v[1] /= len
        v[2] /= len
        return v

    @staticmethod
    def vec3_add(v, w):
        v[0] += w[0]
        v[1] += w[1]
        v[2] += w[2]
        return v

    @staticmethod
    def vec3_scale(v, a):
        v[0] *= a
        v[1] *= a
        v[2] *= a
        return v

    @staticmethod
    def clamp(a, b, c):
        return min(c, max(a, b))

    @staticmethod
    def get_optimal_strafe_angle(wishspeed, accel, velocity, frametime):
        # speed = accel * wishspeed * frametime
        # num = wishspeed - speed
        num = wishspeed * (1.0 - accel * frametime)
        vel_len = MathHelper.vec2_len(velocity)
        if num >= vel_len:
            return 0
        return math.acos(num / vel_len)
