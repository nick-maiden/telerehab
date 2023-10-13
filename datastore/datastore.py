import os
import cv2
import orjson
import json
import datastore.const as const
from azure.storage.blob import BlobServiceClient
from PIL import Image
import numpy as np
from azure.storage.blob import BlobServiceClient
import shutil
import tempfile
import io
import base64

class DataStore:
    def __init__(self):
        self.poses = []
        self.images = None
        self.video_path = None

    def get_video_path(self, sid, clip_num):
        return os.path.join(tempfile.gettempdir(), self.get_video_name(sid, clip_num))

    def get_poses(self):
        return self.poses

    def set_poses(self, poses):
        if not isinstance(poses, list):
            raise TypeError('poses must be of type list')
        
        # restructure formatting of pose data so it's easier to interact with
        self.poses = list(map(lambda p: p[0], poses))

    def set_images(self, images):
        if not isinstance(images, list):
            raise TypeError('images must be of type list')
        self.images = images
    
    def populate_poses_local(self, sid, clip_num):
        ''' KEEP VERSION FOR LOCAL STORAGE UNTIL BLOB STORAGE FINALISED
        Populate clip dict with the contents of a specific clip file from local storage.
        Return true if clip file already existed, false otherwise.

        Args:   sid         (str)  - the uuid of the session being searched 
                clip_num    (int)  - the clip number of this clip           
        '''
        path = os.path.dirname(__file__)
        try:
            with open(path + "/sessions/poses/" + self.get_poses_name(sid, clip_num) + ".json", "r") as f:
                self.poses = orjson.loads(f.read())
            return True
        except FileNotFoundError:
            return False
        
    def populate_poses(self, sid, clip_num):
        '''Populate clip dict with the contents of a specific clip from a session from cloud storage.
        Return true if clip file already exists, false otherwise.

        Args:   sid         (str)  - the uuid of the session being searched 
                clip_num    (int)  - the clip number of this clip       
        '''
        # Create a blob client using the local file name as the name for the blob
        blob_service_client = BlobServiceClient.from_connection_string(const.AZ_CON_STR)
        blob_client = blob_service_client.get_blob_client(const.AZ_POSES_CONTAINER_NAME, self.get_poses_name(sid, clip_num))

        if blob_client.exists():
            # Download the blob from that clip as a string and convert to json
            pose_data_string = blob_client.download_blob().content_as_text()
            self.poses = json.loads(pose_data_string)
            return True
        else:
            # No blob exists, for the moment return false to signify this
            return False
        
    def populate_video(self, sid, clip_num):
        '''Load video from cloud storage into a video file, store path to this file
        in self.video_path. Return True on success, False if video does not exist
        in cloud storage.

        Args:   sid         (str)  - the uuid of the session being searched 
                clip_num    (int)  - the clip number of this clip       
        '''
        blob_service_client = BlobServiceClient.from_connection_string(const.AZ_CON_STR)
        blob_client = blob_service_client.get_blob_client(const.AZ_CLIPS_CONTAINER_NAME, self.get_video_name(sid, clip_num))
        if blob_client.exists():
            self.video_path = os.path.join(tempfile.gettempdir(), self.get_video_name(sid, clip_num))
            with open(self.video_path, "wb") as f:
                video_data = blob_client.download_blob()
                video_data.readinto(f)
            return True
        else:
            return False

    def write_poses_locally(self, sid, clip_num):
        '''Write a clip to local storage on the file system. If there is already data stored

        Args:
            sid (str) - the UUID of the session being written
        '''
        path = os.path.dirname(__file__)
        filename = self.get_poses_name(sid, clip_num) + ".json"
        file_path = os.path.join(path, "sessions", "poses", filename)

        # Check if the file already exists
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                existing_data = json.load(f)  # Load existing data from the file
        else:
            existing_data = []  # Create a new dictionary if the file doesn't exist

        # Update the existing data with the new frame data
        existing_data += self.poses
        with open(file_path, "w") as f:
            json.dump(existing_data, f, indent=4)

    def write_images_locally(self, sid, clip_num):
        '''Write the image data to local storage on the file system.

        Args:
            sid (str) - the UUID of the session being written
            clip_num (int) - the clip number of the session being written
        '''
        path = os.path.dirname(__file__)
        directory = os.path.join(path, "sessions", "images", self.get_images_name(sid, clip_num))
        os.makedirs(directory, exist_ok=True)

        start = self._get_next_image_number(directory)

        # # JPG
        # for i in range(len(self.images)):
        #     image = Image.open(io.BytesIO(base64.decodebytes(bytes(self.images[i], "utf-8"))))
        #     image.save(os.path.join(directory, f"img{start+i}.jpg"))


        # # RGB 
        for i, image_array in enumerate(self.images, start=start):
            image = Image.fromarray(np.array(image_array, dtype='uint8'))
            image.save(os.path.join(directory, f"img{i}.jpg"))

    def _get_next_image_number(self, directory):
        '''Get the next image number to be used in the given directory.

        Args:
            directory (str) - The directory to check for existing images.

        Returns:
            int - The next image number to be used.
        '''
        existing_files = os.listdir(directory)
        if existing_files:
            highest_num = max(int(f.split("img")[-1].split(".jpg")[0]) for f in existing_files if f.startswith("img") and f.endswith(".jpg"))
            return highest_num + 1
        else:
            return 0

    def write_poses_to_cloud(self, sid):
        '''Write pose data for all clips from a session to cloud storage.

        Args:
            sid (str) - the UUID of the session being written
        '''
        session_data = {}
        # Iterate through the local files in the sessions directory
        path = os.path.dirname(__file__)
        directory = os.path.join(path, "sessions", "poses")
        for filename in os.listdir(directory):
            if filename.startswith(f"poses_{sid}_"):
                file_path = os.path.join(directory, filename)
                with open(file_path, "r") as f:
                    clip_num = int(filename.split("_")[-1].split(".")[0])
                    session_data[clip_num] = json.load(f)

                # Delete the local file
                os.remove(file_path)

        # Upload the session data to Azure Blob Storage
        if session_data:
            # Create a blob service client
            blob_service_client = BlobServiceClient.from_connection_string(const.AZ_CON_STR)

            # Iterate through the session data and upload/update blobs
            for clip_num, frames in session_data.items():
                filename = self.get_poses_name(sid, clip_num)
                blob_client = blob_service_client.get_blob_client(const.AZ_POSES_CONTAINER_NAME, filename)

                if blob_client.exists():
                    # Shouldn't be reached, but handle this case just to be safe
                    downloaded_bytes = blob_client.download_blob().readall()
                    existing_data = json.loads(downloaded_bytes)
                    # Append the new frame to the existing clip data
                    existing_data.update(frames)
                    updated_clip_data_bytes = json.dumps(existing_data).encode('utf-8')

                    # Upload the updated clip data (overwrite with updated information)
                    blob_client.upload_blob(updated_clip_data_bytes, overwrite=True)
                else:
                    # Upload the clip data as a new blob
                    clip_data_bytes = json.dumps(frames).encode('utf-8')
                    blob_client.upload_blob(clip_data_bytes)


    def write_images_to_cloud(self, sid, fps=15):
        '''Convert directories of images stored on the file system into videos and upload to Azure.'''
        base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "datastore/sessions/images")
        
        # Iterate through all directories that start with images_sid
        for dir_name in os.listdir(base_path):
            if dir_name.startswith(f"images_{sid}_"):
                clip_num = dir_name.split('_')[-1]
                images_path = os.path.join(base_path, dir_name)
                images = sorted([img for img in os.listdir(images_path) if img.endswith('.jpg')], key=lambda x: int(x[3:len(x)-4]))

                # Get the first image to get dimensions
                image_path = os.path.join(images_path, images[0])
                frame = cv2.imread(image_path)
                height, width, _ = frame.shape

                video_name = f"vid_{sid}_{clip_num}.mp4"
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video = cv2.VideoWriter(video_name, fourcc, fps, (width, height))

                for image in images:
                    image_path = os.path.join(images_path, image)
                    frame = cv2.imread(image_path)
                    video.write(frame)

                video.release()

                # Upload the video to Azure Blob Storage
                blob_service_client = BlobServiceClient.from_connection_string(const.AZ_CON_STR)
                blob_client = blob_service_client.get_blob_client(const.AZ_CLIPS_CONTAINER_NAME, blob=video_name)
                with open(video_name, "rb") as f:
                    blob_client.upload_blob(f, overwrite=True)

                # Optionally, delete the local video file after uploading
                os.remove(video_name)
                # Delete the directory from the images directory after converting to a video and uploading
                shutil.rmtree(images_path)
        

    def delete_clip(self, sid, clip_num):
        '''Delete the poses and images blobs for a clip.

        Args:
            sid (str) - the UUID for the session that the clip being deleted belongs to
            clip_num (int) - the clip number of the clip being deleted
        '''
        blob_service_client = BlobServiceClient.from_connection_string(const.AZ_CON_STR)
        poses_blob_client = blob_service_client.get_blob_client(const.AZ_POSES_CONTAINER_NAME, self.get_poses_name(sid, clip_num))
        video_blob_client = blob_service_client.get_blob_client(const.AZ_CLIPS_CONTAINER_NAME, self.get_images_name(sid, clip_num))

        if poses_blob_client.exists():
            poses_blob_client.delete_blob()
        if video_blob_client.exists():
            video_blob_client.delete_blob()

    @classmethod
    def get_poses_name(cls, sid, clip_num):
        '''Return the name that should be used to identify the file containing poses for this clip.

        Args:   sid         (str)  - the uuid of the session being searched 
                clip_num    (int)  - the clip number of this clip   
        '''
        return f"poses_{sid}_{clip_num}"

    @classmethod
    def get_images_name(cls, sid, clip_num):
        '''Return the name that should be used to identify the directory containing images for this clip.

        Args:   sid         (str)  - the uuid of the session being searched 
                clip_num    (int)  - the clip number of this clip   
        '''
        return f"images_{sid}_{clip_num}"
    
    @classmethod
    def get_video_name(cls, sid, clip_num):
        '''Return the name that should be used to identify the video for a clip.

        Args:   sid         (str)  - the uuid of the session being searched 
                clip_num    (int)  - the clip number of this clip   
        '''
        return f"vid_{sid}_{clip_num}.mp4"

    
