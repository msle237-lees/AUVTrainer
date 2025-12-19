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
                    "Hz": 30,
                    "configuration": {
                        "CaptureWidth": 512,
                        "CaptureHeight": 512
                    }
                },
                {
                    "sensor_type": "DepthSensor",
                    "socket": "DepthSocket",
                    "Hz": 30,
                    "configuration": {
                        "Sigma": 0.255
                    }
                },
                {
                    "sensor_type": "IMUSensor",
                    "socket": "IMUSocket",
                    "Hz": 30,
                    "configuration": {
                        "AccelSigma": 0.00277,
                        "AngVelSigma": 0.00123,
                        "AccelBiasSigma": 0.00141,
                        "AngVelBiasSigma": 0.00388,
                        "ReturnBias": True
                    }
                }   
            ],
            "control_scheme": 0,
            "location": [0, 0, -10]
        }
    ]
}