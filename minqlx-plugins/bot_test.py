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
        self.add_command("setend", self.cmd_set_end)
        self.add_command("addcp", self.cmd_add_cp)
        self.add_command("removecp", self.cmd_remove_cp)
        self.add_command("addcs", self.cmd_add_cs)

    def handle_client_think(self, player, client_cmd):
        return client_cmd

    def cmd_add(self, player, msg, channel):
        self.bot = StrafeBot(minqlx.bot_add())
        self.bot.set_start()

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
        MapConfig.start_point = Point.from_player(player, "start")
        if self.bot != None:
            self.bot.set_start()

    def cmd_set_end(self, player, msg, channel):
        MapConfig.end_point = Point.from_player(player, "end")

    def cmd_add_cp(self, player, msg, channel):
        MapConfig.checkpoints.append(
            Point.from_player(player, "cp{}".format(len(MapConfig.checkpoints)))
        )

    def cmd_remove_cp(self, player, msg, channel):
        if len(MapConfig.checkpoints) > 0:
            MapConfig.checkpoints.pop()

    def cmd_add_cs(self, player, msg, channel):
        # magic values that should give 511-512 ups
        walk_frames = 12
        strafe_frames = 69
        strafe_angle = 250
        try:
            if len(msg) > 1:
                walk_frames = int(msg[1])
        except:
            pass
        try:
            if len(msg) > 2:
                strafe_frames = int(msg[2])
        except:
            pass
        try:
            if len(msg) > 3:
                strafe_angle = int(msg[3])
        except:
            pass
        self.bot.add_cs_start(walk_frames, strafe_frames, strafe_angle)

    def handle_frame(self):
        if self.bot is not None:
            if self.bot.run_frame() == False:
                self.bot = None


class Point:
    position = [0, 0, 0]
    angles = [0, 0, 0]
    ground_ent = -1
    name = ""

    def __init__(self, name="") -> None:
        self.name = name

    @staticmethod
    def from_player(player, name=""):
        p = Point(name)
        p.position = player.state.position
        p.angles = [
            0,
            player.state.viewangles[1],
            0,
        ]
        p.ground_ent = player.state.ground_entity
        return p


class MapConfig:
    start_point = Point("start")
    checkpoints = []
    end_point = Point("end")

    @staticmethod
    def get_reward(position, velocity):
        remaining_points = MapConfig.get_remaining_points(position)

        # VELOCITY DIRECTION
        # TODO lerp direction towards next point.position or
        # current point.angles (forward) when near the point
        want_direction = MathHelper.vec3_norm(
            MathHelper.vec3_sub(remaining_points[0].position, position)
        )
        direction_reward = MathHelper.vec_dot(want_direction, velocity, 3)

        # VELOCITY MAGNITUDE
        velocity_reward = MathHelper.vec2_len(velocity)

        # DISTANCE TO ROUTE
        previous_point = MapConfig.get_previous_point(remaining_points[0])
        closest = remaining_points[0]
        if previous_point != None:
            closest = MathHelper.line_closest_point_clamped(
                previous_point.position, remaining_points[0].position, position
            )
        distance = MathHelper.vec3_dist(position, closest)
        distance_reward = 1.0 / distance

        return (
            #
            100.0 * distance_reward
            + 1.0 * direction_reward
            + 5.0 * velocity_reward
        )

    # get a list of all the points we haven't passed yet
    # NOTE: always includes end_zone.point even if past it
    @staticmethod
    def get_remaining_points(position):
        points = [MapConfig.start_point]
        for cp in MapConfig.checkpoints:
            points.append(cp)
        points.append(MapConfig.end_point)

        nearest_index = -1
        nearest_dist = math.inf
        for i in range(0, len(points)):
            dist = MathHelper.vec3_dist(position, points[i].position)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_index = i

        if nearest_index < len(points) - 1:
            # are we past nearest point?
            forward = MathHelper.vec3_sub(
                points[nearest_index + 1].position, points[nearest_index].position
            )
            to_nearest = MathHelper.vec3_sub(points[nearest_index].position, position)
            if MathHelper.vec_dot(to_nearest, forward, 3) > 0:
                next_index = nearest_index
            else:
                next_index = nearest_index + 1
        else:
            next_index = nearest_index

        return points[next_index:]

    @staticmethod
    def get_previous_point(point):
        points = [MapConfig.start_point]
        for cp in MapConfig.checkpoints:
            points.append(cp)
        points.append(MapConfig.end_point)
        for i in range(len(points)):
            if points[i].name == point.name:
                if i > 0:
                    return points[i - 1]
                break
        return None


class Actions(IntEnum):
    LEFT_DIAG = 0
    RIGHT_DIAG = 1
    LEFT = 2
    RIGHT = 3
    MAX_ACTION = 4


TURN_SPEED_MAX = 180
TURN_SPEED_INTERVAL = 3
INPUT_FRAME_INTERVAL = 50


class StrafeBot(minqlx.Player):
    playback_frame = -1
    # action, position, velocity, viewangles, ground_entity, jump_time, double_jumped
    history = []
    playback = False
    solve = False
    best_solution = None
    last_solution = None
    measure_next_frame = False
    save_next_frame = False
    queued_actions = []

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
        self.queued_actions = []
        self.best_solution = StrafeBot.empty_solution()
        self.last_solution = StrafeBot.empty_solution()

    def set_start(self):
        self.reset()
        self.teleport(
            MapConfig.start_point.position,
            (0, 0, 0),
            (0, MapConfig.start_point.angles[1], 0),
            MapConfig.start_point.ground_ent,
            0,
            0,
        )
        self.history.append(
            [
                StrafeBot.empty_solution(),
                [
                    MapConfig.start_point.position[0],
                    MapConfig.start_point.position[1],
                    MapConfig.start_point.position[2],
                ],
                [0, 0, 0],
                [0, MapConfig.start_point.angles[1], 0],
                MapConfig.start_point.ground_ent,
                0,
                0,
            ]
        )

    def add_cs_start(self, walk_frames, strafe_frames, strafe_angle):
        self.save_next_frame = True
        self.queued_actions.extend(
            StrafeBot.get_cs_actions(walk_frames, strafe_frames, strafe_angle)
        )

    def start_playback(self):
        if len(self.history) > 0:
            self.teleport(
                self.history[0][1],
                self.history[0][2],
                self.history[0][3],
                self.history[0][4],
                self.history[0][5],
                self.history[0][6],
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
                self.history[-1][1],
                self.history[-1][2],
                self.history[-1][3],
                self.history[-1][4],
                self.history[-1][5],
                self.history[-1][6],
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

        # determinism!
        self.teleport(
            self.history[self.playback_frame][1],
            self.history[self.playback_frame][2],
            self.history[self.playback_frame][3],
            self.history[self.playback_frame][4],
            self.history[self.playback_frame][5],
            self.history[self.playback_frame][6],
        )

        return self.run_action(self.history[self.playback_frame][0])

    def run_solve_frame(self):
        if len(self.queued_actions) > 0:
            act = self.queued_actions.pop(0)

            if self.save_next_frame == True:
                # store history for each past frame in INPUT_FRAME_INTERVAL
                self.history.append(
                    [
                        act,
                        self.state.position,
                        self.state.velocity,
                        self.state.viewangles,
                        self.state.ground_entity,
                        self.state.jump_time,
                        self.state.double_jumped,
                    ]
                )

            return self.run_action(act)

        # 1 frame delay so run_action applies new position
        if self.save_next_frame == True:
            self.save_next_frame = False
            self.history.append(
                [
                    StrafeBot.empty_solution(),
                    self.state.position,
                    self.state.velocity,
                    self.state.viewangles,
                    self.state.ground_entity,
                    self.state.jump_time,
                    self.state.double_jumped,
                ]
            )

        # 1 frame delay so run_action applies new position
        if self.measure_next_frame == True:
            self.measure_next_frame = False
            old_reward = self.last_solution[2]
            self.last_solution[2] = MapConfig.get_reward(
                self.state.position, self.state.velocity
            )

            if self.last_solution[2] > self.best_solution[2]:
                self.best_solution = [
                    self.last_solution[0],
                    self.last_solution[1],
                    self.last_solution[2],
                ]

            # were we turning?
            if old_reward > self.last_solution[2] and self.last_solution[0] in [
                Actions.LEFT,
                Actions.RIGHT,
            ]:
                if self.last_solution[1] > TURN_SPEED_INTERVAL:
                    # turning faster is giving less reward, don't bother iterating through remaining angles
                    if self.last_solution[0] == Actions.LEFT:
                        self.last_solution[0] = Actions.RIGHT
                        self.last_solution[
                            1
                        ] = 0  # incremented to TURN_SPEED_INTERVAL below
                    elif self.last_solution[1] == Actions.RIGHT:
                        # tried all inputs
                        return self.solve_frame_advance(self.best_solution)

        # iterate through inputs
        if self.last_solution[0] == Actions.MAX_ACTION:
            self.last_solution[0] = Actions.LEFT_DIAG

        elif self.last_solution[0] == Actions.LEFT_DIAG:
            self.last_solution[0] = Actions.RIGHT_DIAG

        elif self.last_solution[0] == Actions.RIGHT_DIAG:
            self.last_solution[0] = Actions.LEFT
            self.last_solution[1] = TURN_SPEED_INTERVAL

        elif self.last_solution[0] == Actions.LEFT:
            self.last_solution[1] += TURN_SPEED_INTERVAL
            if self.last_solution[1] > TURN_SPEED_MAX:
                self.last_solution[0] = Actions.RIGHT
                self.last_solution[1] = TURN_SPEED_INTERVAL

        elif self.last_solution[0] == Actions.RIGHT:
            self.last_solution[1] += TURN_SPEED_INTERVAL
            if self.last_solution[1] > TURN_SPEED_MAX:
                # tried all inputs
                return self.solve_frame_advance(self.best_solution)

        # run the same solution INPUT_FRAME_INTERVAL frames in a row
        return self.solve_frame_measure()

    def solve_frame_measure(self):
        self.teleport(
            self.history[-1][1],
            self.history[-1][2],
            self.history[-1][3],
            self.history[-1][4],
            self.history[-1][5],
            self.history[-1][6],
        )
        self.measure_next_frame = True
        for i in range(INPUT_FRAME_INTERVAL - 1):
            self.queued_actions.append(self.last_solution)
        success = self.run_action(self.last_solution)
        return success

    def solve_frame_advance(self, solution):
        self.history[-1][0] = solution
        self.teleport(
            self.history[-1][1],
            self.history[-1][2],
            self.history[-1][3],
            self.history[-1][4],
            self.history[-1][5],
            self.history[-1][6],
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
        for i in range(INPUT_FRAME_INTERVAL - 1):
            self.queued_actions.append(solution)
        return success

    def idle_frame(self):
        return self.run_action([Actions.MAX_ACTION])

    def teleport(self, pos, vel, ang, ground_entity=-1, jump_time=-1, double_jumped=-1):
        minqlx.set_position(self.id, minqlx.Vector3(pos))
        minqlx.set_velocity(self.id, minqlx.Vector3(vel))
        minqlx.set_viewangles(self.id, minqlx.Vector3(ang))
        if ground_entity >= 0:
            minqlx.set_ground_entity(self.id, ground_entity)
        if jump_time >= 0:
            minqlx.set_jump_time(self.id, jump_time)
        if double_jumped >= 0:
            minqlx.set_double_jumped(self.id, double_jumped)

    @staticmethod
    def get_cs_actions(walk_frames, strafe_frames, strafe_angle):
        actions = []
        total_frames = walk_frames + strafe_frames
        turn_rate = (125 / strafe_frames) * strafe_angle
        for i in range(total_frames):
            actions.append(
                [
                    Actions.LEFT,
                    turn_rate if i >= walk_frames else 0.0,
                    -math.inf,
                    False if i < total_frames - 1 else True,
                ]
            )
        return actions

    def run_action(self, action):
        max_ground_speed = 320.0
        velocity = self.state.velocity
        vel_len = MathHelper.vec2_len(velocity)
        grounded = self.state.grounded
        jump = (
            grounded and vel_len > max_ground_speed and action[0] != Actions.MAX_ACTION
        )
        # disallow jump arg, e.g. when circle strafing
        if len(action) >= 4 and action[3] == False:
            jump = False
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
                turn = action[1] * frametime
            elif act == Actions.RIGHT:
                act = Actions.RIGHT_DIAG
                turn = -action[1] * frametime

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
                if vel_len > 0.1:
                    yaw_change = action[1] * frametime
                    if action[0] == Actions.RIGHT:
                        yaw_change = -yaw_change
                    vel_yaw = MathHelper.get_yaw(
                        [velocity[0], velocity[1], velocity[2]]
                    )
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
        a = [v[0], v[1], v[2]]
        len = MathHelper.vec3_len(a)
        a[0] /= len
        a[1] /= len
        a[2] /= len
        return a

    @staticmethod
    def vec3_add(v, w):
        return [v[0] + w[0], v[1] + w[1], v[2] + w[2]]

    @staticmethod
    def vec3_sub(v, w):
        return [v[0] - w[0], v[1] - w[1], v[2] - w[2]]

    @staticmethod
    def vec3_scale(v, a):
        return [v[0] * a, v[1] * a, v[2] * a]

    @staticmethod
    def vec3_dist(v, w):
        return MathHelper.vec3_len([v[0] - w[0], v[1] - w[1], v[2] - w[2]])

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

    @staticmethod
    def line_closest_point(start, end, pos):
        norm = MathHelper.vec3_norm(MathHelper.vec3_sub(end, start))
        to_pos = MathHelper.vec3_sub(pos, start)
        frac = MathHelper.vec_dot(to_pos, norm, 3)
        return MathHelper.vec3_add(start, MathHelper.vec3_scale(norm, frac))

    @staticmethod
    def line_closest_point_clamped(start, end, pos):
        closest = MathHelper.line_closest_point(start, end, pos)

        # closest is a point projected onto the line
        # and can be outside the line segment, clamp.
        line_dot = MathHelper.vec_dot(start, end, 3)
        closest_dot = MathHelper.vec_dot(closest, end, 3)

        if line_dot * closest_dot > 0:
            # same direction
            if MathHelper.vec3_dist(start, end) < MathHelper.vec3_dist(closest, end):
                closest = start
        else:
            # opposite
            if MathHelper.vec3_dist(start, end) < MathHelper.vec3_dist(closest, start):
                closest = end

        return closest
