import os
# "ec2-13-53-139-90.eu-north-1.compute.amazonaws.com"
BACKEND_HOST = os.getenv("BACKEND_HOST", "ec2-13-53-139-90.eu-north-1.compute.amazonaws.com") #"127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", 5000))
FRONTEND_KEY = os.getenv("FRONTEND_KEY")