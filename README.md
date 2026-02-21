# CARLA 0.9.15 on DigitalOcean GPU (no snapshots)

## Assumption
Your GPU droplet image already supports Docker + NVIDIA GPU runtime.
Verify:
```bash
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

## Repo layout

```
carla-do-bootstrap/
  README.md
  run_carla.sh
  stop_carla.sh
  record_mp4.py
  requirements.txt
```

---

# How to use this in real life (your exact flow)

### On every fresh droplet

```bash
git clone https://github.com/Md-Hasib-Askari/carla-do-bootstrap.git
cd carla-do-bootstrap
chmod +x run_carla.sh stop_carla.sh
./run_carla.sh

sudo apt update
sudo apt install -y ffmpeg python3-pip
pip3 install -r requirements.txt

python3 record_mp4.py
```

---

## Start CARLA (droplet)

```bash
chmod +x run_carla.sh stop_carla.sh
./run_carla.sh
docker logs -f carla
```

## Record MP4 (droplet)

Install deps:

```bash
sudo apt update
sudo apt install -y ffmpeg python3-pip
pip3 install -r requirements.txt
```

Record:

```bash
python3 record_mp4.py
# output default: /root/carla_drive.mp4
```

Customize recording:

```bash
FPS=10 W=640 H=360 DURATION_SECONDS=60 OUT_MP4=/root/out.mp4 python3 record_mp4.py
```

## Download the MP4 (from your laptop)

```bash
scp root@DROPLET_IP:/root/carla_drive.mp4 .
```

## Stop CARLA (droplet)

```bash
./stop_carla.sh
```

