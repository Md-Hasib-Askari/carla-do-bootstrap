import carla
import gc
import time

def cleanup_carla(client, world, vehicles, sensors):
    """
    Cleanup function to properly destroy CARLA actors and free resources.
    
    Args:
        client: CARLA client object
        world: CARLA world object
        vehicles: List of vehicle actors
        sensors: List of sensor actors
    """
    
    print("Starting CARLA cleanup...")
    
    try:
        # Destroy sensors first
        for sensor in sensors:
            if sensor.is_alive:
                sensor.destroy()
        print(f"Destroyed {len(sensors)} sensors")
        
        # Destroy vehicles
        for vehicle in vehicles:
            if vehicle.is_alive:
                vehicle.destroy()
        print(f"Destroyed {len(vehicles)} vehicles")
        
        # Set synchronous mode off
        settings = world.get_settings()
        settings.synchronous_mode = False
        world.apply_settings(settings)
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
    
    finally:
        # Force garbage collection
        gc.collect()
        time.sleep(0.5)
        print("CARLA cleanup complete")

if __name__ == "__main__":
    try:
        client = carla.Client('localhost', 2000)
        client.set_timeout(10.0)
        world = client.get_world()
        
        vehicles = list(world.get_actors().filter('vehicle.*'))
        sensors = list(world.get_actors().filter('sensor.*'))
        
        cleanup_carla(client, world, vehicles, sensors)
        
    except Exception as e:
        print(f"Failed to connect to CARLA: {e}")