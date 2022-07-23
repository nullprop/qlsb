#!/bin/bash
docker run -it \
    -p 27961:27961 \
    -p 27961:27961/udp \
    -p 28961:28961 \
    -v qlsb_steamapps_vol:/home/steam/qlds/steamapps \
    -v qlsb_redis_vol:/var/lib/redis \
    --cap-add=SYS_NICE qlsb