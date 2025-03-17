import assemblyai as aai
import os
from dotenv import load_dotenv

load_dotenv()
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")
# You can use a local filepath:
# audio_file = "./example.mp3"
# Or use a publicly-accessible URL:

def transcribe_audio(audio_file, output_file, speackers_expected=2):
    config = aai.TranscriptionConfig(
        speaker_labels=False
    )
    transcript = aai.Transcriber().transcribe(audio_file, config)
    
    # Since we're not using speaker labels, we'll just get the full transcript
    transcription_text = transcript.text
    print(f"Transcription: {transcription_text}")
    
    # Write the transcription to the output file
    with open(output_file, "w") as f:
        f.write(transcription_text)
    
    # Return the transcription as a single string instead of a list of dialogues
    return transcription_text