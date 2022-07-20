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

import minqlx
from pprint import pprint


class bot_test(minqlx.Plugin):
    client_num = -1

    def __init__(self):
        super().__init__()
        self.add_hook("client_think", self.handle_client_think)
        self.add_hook("frame", self.handle_frame)
        # self.allocate()
        # self.add()
        self.add_command("testbot", self.cmd_add)

    def handle_client_think(self, player, client_cmd):
        # client_cmd["forwardmove"] = 127
        # print("client cmd player {}:".format(player.name))
        # pprint(client_cmd)
        return client_cmd

    def cmd_add(self, player, msg, channel):
        self.client_num = minqlx.bot_add()
        print("bot_add: {}".format(self.client_num))
        player.tell("bot_add: {}".format(self.client_num))

    @minqlx.delay(3)
    def add(self):
        self.client_num = minqlx.bot_add()
        print("bot_add: {}".format(self.client_num))

    def handle_frame(self):
        if self.client_num >= 0:
            cmd = {
                "pitch": 0,
                "yaw": 0,
                "roll": 0,
                "buttons": 0,
                "weapon": 5,
                "weapon_primary": 5,
                "fov": 100,
                "forwardmove": 0,
                "rightmove": 0,
                "upmove": 0,
            }
            if minqlx.client_think(self.client_num, cmd) == False:
                self.client_num = -1
