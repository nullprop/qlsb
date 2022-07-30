# Debian 9 (stretch) Docker image for qlsb
#
#

FROM debian:stretch

# Deps
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -qy \
    sudo \
    git \
    build-essential \
    lib32gcc1 \
    lib32z1 \
    lib32stdc++6 \
    python3 \
    python3-dev \
    redis-server \
    wget
RUN apt-get -qy autoremove && apt-get -qy clean

# RUN wget https://bootstrap.pypa.io/get-pip.py
RUN wget https://bootstrap.pypa.io/pip/3.5/get-pip.py
RUN python3 get-pip.py
RUN rm get-pip.py

# steam user
RUN useradd -m steam
# RUN passwd steam pootis
USER steam

# env
ENV HOME /home/steam
ENV STEAMCMD $HOME/steamcmd
ENV QLDS $HOME/qlds
ENV DATA $QLDS/qlsb_data

# Steamcmd
RUN mkdir $STEAMCMD
WORKDIR $STEAMCMD
RUN wget https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz
RUN tar -xvzf steamcmd_linux.tar.gz

# qlds
RUN ./steamcmd.sh +force_install_dir $QLDS +login anonymous +app_update 349090 +quit
RUN chown steam:steam $QLDS

# minqlx
COPY --chown=steam:steam minqlx $HOME/minqlx
# needed for version.py (called from make)
COPY --chown=steam:steam .git $HOME/minqlx/.git
WORKDIR $HOME/minqlx
RUN make
RUN cp -r bin/* $QLDS

# minqlx-plugins
COPY --chown=steam:steam minqlx-plugins $QLDS/minqlx-plugins
WORKDIR $QLDS/minqlx-plugins
RUN python3 -m pip install -r requirements.txt

# server settings
COPY --chown=steam:steam server-settings $QLDS

# data dir
RUN mkdir $DATA
RUN chown steam:steam $DATA

# clean
RUN \
    rm -rf $HOME/minqlx && \
    rm -rf $STEAMCMD/steamcmd_linux.tar.gz

# run
USER root
WORKDIR $QLDS
ENTRYPOINT [ \
    "/usr/bin/nice", "-n", "-20", \
    "/usr/bin/ionice", "-c", "1", "-n", "1", "-t", \
    "/usr/bin/sudo", "--user", "steam", \
    "/home/steam/qlds/start_server.sh", "turbo" \
]
EXPOSE 27961
EXPOSE 27961/udp
EXPOSE 28961