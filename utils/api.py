import requests
import json
import subprocess
import os
from PIL import Image
import random
from mutagen.mp3 import MP3
import time

process_kill = False

openai_api = ""
pexels_api = ""


def generate_script(title, duration):

    # Endpoint URL
    url = "https://api.openai.com/v1/chat/completions"

    # Headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openai_api}"
    }

    # Request payload
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": f"""title: {title}
                time limit: {duration} second
                Do not add more than time limit.
                the content should be read in time limit. 
                Do not add more than two paragraphs of content.
                Just write the content. 
                Do not add multiple readers. 
                Do not add extra informatin like 'fun fact for short video'. 
                Also do not add informatin like starting animation, ending animation, etc.
                also do not add information like headings, narrators, etc."""
            }
        ]
    }

    # Make the POST request
    try:
        response = requests.post(url, headers=headers, json=payload)
    except:
        return 1, "Failed to make request, Try Again!"

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        return 0, data['choices'][0]['message']['content']  # Print the JSON response with indentation
    else:
        return 1, f"Failed to make request: {response.status_code}"
    

def generate_audio(text, voice, speed, bg_music, bg_music_level):
    # API endpoint URL
    url = "https://api.openai.com/v1/audio/speech"


    # Headers
    headers = {
        "Authorization": f"Bearer {openai_api}",
        "Content-Type": "application/json"
    }

    # Payload dictionary
    data = {
        "model": "tts-1-hd",
        "input": text,
        "voice": voice,
        "speed": speed,
    }

    # Convert payload dictionary to JSON string
    data_json = json.dumps(data)

    # Make a POST request to the OpenAI API
    try:
        response = requests.post(url, headers=headers, data=data_json)
    except:
        return 1, "Failed to make request, Try Again!"


    # Check if the request was successful
    if response.status_code == 200:
        # Save the audio content to a file named speech.mp3
        with open("temp/speech.mp3", "wb") as file:
            file.write(response.content)
        if bg_music != "None":
            bg_music_file = f"""music/{bg_music}.mp3"""
            audio_cmd = f"""ffmpeg -y -i "temp/speech.mp3" -i "{bg_music_file}" -filter_complex "[0:a]volume=1[a];[1:a]volume={bg_music_level}[b];[a][b]amix=inputs=2:duration=first:dropout_transition=2" temp/final.mp3"""
            subprocess.call(audio_cmd, shell=True)
            return 0, "temp/final.mp3"
        if bg_music == "None":
            return 0, "temp/speech.mp3"
    else:
        return 1, f"Failed to make request: {response.status_code}"  # Print the error message if any
    


def generate_subtitles(audio_file):
    # API endpoint URL
    url = "https://api.openai.com/v1/audio/transcriptions"

    # Headers
    headers = {
        "Authorization": f"Bearer {openai_api}",
    }

    # Payload as multipart form-data
    payload = {
        "model": "whisper-1",
        "response_format": "srt",
    }

    # Open the audio file
    with open(audio_file, 'rb') as file:
        files = {'file': (audio_file, file, 'audio/mpeg')}

        # Make a POST request to the OpenAI API
        try:
            response = requests.post(url, headers=headers, data=payload, files=files)
        except:
            return 1, "Failed to make request, Try Again!"

        # Check if the request was successful
        if response.status_code == 200:
            # Print the transcription
            with open("temp/subtitles.srt", "w") as file:
                file.write(response.text)
            return 0, "temp/subtitles.srt"
        else:
            return 1, f"Failed to make request: {response.status_code}"  # Print the error message if any
        
def generate_images(query, per_page, page, frame):

    if frame == "16:9":
        orientation = "landscape"
    elif frame == "9:16":
        orientation = "portrait"
    elif frame == "1:1":
        orientation = "square"

    try:
        url = f"https://api.pexels.com/v1/search?query={query}&per_page={per_page}&orientation={orientation}&page={page}"
    except:
        return 1, "Failed to make request, Try Again!"

    headers = {
        "Authorization": pexels_api
    }

    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()
        image_urls = [photo["src"]["medium"] for photo in data["photos"]]
        return 0, image_urls
    else:
        return 1, f"Failed to make request: {response.status_code}"



def generate_video(images_files, voiceover_file, frame, font_name, font_size, font_color):

    exit_code, subtitles_file = generate_subtitles(voiceover_file)
    if exit_code != 0:
        return exit_code, subtitles_file
    
    audio = MP3(voiceover_file)
    duration = audio.info.length / len(images_files)

    

    if frame == "9:16":
        frame_resolution = (1080, 1920)
        size = "1080x1920"
    elif frame == "16:9":
        frame_resolution = (1920, 1080)
        size = "1920x1080"
    elif frame == "1:1":
        frame_resolution = (1080, 1080)
        size = "1080x1080"


    for img in images_files:
        im = Image.open(img)
        im = im.convert("RGB")
        im = im.resize(frame_resolution)
        im.save(img)


    video_cmd = """ffmpeg -y """
    for img in images_files:
        video_cmd += f"""-loop 1 -t {duration + 0.8} -i {img} """

    video_cmd += """-filter_complex \""""

    input_duration = duration + 0.8
    prev_xfade = 0
    xfade_duration = 1
    offset = input_duration + prev_xfade - xfade_duration
    if len(images_files) == 1:
        video_cmd += f""""""
    if len(images_files) == 2:
        video_cmd += f"""[0][1]xfade=transition=fade:duration=1:offset={offset},format=yuv420p;"""
    else:
        video_cmd += f"""[0][1]xfade=transition=distance:duration=1:offset={offset}[vfade1];"""
    prev_xfade = offset
    offset = input_duration + prev_xfade - xfade_duration

    transitions = ["horzclose", "horzopen", "vertclose", "vertopen", "diagbl", "diagbr", "diagtl", "diagtr"]

    for i in range(len(images_files) - 2):
        transition = random.choice(transitions)
        if i == len(images_files) - 3:
            video_cmd += f"""[vfade{i + 1}][{i + 2}]xfade=transition={transition}:duration=1:offset={offset},format=yuv420p;"""
        else:
            video_cmd += f"""[vfade{i + 1}][{i + 2}]xfade=transition={transition}:duration=1:offset={offset}[vfade{i + 2}];"""
        prev_xfade = offset
        offset = input_duration + prev_xfade - xfade_duration

    video_cmd += f"""\" -s {size} -aspect {frame} -threads 4 "temp/out.mp4"""

    color_code = {'white': "FFFFFF", 'red': "FF0000", 'green': '00FF00', 'blue': '0000FF', 'yellow': 'FFFF00', 'cyan': '00FFFF', 'magenta': 'FF00FF', 'gray': '808080'}

    subtitles_cmd = f"""ffmpeg -y -i temp/out.mp4 -i {voiceover_file} -vf \"subtitles=temp/subtitles.srt:force_style='FontName={font_name},FontSize={font_size},PrimaryColour=&H{color_code[font_color]}&,OutlineColour=&H000000&,BorderStyle=3,Outline=5,Shadow=0,MarginV=20'\" -map 0:v -map 1:a -c:v libx264 -c:a copy -threads 4 temp/output.mp4"""

    process1 = subprocess.Popen(video_cmd, shell=True)
    while process1.poll() is None:
        if process_kill:
            os.kill(process1.pid, 0)
            break;
        else:
            pass

        
    process2 = subprocess.Popen(subtitles_cmd, shell=True)
    while process2.poll() is None:
        if process_kill:
            os.kill(process2.pid, 0)
            break;
        else:
            pass

    return 0, os.getcwd()+"\\temp\\output.mp4"
