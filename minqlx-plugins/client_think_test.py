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


class client_think_test(minqlx.Plugin):
    def __init__(self):
        super().__init__()
        self.add_hook("client_think", self.handle_client_think)

    def handle_client_think(self, player, client_cmd):
        #client_cmd["forwardmove"] = 127
        print("client cmd player {}:".format(player.name))
        pprint(client_cmd)
        return client_cmd
