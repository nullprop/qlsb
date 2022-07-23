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
from enum import IntEnum
from pprint import pprint


class Actions(IntEnum):
    LEFT_DIAG = 0
    RIGHT_DIAG = 1
    LEFT = 2
    RIGHT = 3
    MAX_ACTION = 4


class bot_test(minqlx.Plugin):
    client_num = -1
    client_player = None
    action = Actions.LEFT_DIAG

    def __init__(self):
        super().__init__()
        self.add_hook("client_think", self.handle_client_think)
        self.add_hook("frame", self.handle_frame)
        # self.allocate()
        # self.add()
        self.add_command("testbot", self.cmd_add)
        self.add_command("testang", self.cmd_ang)
        self.cycle_action()

    def handle_client_think(self, player, client_cmd):
        # client_cmd["forwardmove"] = 127
        # print("client cmd player {}:".format(player.name))
        # pprint(client_cmd)
        return client_cmd

    def cmd_add(self, player, msg, channel):
        self.add()

    @minqlx.delay(3)
    def add(self):
        self.client_num = minqlx.bot_add()
        self.client_player = self.player(self.client_num)
        print("bot_add: {}".format(self.client_num))

    @minqlx.delay(3)
    def cycle_action(self):
        new_action = (int(self.action) + 1) % int(Actions.MAX_ACTION)
        self.action = Actions(new_action)
        self.cycle_action()

    def cmd_ang(self, player, msg, channel):
        forward = MathHelper.get_forward(player.state.viewangles[1])
        right = [forward[1], -forward[0], 0]
        print(
            "yaw {}, forward {} {}, right {} {}".format(
                player.state.viewangles[1], forward[0], forward[1], right[0], right[1]
            )
        )

    def handle_frame(self):
        if self.client_num >= 0:
            grounded = self.client_player.state.grounded
            max_ground_speed = 320.0
            velocity = self.client_player.state.velocity
            vel_len = MathHelper.vec2_len(velocity)
            jump = grounded and vel_len > max_ground_speed
            action = self.action
            if grounded:
                if action == Actions.LEFT:
                    action = Actions.LEFT_DIAG
                elif action == Actions.RIGHT:
                    action = Actions.RIGHT_DIAG
            wishmove = self.get_wishmove(action, jump)

            current_yaw = self.client_player.state.viewangles[1]
            new_yaw = current_yaw

            if MathHelper.vec2_len(wishmove) > 0.1 and vel_len > 0.1:
                forward = MathHelper.get_forward(current_yaw)
                right = [forward[1], -forward[0], 0]

                wishdir = [0.0, 0.0, 0.0]
                for i in range(3):
                    wishdir[i] = forward[i] * wishmove[0] + right[i] * wishmove[1]
                wishdir[2] += wishmove[2]
                vel_to_optimal_yaw = StrafeHelper.get_optimal_strafe_angle(
                    forward,
                    velocity,
                    wishmove,
                    10.0 if grounded else 1.0,
                    1.0 / 125.0,
                )
                vel_yaw = MathHelper.get_yaw([velocity[0], velocity[1], velocity[2]])
                new_yaw = vel_yaw + vel_to_optimal_yaw

            # delta required here too for bot
            new_yaw = MathHelper.wrap_yaw(
                new_yaw - self.client_player.state.delta_angles[1]
            )

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
            if minqlx.client_think(self.client_num, cmd) == False:
                self.client_num = -1

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


class StrafeHelper:
    """
    Optimal strafe angles based on code by kugelrund.
    https://github.com/kugelrund/strafe_helper
    MPL 2.0
    """

    # Note: Assumes forward is normalized
    @staticmethod
    def get_optimal_strafe_angle(forward, velocity, wishdir, accel, frametime):
        v_z = velocity[2]
        w_z = wishdir[2]

        wishspeed = MathHelper.vec3_len(wishdir)
        velocity_len = MathHelper.vec2_len(velocity)
        wishdir_len = MathHelper.vec2_len(wishdir)

        forward_vel_angle = math.acos(
            MathHelper.vec_dot(forward, wishdir, 2) / wishdir_len
        ) * MathHelper.vec2_angle_sign(wishdir, forward)

        angle_sign = MathHelper.vec2_angle_sign(wishdir, velocity)

        angle_optimal = (wishspeed * (1.0 - accel * frametime) - v_z * w_z) / (
            velocity_len * wishdir_len
        )
        angle_optimal = MathHelper.clamp(angle_optimal, -1.0, 1.0)
        angle_optimal = math.acos(angle_optimal)
        angle_optimal = angle_sign * angle_optimal - forward_vel_angle

        # return angle_optimal

        angle_minimum = (
            (wishspeed - v_z * w_z)
            / (2.0 - wishdir_len * wishdir_len)
            * wishdir_len
            / velocity_len
        )
        angle_minimum = MathHelper.clamp(angle_minimum, -1.0, 1.0)
        angle_minimum = math.acos(angle_minimum)
        angle_minimum = angle_sign * angle_minimum - forward_vel_angle

        angle_maximum = (
            -0.5 * accel * frametime * wishspeed * wishdir_len / velocity_len
        )
        angle_maximum = MathHelper.clamp(angle_maximum, -1.0, 1.0)
        angle_maximum = math.acos(angle_maximum)
        angle_maximum = angle_sign * angle_maximum - forward_vel_angle

        angle_current = MathHelper.vec_dot(velocity, forward, 2) / velocity_len
        angle_current = MathHelper.clamp(angle_current, -1.0, 1.0)
        angle_current = math.acos(angle_current)
        angle_current = MathHelper.vec2_angle_sign(forward, velocity) * angle_current

        angle_optimal = MathHelper.clamp(angle_optimal, angle_minimum, angle_maximum)
        return angle_optimal

        """ Make sure that angle_current fits well to the other angles. That is, try
        * equivalent angles by adding or subtracting multiples of 2 * M_PI such
        * that the angle values are closest to each other. That way we avoid
        * differences greater than 2 * M_PI between the angles, which would break
        * the drawing code. """
        two_pi = math.pi * 2.0
        angle_current += math.trunc((angle_minimum - angle_current) / two_pi) * two_pi
        angle_current += math.trunc((angle_maximum - angle_current) / two_pi) * two_pi

        return angle_optimal - angle_current
