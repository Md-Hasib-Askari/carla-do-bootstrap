import carla
import numpy as np
import subprocess
import time
import queue
import random
import os

HOST = os.getenv("CARLA_HOST", "127.0.0.1")
PORT = int(os.getenv("CARLA_PORT", "2000"))
TM_PORT = int(os.getenv("CARLA_TM_PORT", "8000"))

OUT_MP4 = os.getenv("OUT_MP4", "/root/carla_drive.mp4")
W = int(os.getenv("W", "1280"))
H = int(os.getenv("H", "720"))
FPS = int(os.getenv("FPS", "20"))
DURATION_SECONDS = int(os.getenv("DURATION_SECONDS", "30"))

frame_q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=2)

def on_image(img: carla.Image):
    arr = np.frombuffer(img.raw_data, dtype=np.uint8).reshape(img.height, img.width, 4)
    bgr = arr[:, :, :3]  # BGR for ffmpeg bgr24
    if frame_q.full():
        try:
            frame_q.get_nowait()
        except queue.Empty:
            pass
    frame_q.put_nowait(bgr)

def main():
    client = carla.Client(HOST, PORT)
    client.set_timeout(30.0)
    world = client.get_world()

    settings = world.get_settings()
    prev_sync = settings.synchronous_mode
    prev_fds = settings.fixed_delta_seconds

    # Deterministic stepping for stable FPS recording
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 1.0 / FPS
    world.apply_settings(settings)

    tm = client.get_trafficmanager(TM_PORT)
    tm.set_synchronous_mode(True)

    bp_lib = world.get_blueprint_library()

    # Optional: remove any previous RGB cameras (helps reruns)
    for a in world.get_actors().filter("sensor.camera.rgb"):
        try:
            a.destroy()
        except Exception:
            pass

    # Spawn a vehicle safely
    vehicle_bp = bp_lib.filter("vehicle.tesla.model3")[0]
    spawn_points = world.get_map().get_spawn_points()
    random.shuffle(spawn_points)

    vehicle = None
    for sp in spawn_points:
        vehicle = world.try_spawn_actor(vehicle_bp, sp)
        if vehicle:
            break
    if not vehicle:
        raise RuntimeError("Could not spawn vehicle (all spawn points blocked).")

    vehicle.set_autopilot(True, TM_PORT)

    # Camera
    cam_bp = bp_lib.find("sensor.camera.rgb")
    cam_bp.set_attribute("image_size_x", str(W))
    cam_bp.set_attribute("image_size_y", str(H))
    cam_bp.set_attribute("fov", "90")
    cam_bp.set_attribute("sensor_tick", str(1.0 / FPS))

    camera = world.spawn_actor(
        cam_bp,
        carla.Transform(carla.Location(x=-7, z=3), carla.Rotation(pitch=-15)),
        attach_to=vehicle,
    )
    camera.listen(on_image)

    # ffmpeg: raw BGR frames -> H.264 mp4
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "bgr24",
        "-s", f"{W}x{H}",
        "-r", str(FPS),
        "-i", "-",  # stdin
        "-an",
        "-vcodec", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        OUT_MP4,
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    frames_written = 0
    start = time.time()

    try:
        while time.time() - start < DURATION_SECONDS:
            world.tick()

            # drain queue to keep latest frame (no backlog lag)
            frame = None
            while not frame_q.empty():
                frame = frame_q.get_nowait()

            if frame is not None:
                proc.stdin.write(frame.tobytes())
                frames_written += 1

    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        proc.wait()

        try:
            camera.stop()
        except Exception:
            pass
        try:
            camera.destroy()
        except Exception:
            pass
        try:
            vehicle.destroy()
        except Exception:
            pass

        # Restore previous world settings
        settings = world.get_settings()
        settings.synchronous_mode = prev_sync
        settings.fixed_delta_seconds = prev_fds
        world.apply_settings(settings)

    print(f"✅ Saved: {OUT_MP4}")
    print(f"Frames: {frames_written}  (~{frames_written / FPS:.1f}s at {FPS} FPS)")

if __name__ == "__main__":
    main()