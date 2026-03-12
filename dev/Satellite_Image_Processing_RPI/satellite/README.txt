SATELLITE EMULATION THROUGH FAAS

★ OVERVIEW

This repository demonstrates a Satellite Image Processing System using Function as a Service (FaaS). The system simulates a satellite sending images to a cloud function for processing and returning the processed image
to a client application. The architecture uses OpenFaaS to deploy and execute the satellite function, while a Python-based client application sends requests and receives processed images. This setup allows testing 
of serverless image processing pipelines using a simulated satellite environment.

★ FEATURES

● On-Demand Function Execution: The satellite processing function is triggered only when a client request is received.
● Secure HTTPS Communication: Communication between the client and the FaaS gateway is performed using secure HTTPS connections.
● Remote Access via Subdomain Tunnel: A reverse tunnel with a registered subdomain enables remote access to the OpenFaaS gateway.
● Automated Image Encoding and Transfer: Satellite images are encoded in Base64 format for efficient transmission through HTTP responses.
● Containerized Deployment: The satellite function runs inside a Docker container, ensuring portability and environment consistency.

★ DEPENDENCIES

Before running the satellite emulation, ensure the following setup are installed:

1. WSL Setup - https://github.com/bitresearch2006/setup_wsl

2. FAAS Setup - https://github.com/bitresearch2006/faas_setup

3. Sub domain registration - https://github.com/bitresearch2006/Sub_Domain_Register

★ INSTALLATION

Running the satellite emulation inside WSL provides a native Linux environment, which is fully compatible with tools like Docker, OpenFaaS and other Linux-based dependencies.
It also simplifies installation and improves stability.

1. Install venv Package

sudo apt install python3.12-venv

2. Create the Virtual Environment

python3 -m venv venv

3. Activate the Virtual Environment

source venv/bin/activate           # The (venv) confirms the environment is active

4. Install Required Python Packages

pip install pillow numpy requests flask

5. Run Local Satellite Emulator Test

cd /(move to your path)

python TestApp.py

Expected output - Fetching random image... Image name: xxxx.jpg, Image loaded successfully

This confirms local satellite emulation is working

6. Deploy function

This system is designed to automatically generate and deploy the OpenFaaS functions using Gradle

(i) Install Java (OpenJDK)

sudo apt update
sudo apt install openjdk-17-jdk

(ii) Verify Java Installation

java -version

(iii) Set JAVA_HOME

Find the Java path:
readlink -f $(which java)

Example output:
/usr/lib/jvm/java-17-openjdk-amd64/bin/java

So the JAVA_HOME should be:
/usr/lib/jvm/java-17-openjdk-amd64

Now set it temporarily:
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH

Verify:
echo $JAVA_HOME

(iv) Run the Gradle Command

Give permission to the script and then run
chmod +x gradlew
./gradlew faasAll

# Possibilities of errors and their fix

a) FAILURE: Build failed with an exception. * What went wrong: Task 'lint' not found in root project 'satellite'. Some candidates are: 'init'.

Fix: Disable tests for the FAAS build
export TEST_ENABLED=false

This tells the FAAS Docker build: skip lint and test steps

b) DEPRECATED: The legacy builder is deprecated
Install the buildx component to build images with BuildKit

Fix: Install Docker Buildx
sudo apt update
sudo apt install docker-buildx

Restart Docker service
sudo service docker restart

(v) Confirm Deployment

faas-cli list

Expexted output: Function     Invocations     Replicas
                 satellite       0               1

7. Run satellite emulation file

(i) Change nano file
sudo nano TestAppFAAS.py
# HOST = "<local IP address>" and 
  PORT = xxxx

(ii) Run the required file
python TestAppFAAS.py

8. Remote testing
Can be run in windows by using the "https://username.bitone.in" in the TestAppFAAS.py file and in browser

★ CONCLUSION

This project demonstrates a serverless satellite image processing pipeline using OpenFaaS.

The implemented system successfully:

● Deploys a satellite image processing function
● Simulates satellite image transmission
● Processes and returns image data using serverless architecture

This setup provides a simple framework for experimenting with cloud-based satellite data processing systems.

