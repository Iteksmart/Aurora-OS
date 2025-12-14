"""
Aurora OS - Voice Interface
Voice recognition and synthesis for hands-free AI interaction
Supports offline voice recognition and multiple languages
"""

import os
import sys
import json
import asyncio
import threading
import queue
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from pathlib import Path
import logging
from datetime import datetime

try:
    import speech_recognition as sr
    import pyttsx3
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    print("Voice libraries not available. Install with: pip install speechrecognition pyttsx3")

try:
    import numpy as np
    import sounddevice as sd
    from scipy.io import wavfile
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

@dataclass
class VoiceCommand:
    """Voice command structure"""
    text: str
    confidence: float
    timestamp: datetime
    language: str = "en-US"

@dataclass
class VoiceSettings:
    """Voice interface settings"""
    wake_word: str = "Aurora"
    language: str = "en-US"
    confidence_threshold: float = 0.7
    listening_timeout: int = 5
    voice_enabled: bool = True
    voice_rate: int = 150
    voice_volume: float = 0.9

class VoiceInterface:
    """
    Voice interface for Aurora OS
    Provides speech recognition and synthesis capabilities
    """
    
    def __init__(self, settings: VoiceSettings = None):
        self.settings = settings or VoiceSettings()
        self.recognizer = sr.Recognizer() if VOICE_AVAILABLE else None
        self.microphone = None
        self.tts_engine = None
        
        # State management
        self.is_listening_flag = False
        self.is_wake_word_active = False
        self.recognition_queue = queue.Queue()
        self.last_recognition = None
        
        # Callbacks
        self.on_command_received = None
        self.on_wake_word_detected = None
        
        # Audio settings
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
        
        self.logger = logging.getLogger("Aurora.VoiceInterface")
        self._setup_logging()
        
        # Initialize components
        self._init_voice_components()
        
    def _setup_logging(self):
        """Setup logging"""
        log_dir = Path("/var/log/aurora")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_dir / "voice_interface.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _init_voice_components(self):
        """Initialize voice recognition and synthesis"""
        try:
            if VOICE_AVAILABLE:
                # Initialize speech recognizer
                self.recognizer = sr.Recognizer()
                self.recognizer.energy_threshold = 300
                self.recognizer.dynamic_energy_threshold = True
                self.recognizer.pause_threshold = 0.8
                
                # Initialize microphone
                self.microphone = sr.Microphone()
                
                # Calibrate microphone
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
                self.logger.info("Speech recognition initialized")
            
            # Initialize text-to-speech
            self._init_tts()
            
        except Exception as e:
            self.logger.error(f"Failed to initialize voice components: {e}")
    
    def _init_tts(self):
        """Initialize text-to-speech engine"""
        try:
            if VOICE_AVAILABLE:
                self.tts_engine = pyttsx3.init()
                
                # Configure voice
                voices = self.tts_engine.getProperty('voices')
                
                # Prefer female voice for assistant
                for voice in voices:
                    if 'female' in voice.gender.lower() or 'zira' in voice.id.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
                
                # Set voice properties
                self.tts_engine.setProperty('rate', self.settings.voice_rate)
                self.tts_engine.setProperty('volume', self.settings.voice_volume)
                
                self.logger.info("Text-to-speech initialized")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize TTS: {e}")
    
    def is_available(self) -> bool:
        """Check if voice interface is available"""
        return VOICE_AVAILABLE and self.microphone is not None
    
    def start_listening(self, timeout: int = None):
        """Start listening for voice commands"""
        if not self.is_available():
            raise RuntimeError("Voice interface not available")
        
        timeout = timeout or self.settings.listening_timeout
        self.is_listening_flag = True
        
        try:
            with self.microphone as source:
                # Listen for audio
                audio = self.recognizer.listen(source, timeout=timeout)
            
            # Recognize speech
            text = self._recognize_speech(audio)
            
            if text:
                command = VoiceCommand(
                    text=text,
                    confidence=self._get_confidence(text),
                    timestamp=datetime.now(),
                    language=self.settings.language
                )
                
                self.last_recognition = command
                self.recognition_queue.put(command)
                
                # Trigger callback
                if self.on_command_received:
                    self.on_command_received(command)
                
                self.logger.info(f"Voice command recognized: {text}")
        
        except sr.WaitTimeoutError:
            self.logger.debug("Listening timeout")
        except Exception as e:
            self.logger.error(f"Voice recognition error: {e}")
        finally:
            self.is_listening_flag = False
    
    def start_wake_word_detection(self):
        """Start continuous wake word detection"""
        if not self.is_available():
            raise RuntimeError("Voice interface not available")
        
        self.is_wake_word_active = True
        
        def wake_word_loop():
            while self.is_wake_word_active:
                try:
                    with self.microphone as source:
                        # Listen for wake word with shorter timeout
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                    
                    # Check for wake word
                    text = self._recognize_speech(audio)
                    
                    if text and self._is_wake_word(text):
                        self.logger.info(f"Wake word detected: {text}")
                        
                        # Trigger callback
                        if self.on_wake_word_detected:
                            self.on_wake_word_detected(text)
                        
                        # Optionally listen for command after wake word
                        time.sleep(0.5)
                        self.start_listening()
                
                except sr.WaitTimeoutError:
                    continue  # Normal timeout, continue listening
                except Exception as e:
                    self.logger.error(f"Wake word detection error: {e}")
                    time.sleep(1)
        
        # Run in background thread
        threading.Thread(target=wake_word_loop, daemon=True).start()
    
    def stop_wake_word_detection(self):
        """Stop wake word detection"""
        self.is_wake_word_active = False
    
    def _recognize_speech(self, audio) -> Optional[str]:
        """Recognize speech from audio"""
        if not self.recognizer:
            return None
        
        try:
            # Try multiple recognition engines
            
            # 1. Google Speech Recognition (online)
            try:
                text = self.recognizer.recognize_google(audio, language=self.settings.language)
                return text
            except:
                pass
            
            # 2. Sphinx (offline)
            try:
                text = self.recognizer.recognize_sphinx(audio)
                return text
            except:
                pass
            
            # 3. Whisper (if available)
            try:
                import whisper
                model = whisper.load_model("tiny.en")
                
                # Convert audio to wav file
                with open("/tmp/temp_audio.wav", "wb") as f:
                    f.write(audio.get_wav_data())
                
                result = model.transcribe("/tmp/temp_audio.wav")
                return result["text"].strip()
            except:
                pass
        
        except Exception as e:
            self.logger.error(f"Speech recognition failed: {e}")
        
        return None
    
    def _is_wake_word(self, text: str) -> bool:
        """Check if text contains wake word"""
        text_lower = text.lower().strip()
        wake_word_lower = self.settings.wake_word.lower()
        
        # Exact match
        if text_lower == wake_word_lower:
            return True
        
        # Contains wake word
        if wake_word_lower in text_lower:
            return True
        
        # Similar sounding variations
        variations = [
            "aurora", "arora", "rora",
            "hey aurora", "ok aurora", "hi aurora"
        ]
        
        return any(var in text_lower for var in variations)
    
    def _get_confidence(self, text: str) -> float:
        """Calculate confidence score for recognized text"""
        if not text:
            return 0.0
        
        # Base confidence on text length and clarity
        confidence = min(1.0, len(text.split()) * 0.2)
        
        # Adjust for wake word
        if self.settings.wake_word.lower() in text.lower():
            confidence += 0.2
        
        return min(1.0, confidence)
    
    def speak(self, text: str, async_speak: bool = True):
        """Convert text to speech"""
        if not self.settings.voice_enabled or not self.tts_engine:
            return
        
        def speak_sync():
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
                self.logger.info(f"Spoke: {text[:50]}...")
            except Exception as e:
                self.logger.error(f"TTS error: {e}")
        
        if async_speak:
            threading.Thread(target=speak_sync, daemon=True).start()
        else:
            speak_sync()
    
    def get_recognized_text(self) -> Optional[str]:
        """Get the most recently recognized text"""
        try:
            command = self.recognition_queue.get_nowait()
            return command.text
        except queue.Empty:
            return None
    
    def is_listening(self) -> bool:
        """Check if currently listening"""
        return self.is_listening_flag
    
    def is_wake_word_active(self) -> bool:
        """Check if wake word detection is active"""
        return self.is_wake_word_active
    
    def update_settings(self, new_settings: VoiceSettings):
        """Update voice interface settings"""
        self.settings = new_settings
        
        # Update TTS settings
        if self.tts_engine:
            self.tts_engine.setProperty('rate', new_settings.voice_rate)
            self.tts_engine.setProperty('volume', new_settings.voice_volume)
        
        # Update recognizer settings
        if self.recognizer:
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
    
    def set_language(self, language: str):
        """Set recognition language"""
        self.settings.language = language
    
    def set_voice_properties(self, rate: int = None, volume: float = None):
        """Set TTS voice properties"""
        if rate:
            self.settings.voice_rate = rate
        if volume:
            self.settings.voice_volume = volume
        
        if self.tts_engine:
            if rate:
                self.tts_engine.setProperty('rate', rate)
            if volume:
                self.tts_engine.setProperty('volume', volume)
    
    def get_available_microphones(self) -> List[Dict[str, Any]]:
        """Get list of available microphones"""
        if not VOICE_AVAILABLE:
            return []
        
        try:
            mic_list = []
            for i, mic_name in enumerate(sr.Microphone.list_microphone_names()):
                mic_list.append({
                    'index': i,
                    'name': mic_name,
                    'device': sr.Microphone(device_index=i)
                })
            return mic_list
        except Exception as e:
            self.logger.error(f"Error getting microphones: {e}")
            return []
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get list of available TTS voices"""
        if not self.tts_engine:
            return []
        
        try:
            voices = []
            for voice in self.tts_engine.getProperty('voices'):
                voices.append({
                    'id': voice.id,
                    'name': voice.name,
                    'languages': voice.languages,
                    'gender': voice.gender,
                    'age': voice.age
                })
            return voices
        except Exception as e:
            self.logger.error(f"Error getting voices: {e}")
            return []
    
    def save_settings(self, file_path: str = None):
        """Save voice settings to file"""
        if file_path is None:
            file_path = Path.home() / ".config" / "aurora" / "voice_settings.json"
        
        try:
            settings_dict = {
                'wake_word': self.settings.wake_word,
                'language': self.settings.language,
                'confidence_threshold': self.settings.confidence_threshold,
                'listening_timeout': self.settings.listening_timeout,
                'voice_enabled': self.settings.voice_enabled,
                'voice_rate': self.settings.voice_rate,
                'voice_volume': self.settings.voice_volume
            }
            
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w') as f:
                json.dump(settings_dict, f, indent=2)
            
            self.logger.info(f"Voice settings saved to {file_path}")
        
        except Exception as e:
            self.logger.error(f"Error saving settings: {e}")
    
    def load_settings(self, file_path: str = None) -> VoiceSettings:
        """Load voice settings from file"""
        if file_path is None:
            file_path = Path.home() / ".config" / "aurora" / "voice_settings.json"
        
        try:
            file_path = Path(file_path)
            if file_path.exists():
                with open(file_path, 'r') as f:
                    settings_dict = json.load(f)
                
                self.settings = VoiceSettings(**settings_dict)
                self.update_settings(self.settings)
                
                self.logger.info(f"Voice settings loaded from {file_path}")
        
        except Exception as e:
            self.logger.error(f"Error loading settings: {e}")
        
        return self.settings
    
    def test_microphone(self) -> bool:
        """Test microphone functionality"""
        if not self.is_available():
            return False
        
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=2)
            
            # Try to recognize
            text = self._recognize_speech(audio)
            return text is not None
        
        except Exception as e:
            self.logger.error(f"Microphone test failed: {e}")
            return False
    
    def test_voice(self, test_text: str = "Voice test successful"):
        """Test text-to-speech functionality"""
        try:
            self.speak(test_text, async_speak=False)
            return True
        except Exception as e:
            self.logger.error(f"Voice test failed: {e}")
            return False
    
    def cleanup(self):
        """Cleanup voice interface resources"""
        try:
            self.stop_wake_word_detection()
            self.is_listening_flag = False
            
            if self.tts_engine:
                self.tts_engine.stop()
            
            self.logger.info("Voice interface cleaned up")
        
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")

# Voice commands processor
class VoiceCommandProcessor:
    """Process voice commands and convert to system actions"""
    
    def __init__(self, voice_interface: VoiceInterface):
        self.voice_interface = voice_interface
        self.command_patterns = self._load_command_patterns()
        
        # Register callbacks
        self.voice_interface.on_command_received = self._process_command
        
    def _load_command_patterns(self) -> Dict[str, Callable]:
        """Load voice command patterns"""
        return {
            # System commands
            r'shutdown|turn off|power down': self._shutdown_system,
            r'restart|reboot': self._restart_system,
            r'sleep|hibernate': self._sleep_system,
            r'lock|lock screen': self._lock_screen,
            
            # Application commands
            r'open (\w+)': self._open_application,
            r'close (\w+)': self._close_application,
            r'switch to (\w+)': self._switch_application,
            
            # Settings commands
            r'increase volume|volume up': self._increase_volume,
            r'decrease volume|volume down': self._decrease_volume,
            r'mute|unmute': self._toggle_mute,
            r'brighter|increase brightness': self._increase_brightness,
            r'dimmer|decrease brightness': self._decrease_brightness,
            
            # Information commands
            r'what time|current time': self._tell_time,
            r'weather|forecast': self._tell_weather,
            r'battery level': self._tell_battery,
            r'system status': self._tell_system_status,
            
            # Aurora AI commands
            r'aurora|hey aurora': self._activate_assistant,
            r'help|what can you do': self._show_help,
        }
    
    def _process_command(self, command: VoiceCommand):
        """Process a voice command"""
        import re
        
        text = command.text.lower()
        
        for pattern, handler in self.command_patterns.items():
            match = re.search(pattern, text)
            if match:
                try:
                    if match.groups():
                        handler(*match.groups())
                    else:
                        handler()
                    self.voice_interface.speak(f"Executing: {match.group()}")
                except Exception as e:
                    self.voice_interface.speak(f"Error executing command: {str(e)}")
                return
        
        # If no pattern matched, pass to AI assistant
        self.voice_interface.speak("Let me help you with that")
        # Forward to AI assistant for processing
    
    def _shutdown_system(self):
        """Shutdown the system"""
        os.system("systemctl poweroff")
    
    def _restart_system(self):
        """Restart the system"""
        os.system("systemctl reboot")
    
    def _sleep_system(self):
        """Put system to sleep"""
        os.system("systemctl suspend")
    
    def _lock_screen(self):
        """Lock the screen"""
        os.system("loginctl lock-session")
    
    def _open_application(self, app_name: str):
        """Open an application"""
        os.system(f"gtk-launch {app_name} 2>/dev/null &")
    
    def _close_application(self, app_name: str):
        """Close an application"""
        os.system(f"pkill -f {app_name}")
    
    def _switch_application(self, app_name: str):
        """Switch to an application"""
        os.system(f"wmctrl -a {app_name}")
    
    def _increase_volume(self):
        """Increase system volume"""
        os.system("amixer set Master 5%+")
    
    def _decrease_volume(self):
        """Decrease system volume"""
        os.system("amixer set Master 5%-")
    
    def _toggle_mute(self):
        """Toggle mute"""
        os.system("amixer set Master toggle")
    
    def _increase_brightness(self):
        """Increase screen brightness"""
        os.system("brightnessctl set +10%")
    
    def _decrease_brightness(self):
        """Decrease screen brightness"""
        os.system("brightnessctl set 10%-")
    
    def _tell_time(self):
        """Tell current time"""
        from datetime import datetime
        current_time = datetime.now().strftime("%I:%M %p")
        self.voice_interface.speak(f"The current time is {current_time}")
    
    def _tell_weather(self):
        """Tell weather information"""
        self.voice_interface.speak("Weather information not available yet")
    
    def _tell_battery(self):
        """Tell battery level"""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery:
                percentage = battery.percent
                self.voice_interface.speak(f"Battery level is {percentage}%")
            else:
                self.voice_interface.speak("No battery detected")
        except:
            self.voice_interface.speak("Could not read battery level")
    
    def _tell_system_status(self):
        """Tell system status"""
        try:
            import psutil
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            self.voice_interface.speak(f"CPU usage is {cpu}%, Memory usage is {memory}%")
        except:
            self.voice_interface.speak("Could not read system status")
    
    def _activate_assistant(self):
        """Activate AI assistant"""
        from ..ui.taskbar_assistant import show_assistant
        show_assistant()
    
    def _show_help(self):
        """Show help information"""
        help_text = "I can help you manage your system, open applications, adjust settings, and answer questions. Try saying 'open firefox', 'what time is it', or 'system status'."
        self.voice_interface.speak(help_text)

# Global voice interface instance
_voice_interface = None

def get_voice_interface() -> VoiceInterface:
    """Get global voice interface instance"""
    global _voice_interface
    if _voice_interface is None:
        _voice_interface = VoiceInterface()
    return _voice_interface

def initialize_voice_system():
    """Initialize the voice system"""
    voice = get_voice_interface()
    processor = VoiceCommandProcessor(voice)
    
    # Load settings
    voice.load_settings()
    
    return voice, processor