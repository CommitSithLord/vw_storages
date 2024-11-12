# tasks.py

# tasks.py

from celery import shared_task
from celery.result import AsyncResult
from .celery import app as celery_app
import os
import requests
from urllib.parse import urlparse
from django.core.files.temp import NamedTemporaryFile
import base64
from django.conf import settings
import uuid


@shared_task
def upload_file_to_server(url, data, headers, file_path, file_name):
    with open(file_path, 'rb') as file:
        files = {'files': (file_name, file)}
        response = requests.post(url, data=data, headers=headers, files=files)

    # Check if the upload was successful (you can adjust the condition as needed)
    if response.status_code == 200:
        # Delete the file after successful upload
        os.remove(file_path)
        return response.text
    else:
        # Handle the case where the upload was not successful
        return f"File upload failed with status code {response.status_code}: {response.text}"


@shared_task
def check_upload_status(task_id):
    result = AsyncResult(task_id, app=celery_app)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result,
    }

@shared_task
def download_file_and_encode(url, cookie, filename, podname):
    url = url + "v1/file/download"
    headers = {
        'Cookie': cookie
    }
    files = {
        'filePath': (None, filename),
        'podName': (None, podname)
    }

    response = requests.post(url, headers=headers, files=files, stream=True)
        
    if response.status_code == 200:
        content = response.content
        base64_content = base64.b64encode(content).decode('utf-8')
        return {"file_content_base64": base64_content}
    else:
        return {"error": "File download failed"}


@shared_task
def download_and_upload(video_url):
    file_name = f"{uuid.uuid4()}.m4v"
    download_path = os.path.join(settings.MEDIA_ROOT, file_name)
    print(file_name, video_url, download_path)

    # Download the video from the URL and save it temporarily
    response = requests.get(video_url)
    with open(download_path, 'wb') as file:
        file.write(response.content)

    # Upload the downloaded file to the Swarm API
    url = 'https://dev.api.cast.video.wiki/bzz?name=' + str(file)
    print(url,"urrll")
    headers = {
        'swarm-postage-batch-id': '72bf988faf80cf1e962f210687f5c4193b66726e37c3f417b6685a6915d6a0f9',
        'Content-Type': 'video/webm'
    }
    with open(download_path, 'rb') as file:
        upload_response = requests.post(url, headers=headers, data=file)
    print(url, file)
    # Remove the downloaded file after upload
    os.remove(download_path)
    print(upload_response)
    return upload_response.json(), upload_response.status_code

@shared_task
def upload_video_task(file_url):
    parsed_url = urlparse(file_url)
    filename = parsed_url.path.split("/")[-1]
    if file_url.startswith("https://live1.decast.live"):
        parts = parsed_url.path.split("/")
        filename = parts[3] + ".m4v"
    
    url = f"https://storage.sia.video.wiki/api/worker/objects/videowiki/{filename}"

    resp = requests.get(file_url)
    binary_data = resp.content

    headers = {
        'Content-Type': 'video/webm',
        'Authorization': 'Basic OnBhc3N3b3Jk'
    }

    response = requests.put(url, headers=headers, data=binary_data)
    return {"filename": filename, "status_code": response.status_code, "response_text": response.text}

@shared_task
def download_video_task(file_name):
    headers = {
        'Authorization': 'Basic OnBhc3N3b3Jk',
        'Content-Type': 'video/webm'
    }
    url = f"https://storage.sia.video.wiki/api/worker/objects/videowiki/{file_name}"

    # Send GET request
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        binary_data = response.content
        encoded_data = base64.b64encode(binary_data).decode('utf-8')
        return {"binary_data": encoded_data}
    else:
        return {"error": "Failed to download file", "status_code": response.status_code}

@shared_task
def download_file(hash):
    url = f'https://dev.api.cast.video.wiki/bzz/{hash}'
    response = requests.get(url)
    if response.status_code == 200:
        binary_data = response.content
        encoded_data = base64.b64encode(binary_data).decode('utf-8')
        return {"binary_data": encoded_data}
        # return response.content
    else:
        return None



