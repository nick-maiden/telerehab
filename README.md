## telerehab
telerehab is designed to assist healthcare professionals (physiotherapists, occupational therapists, etc) when conducting a remote session with a patient. Using the mobile app, a patient is able to record themselves completing exercises prescribed by their clinician. Pose estimation is then run on this video data in real time and results may be viewed afterwards by the patient or their clinician.

The alternative way for clinicians to conduct remote sessions currently is via a video call, however telerehab presents several advantages over this method. Firstly, the recording of exercises by a patient and review by a clinician may be completed asynchronously. Most importantly however the utility of the data captured through pose estimation is far greater for a clinician, allowing them to do such things as view joint angles to determine range of motion through exercises. This is simply not possible with video data alone.

## How to run
1. Install Docker and ensure it is running.
2. Download Expo App on smartphone.
3. Run the following commands:
```
git clone git@github.com:nick-maiden/telerehab.git
cd telerehab
docker compose up
```
4. Open mobile app.
5. Enter connection code (local IP address) and backend port number (8000 by default) inside mobile app.
6. Use record button in mobile app to start and stop exercise recordings.
7. Access web app via:
```
http://(your-local-ip-address):8000/data/visualise2D/
```

## Future work
The first goal for telerehab moving forward is to validate results collected by the system to ensure that they meet clinical standards in terms of accuracy. Following this, the aim is to have the mobile app provide live feedback on exercise quality to the patient whilst they are completing the exercise, to ensure that they are performing their exercises correctly.
