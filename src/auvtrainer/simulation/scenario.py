scenario = {
    "name": "test_rgb_camera",
    "world": "SimpleUnderwater",
    "package_name": "Ocean",
    "main_agent": "auv0",
    "ticks_per_sec": 30,
    "agents": [
        {
            "agent_name": "auv0",
            "agent_type": "HoveringAUV",
            "sensors": [
                {
                    "sensor_type": "RGBCamera",
                    "socket": "CameraSocket",
                    "Hz": 20,
                    "configuration": {
                        "CaptureWidth": 512,
                        "CaptureHeight": 512
                    }
                },
                {
                    "sensor_type": "DepthSensor",
                    "socket": "DepthSocket",
                    "Hz": 20,
                    "configuration": {
                        "Sigma": 0.255
                    }
                }
            ],
            "control_scheme": 0,
            "location": [0, 0, -10]
        }
    ]
}