from django.shortcuts import render
from django.http import JsonResponse
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
import os
from openai import OpenAI
from django.conf import settings
from django.template.loader import get_template
from django.http import HttpResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

openAI_client = OpenAI(api_key=settings.OPENAI_API_KEY)

def index(request):
    template_name = 'chatbot/index.html'
    try:
        template = get_template(template_name)
        return render(request, template_name)
    except Exception as e:
        return HttpResponse(f"Template not found: {template_name}. Error: {e}")

def process_audio(request):
    if request.method == 'POST':
        # Receive the audio file
        if 'audio' not in request.FILES:
            print('No audio file provided')
            return JsonResponse({'error': 'No audio file provided'}, status=400)

        audio_file = request.FILES['audio']
        print(f'Received audio file: {audio_file.name}')
        print(f'File details: {audio_file}')

        audio_path = default_storage.save('audio.webm', ContentFile(audio_file.read()))
        print(f'Audio file saved to: {audio_path}')

        try:
            # Speech - to - text
            audio_content = default_storage.open(audio_path).read()
            print(f'Audio content length: {len(audio_content)} bytes')

            client_options = {"api_key": settings.GOOGLE_API_KEY}
            client = speech.SpeechClient(client_options=client_options)

            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                language_code="lt-LT",
            )

            response = client.recognize(config=config, audio=audio)
            print(f"response: {response}")

            if not response.results:
                print('No recognition results')
                return JsonResponse({'error': 'No recognition results'}, status=400)

            transcript = response.results[0].alternatives[0].transcript
            print(f"transcript: {transcript}")

            # Answer the question using gpt-3
            gpt3_output = None
            while gpt3_output is None:
                gpt3_response = openAI_client.chat.completions.create(model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Tu esi pagalbinis asistentas lietuvių kalba."},
                    {"role": "user", "content": transcript}
                ])
                gpt3_output = gpt3_response.choices[0].message.content.strip()
            print(f"GPT-3 output: {gpt3_output}")

            # Text - to - speech
            tts_client = texttospeech.TextToSpeechClient(client_options=client_options)
            synthesis_input = texttospeech.SynthesisInput(text=gpt3_output)
            voice = texttospeech.VoiceSelectionParams(
                language_code="lt-LT",
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            tts_response = tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )

            audio_output_path = os.path.join(settings.MEDIA_ROOT, 'output.mp3')
            print(f'Saving audio to: {audio_output_path}')
            with open(audio_output_path, 'wb') as out:
                out.write(tts_response.audio_content)

            print(f"Audio saved to {audio_output_path}")

            return JsonResponse({'transcript': transcript, 'gpt3_output': gpt3_output, 'audio_output_path': '/media/output.mp3'})

        except Exception as e:
            print(f"Error during audio processing: {e}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)