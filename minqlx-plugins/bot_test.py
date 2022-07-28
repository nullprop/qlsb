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


class bot_test(minqlx.Plugin):
    bot = None
    start_pos = None
    start_ang = None

    def __init__(self):
        super().__init__()

        self.add_hook("client_think", self.handle_client_think)
        self.add_hook("frame", self.handle_frame)

        self.add_command("testbot", self.cmd_add)
        self.add_command("resetbot", self.cmd_reset)
        self.add_command("solve", self.cmd_solve)
        self.add_command("stopsolve", self.cmd_stop_solve)
        self.add_command("play", self.cmd_play)
        self.add_command("stopplay", self.cmd_stop_play)
        self.add_command("setstart", self.cmd_set_start)

    def handle_client_think(self, player, client_cmd):
        return client_cmd

    def cmd_add(self, player, msg, channel):
        self.bot = StrafeBot(minqlx.bot_add())
        if self.start_pos != None and self.start_ang != None:
            self.bot.set_start(
                self.start_pos,
                self.start_ang,
            )

    def cmd_reset(self, player, msg, channel):
        self.bot.reset()

    def cmd_solve(self, player, msg, channel):
        self.bot.start_solve()

    def cmd_stop_solve(self, player, msg, channel):
        self.bot.stop_solve()

    def cmd_play(self, player, msg, channel):
        self.bot.start_playback()

    def cmd_stop_play(self, player, msg, channel):
        self.bot.stop_playback()

    def cmd_set_start(self, player, msg, channel):
        self.start_pos = player.state.position
        self.start_ang = [
            0,
            player.state.viewangles[1],
            0,
        ]
        if self.bot != None:
            self.bot.set_start(
                self.start_pos,
                self.start_ang,
            )

    def handle_frame(self):
        if self.bot is not None:
            if self.bot.run_frame() == False:
                self.bot = None


class Actions(IntEnum):
    LEFT_DIAG = 0
    RIGHT_DIAG = 1
    LEFT = 2
    RIGHT = 3
    MAX_ACTION = 4


TURN_SPEED_MAX = 180
INPUT_FRAME_INTERVAL = 25


class StrafeBot(minqlx.Player):
    playback_frame = -1
    history = []
    playback = False
    solve = False
    best_solution = None
    last_solution = None
    measure_next_frame = False
    save_next_frame = False

    def __init__(self, client_id):
        super().__init__(client_id)

    @staticmethod
    def empty_solution():
        return [Actions.MAX_ACTION, 0, -math.inf]

    def reset(self):
        self.playback_frame = -1
        self.history = []
        self.playback = False
        self.solve = False
        self.measure_next_frame = False
        self.save_next_frame = False
        self.best_solution = StrafeBot.empty_solution()
        self.last_solution = StrafeBot.empty_solution()

    def set_start(self, start_pos, start_ang):
        self.reset()
        self.teleport(
            start_pos,
            (0, 0, 0),
            (0, start_ang[1], 0),
        )
        self.history.append(
            [
                [start_pos[0], start_pos[1], start_pos[2]],
                [0, 0, 0],
                [0, start_ang[1], 0],
                StrafeBot.empty_solution(),
            ]
        )

    def start_playback(self):
        if len(self.history) > 0:
            self.teleport(
                self.history[0][0],
                self.history[0][1],
                self.history[0][2],
            )
            self.playback = True
            self.playback_frame = -1
        else:
            print("start_playback() expected history")

    def stop_playback(self):
        self.playback = False

    def start_solve(self):
        if len(self.history) > 0:
            self.teleport(
                self.history[-1][0],
                self.history[-1][1],
                self.history[-1][2],
            )
            self.solve = True
        else:
            print("start_solve() expected history")

    def stop_solve(self):
        self.solve = False

    def run_frame(self):
        if self.playback == True:
            return self.run_playback_frame()
        elif self.solve == True:
            return self.run_solve_frame()
        self.idle_frame()

    def run_playback_frame(self):
        self.playback_frame += 1

        if self.playback_frame > len(self.history) - 1:
            # don't timeout bot
            return self.idle_frame()

        return self.run_action(self.history[self.playback_frame][3])

    def run_solve_frame(self):
        # 1 frame delay so run_action applies new position
        if self.measure_next_frame == True:
            self.measure_next_frame = False
            self.last_solution[2] = self.get_reward()
            if self.last_solution[2] > self.best_solution[2]:
                self.best_solution = [
                    self.last_solution[0],
                    self.last_solution[1],
                    self.last_solution[2],
                ]

        # 1 frame delay so run_action applies new position
        if self.save_next_frame == True:
            self.save_next_frame = False
            self.history.append(
                [
                    self.state.position,
                    self.state.velocity,
                    self.state.viewangles,
                    StrafeBot.empty_solution(),
                ]
            )

        if self.last_solution[0] == Actions.MAX_ACTION:
            self.last_solution[0] = Actions.LEFT_DIAG

        elif self.last_solution[0] == Actions.LEFT_DIAG:
            self.last_solution[0] = Actions.RIGHT_DIAG

        elif self.last_solution[0] == Actions.RIGHT_DIAG:
            self.last_solution[0] = Actions.LEFT
            self.last_solution[1] = 1

        elif self.last_solution[0] == Actions.LEFT:
            self.last_solution[1] += 1
            if self.last_solution[1] > TURN_SPEED_MAX:
                self.last_solution[0] = Actions.RIGHT
                self.last_solution[1] = 1

        elif self.last_solution[0] == Actions.RIGHT:
            self.last_solution[1] += 1
            if self.last_solution[1] > TURN_SPEED_MAX:
                # tried all inputs
                return self.solve_frame_advance(self.best_solution)

        return self.solve_frame_measure()

    def solve_frame_measure(self):
        self.teleport(
            self.history[-1][0],
            self.history[-1][1],
            self.history[-1][2],
        )
        self.measure_next_frame = True
        success = self.run_action(self.last_solution)
        return success

    def solve_frame_advance(self, solution):
        if len(self.history) > 0:
            self.history[-1][3] = solution
            self.teleport(
                self.history[-1][0],
                self.history[-1][1],
                self.history[-1][2],
            )
        print(
            "history len {}, s {} {} {}".format(
                len(self.history),
                solution[0],
                solution[1],
                solution[2],
            )
        )
        self.save_next_frame = True
        success = self.run_action(solution)
        self.last_solution = StrafeBot.empty_solution()
        self.best_solution = StrafeBot.empty_solution()
        return success

    def idle_frame(self):
        return self.run_action([Actions.MAX_ACTION])

    def get_reward(self):
        # TODO
        return self.state.velocity[1]
        # return self.state.position[1] - self.history[-1][0][1]

    def teleport(self, pos, vel, ang):
        minqlx.set_position(self.id, minqlx.Vector3(pos))
        minqlx.set_velocity(self.id, minqlx.Vector3(vel))
        minqlx.set_viewangles(self.id, minqlx.Vector3(ang))

    def run_action(self, action):
        max_ground_speed = 320.0
        velocity = self.state.velocity
        vel_len = MathHelper.vec2_len(velocity)
        grounded = self.state.grounded and velocity[2] < 250
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
            # don't modify passed list
            act = action[0]
            turn = 0
            if act == Actions.LEFT:
                act = Actions.LEFT_DIAG
                turn = action[1]
            elif act == Actions.RIGHT:
                act = Actions.RIGHT_DIAG
                turn = -action[1]

            accel = 10.0

            wishmove = self.get_wishmove(act, jump)
            if turn != 0:
                new_yaw += turn

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
