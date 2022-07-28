#!/bin/bash

gamePort=27961
rconPort=28961
PRIVATE_PW=pootis
RCON_PW=pootis
STATS_PW=pootis

if [[ $1 == "turbo" ]]; then
    mode=0
    mapPool="mappool_qlrace.txt"
    hostname="Private - Turbo (PQL)"
elif [[ $1 == "classic" ]]; then
    mode=2
    mapPool="mappool_qlrace_classic.txt"
    hostname="Private - Classic (VQL)"
else
    exit 1
fi

echo "Starting redis..."
redis-server --daemonize yes
sleep 3

echo "Starting minqlx..."
exec /home/steam/qlds/run_server_x64_minqlx.sh \
    +set com_hunkmegs 128 \
    +set fs_homepath /home/steam/.quakelive/$gamePort \
    +set g_password $PRIVATE_PW \
    +set net_strict 1 \
    +set net_port $gamePort \
    +set sv_hostname $hostname \
    +set sv_mappoolFile $mapPool \
    +set sv_maxclients 16 \
    +set zmq_rcon_enable 1 \
    +set zmq_rcon_password $RCON_PW \
    +set zmq_rcon_port $rconPort \
    +set zmq_stats_enable 1 \
    +set zmq_stats_password $STATS_PW \
    +set qlx_raceMode $mode
