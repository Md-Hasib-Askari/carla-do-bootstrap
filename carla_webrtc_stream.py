import asyncio
import carla
import numpy as np

from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

pcs = set()
latest_frame = None

current_camera = None
current_vehicle = None
current_world = None
cam_blueprint = None

CAMERA_PRESETS = {
    "front":    carla.Transform(carla.Location(x=1.5, z=2.4)),
    "driver":   carla.Transform(carla.Location(x=0.3, y=-0.4, z=1.3)),
    "rear":     carla.Transform(carla.Location(x=-5.0, z=2.5), carla.Rotation(pitch=-10)),
    "top":      carla.Transform(carla.Location(x=0.0, z=8.0),  carla.Rotation(pitch=-90)),
    "hood":     carla.Transform(carla.Location(x=2.2, z=1.0),  carla.Rotation(pitch=-10)),
}


# ===============================
# CARLA CAMERA STREAM
# ===============================

class CarlaVideoTrack(VideoStreamTrack):
    async def recv(self):
        global latest_frame

        pts, time_base = await self.next_timestamp()

        if latest_frame is None:
            await asyncio.sleep(0.01)
            return await self.recv()

        frame = VideoFrame.from_ndarray(latest_frame, format="bgr24")
        frame.pts = pts
        frame.time_base = time_base
        return frame


# ===============================
# CARLA SENSOR CALLBACK
# ===============================

def process_image(image):
    global latest_frame

    array = np.frombuffer(image.raw_data, dtype=np.uint8)
    array = array.reshape((image.height, image.width, 4))
    latest_frame = array[:, :, :3]


# ===============================
# WEB SERVER
# ===============================

async def offer(request):
    params = await request.json()

    pc = RTCPeerConnection()
    pcs.add(pc)

    video = CarlaVideoTrack()
    pc.addTransceiver(video, direction="sendonly")

    offer_desc = RTCSessionDescription(sdp=params["offer"]["sdp"], type=params["offer"]["type"])
    await pc.setRemoteDescription(offer_desc)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.json_response(
        {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type,
        }
    )


async def list_vehicles(request):
    vehicles = current_world.get_actors().filter("vehicle.*")
    data = [
        {"id": v.id, "type": v.type_id, "current": v.id == current_vehicle.id}
        for v in vehicles
    ]
    return web.json_response(data)


async def set_vehicle(request):
    global current_camera, current_vehicle

    params = await request.json()
    vehicle_id = params.get("vehicle_id")

    vehicles = {v.id: v for v in current_world.get_actors().filter("vehicle.*")}
    if vehicle_id not in vehicles:
        return web.json_response({"error": f"Vehicle {vehicle_id} not found"}, status=404)

    if current_camera is not None:
        current_camera.stop()
        current_camera.destroy()

    current_vehicle = vehicles[vehicle_id]
    current_camera = current_world.spawn_actor(
        cam_blueprint,
        CAMERA_PRESETS["front"],
        attach_to=current_vehicle,
    )
    current_camera.listen(process_image)

    return web.json_response({"ok": True, "vehicle_id": vehicle_id})


async def set_camera(request):
    global current_camera

    params = await request.json()
    preset = params.get("preset", "front")

    if preset not in CAMERA_PRESETS:
        return web.json_response({"error": f"Unknown preset '{preset}'"}, status=400)

    if current_camera is not None:
        current_camera.stop()
        current_camera.destroy()

    current_camera = current_world.spawn_actor(
        cam_blueprint,
        CAMERA_PRESETS[preset],
        attach_to=current_vehicle,
    )
    current_camera.listen(process_image)

    return web.json_response({"ok": True, "preset": preset})


async def index(request):
    return web.FileResponse("index.html")


# ===============================
# MAIN
# ===============================

async def main():
    global current_camera, current_vehicle, current_world, cam_blueprint

    # connect to CARLA
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(10.0)

    current_world = client.get_world()
    bp = current_world.get_blueprint_library()

    vehicle_bp = bp.filter("vehicle.*model3*")[0]
    spawn = current_world.get_map().get_spawn_points()[0]

    current_vehicle = current_world.spawn_actor(vehicle_bp, spawn)

    cam_blueprint = bp.find("sensor.camera.rgb")
    cam_blueprint.set_attribute("image_size_x", "800")
    cam_blueprint.set_attribute("image_size_y", "600")

    current_camera = current_world.spawn_actor(
        cam_blueprint,
        CAMERA_PRESETS["front"],
        attach_to=current_vehicle,
    )

    current_camera.listen(process_image)

    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_post("/offer", offer)
    app.router.add_get("/vehicles", list_vehicles)
    app.router.add_post("/set_vehicle", set_vehicle)
    app.router.add_post("/set_camera", set_camera)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

    print("WebRTC server started at http://localhost:8080")

    while True:
        await asyncio.sleep(3600)


asyncio.run(main())