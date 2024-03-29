import streamlit as st
from st_audiorec import st_audiorec

import openai
from gtts import gTTS
from clarifai_helpers import ClarifaiModel

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

import os
import json
from io import BytesIO
from textwrap import wrap
from urllib.request import urlopen



st.set_page_config('SightCom 2', '🤖')
st.title('SightCom 2 🤖')

openai.api_key = st.secrets['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']
with open('system_roles/main_role.txt', 'r') as f:
    main_role = f.read()
with open('system_roles/dalle_role.txt', 'r') as f:
    dalle_role = f.read()
with open('system_roles/qna_role.txt', 'r') as f:
    qna_role = f.read()

def speak(script):
    speech_bytes = BytesIO()
    tts = gTTS(script)
    tts.write_to_fp(speech_bytes)
    st.audio(speech_bytes)

cam = st.camera_input('Take a photo')
mode = st.radio('Choose input mode', ['speak', 'type'])
if mode == 'speak':
    audio_bytes = st_audiorec()
    if audio_bytes:
        file_name = 'temp_audio.mp3'
        with open(file_name, "wb") as f:
            f.write(audio_bytes)

        audio_file = open(file_name, 'rb')
        with st.spinner('Transcribing audio..'):
            query = openai.Audio.transcribe("whisper-1", audio_file, language='en')['text']
        
        audio_file.close()
        os.remove(file_name)
        st.write('Query: ' + query)
    else:
        query = ''
else:
    query = st.text_input('Type your query.')

if query:
    with st.spinner('Assigning role..'):
        classifier = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": main_role},
                {"role": "user", "content": query}
            ]
        )
    category = classifier.choices[0].message.content
    st.write(category)
    category = category.lower()

    if 'image generation' in category:
        with st.spinner('Creating Descriptions..'):
            art_creator = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": dalle_role},
                    {"role": "user", "content": query}
                ]
            )

        response = art_creator.choices[0].message.content
        prompts = json.loads(response)['generated_prompts']

        n = len(prompts)
        nrows = int(np.ceil(np.sqrt(n)))
        ncols = int(np.ceil(n / nrows))
        fig, axes = plt.subplots(nrows, ncols, figsize=(5*ncols, 5*nrows))

        for i, (ax, prom) in enumerate(zip(axes.ravel(), prompts)):
            with st.spinner(f'{i+1}. {prom}'):           
                data = openai.Image.create(
                    prompt=prom,
                    n=1,
                    size="512x512"
                )
            img_url = data['data'][0]['url']
            
            img = np.array(Image.open(urlopen(img_url)))
            ax.imshow(img)

            title = "\n".join(wrap(prom, 40))
            ax.set_title(title)
            ax.axis('off')

        plt.tight_layout()
        st.pyplot(fig)
        speak(' '.join(prompts))

    elif 'questions' in category:
        with st.spinner('Generating answer..'):
            qna_bot = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": qna_role},
                    {"role": "user", "content": query}
                ]
            )
        answer = qna_bot.choices[0].message.content
        st.info('Answer: ' + answer)
        speak(answer)

    elif 'image captioning' in category:
        if cam:
            image_captioner = ClarifaiModel(st.secrets['d5ce30a4f98646deb899a19ff4becaad'], 'salesforce', 'blip', 'general-english-image-caption-blip-2')
            image = Image.open(cam)
            with st.spinner('Running Image Captioning..'):
                response = image_captioner.run(image)
            caption = response.data.text.raw
            st.info('Caption: ' + caption)
            speak(caption)
        else:
            st.warning('take a photo first')

    elif 'ocr' in category:
        if cam:
            ocr = ClarifaiModel(st.secrets['46e99516c2d94f58baf2bcaf5a6a53a9'], 'clarifai', 'main', 'ocr-scene-english-paddleocr')
            image = Image.open(cam)
            with st.spinner('Running Text Recognition..'):
                response = ocr.run(image)
            text = []
            for region in response.data.regions:
                text.append(region.data.text.raw)
            if text:
                text_str = ' '.join(text)
                st.info('Text: ' + text_str)
                speak(text_str)
            else:
                st.warning('No Text Found!')
        else:
            st.warning('take a photo first')

    elif 'color recognition' in category:
        if cam:
            color_recognizer = ClarifaiModel(st.secrets['dd9458324b4b45c2be1a7ba84d27cd04'], 'clarifai', 'main', 'color-recognition')
            image = Image.open(cam)
            with st.spinner('Running Color Recognition..'):
                response = color_recognizer.run(image)
            color = response.data.colors[0].w3c.name
            st.info('Color: ' + color)
            speak(color)
        else:
            st.warning('take a photo first')

    else:
        st.warning('Role cannot be assigned.')
