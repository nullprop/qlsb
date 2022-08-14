# qlsb

A work-in-progress Quake Live strafe bot for defrag (PQL).

https://user-images.githubusercontent.com/26773737/184548865-b7c3800d-ad9b-41b0-84ca-efe2d8e586a2.mp4

## Docker

Note: QL Client binds port 27960. Using the same (host) port in Docker will cause connections to fail silently.

```
docker build -t qlsb .
docker run -d -p 27961:27961 -p 27961:27961/udp -p 28961:28961 -v qlsb_steamapps_vol:/home/steam/qlds/steamapps -v qlsb_redis_vol:/var/lib/redis --cap-add=SYS_NICE qlsb
# interactive:
docker run -it -p 27961:27961 -p 27961:27961/udp -p 28961:28961 -v qlsb_steamapps_vol:/home/steam/qlds/steamapps -v qlsb_redis_vol:/var/lib/redis --cap-add=SYS_NICE qlsb
```

## Credits
- https://github.com/MinoMino/minqlx
- https://github.com/QLRace/minqlx
- https://github.com/QLRace/minqlx-plugins
- https://github.com/QLRace/server-settings
