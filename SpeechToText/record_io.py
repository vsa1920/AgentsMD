import pyaudio
import wave
import threading

class RecordingManager:
    # Audio recording parameters
    FORMAT = pyaudio.paInt16  # 16-bit format
    CHANNELS = 1  # Mono
    RATE = 44100  # Sample rate (Hz)
    CHUNK = 1024  # Buffer size
    DEFAULT_FILENAME = "recorded_audio.wav"

    def __init__(self):
        self.frames = []
        self.is_recording = False
        self.stop_event = None
        self.recording_thread = None
        self.audio = None
        self.stream = None

    def _record_audio(self):
        """Internal function to record audio until stop_event is set."""
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )

        while not self.stop_event.is_set():
            try:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                self.frames.append(data)
            except Exception as e:
                print(f"Error: {e}")
                break

        # Stop and close the stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()

    def start_recording(self):
        """Start recording audio."""
        if self.is_recording:
            return False
        
        self.frames = []
        self.stop_event = threading.Event()
        self.recording_thread = threading.Thread(target=self._record_audio)
        self.is_recording = True
        self.recording_thread.start()
        return True

    def stop_recording(self, filename=DEFAULT_FILENAME):
        """Stop recording and save the audio file."""
        if not self.is_recording:
            return False

        self.stop_event.set()
        self.recording_thread.join()
        self.is_recording = False

        # Save the recorded data to a WAV file
        if self.frames:
            with wave.open(filename, 'wb') as wf:
                audio = pyaudio.PyAudio()
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(audio.get_sample_size(self.FORMAT))
                wf.setframerate(self.RATE)
                wf.writeframes(b''.join(self.frames))
                audio.terminate()
            return True
        return False

    def is_currently_recording(self):
        """Check if currently recording."""
        return self.is_recording 
    
if __name__ == "__main__":
    recording_manager = RecordingManager()
    input("Press Enter to start recording...")
    recording_manager.start_recording()
    input("Press Enter to stop recording...")
    recording_manager.stop_recording("my_audio.wav")
    print("Audio recorded and saved as 'my_audio.wav'.")