# qlsb

## Docker
```
docker build -t qlsb .
docker run -d -p 27960:27960 -p 27960:27960/udp -p 28960:28960 --cap-add=SYS_NICE qlsb
# interactive:
docker run -it -p 27960:27960 -p 27960:27960/udp -p 28960:28960 --cap-add=SYS_NICE qlsb
```

## Credits
- https://github.com/MinoMino/minqlx
- https://github.com/QLRace/minqlx
- https://github.com/QLRace/minqlx-plugins
- https://github.com/QLRace/server-settings