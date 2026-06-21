import numpy as np
import pygame

class SoundGenerator:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.sounds = {}
        
    def init_mixer(self):
        """Initializes Pygame mixer and synthesizes magical spell sounds."""
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1)
            
        self.sounds["fire"] = self.generate_fire()
        self.sounds["water"] = self.generate_water()
        self.sounds["earth"] = self.generate_earth()
        self.sounds["light"] = self.generate_light()
        self.sounds["warp"] = self.generate_warp()
        self.sounds["shield"] = self.generate_shield()
        self.sounds["score"] = self.generate_score()
        self.sounds["error"] = self.generate_error()
        
    def _array_to_sound(self, arr):
        """Converts float32 numpy array to 16-bit signed PCM Pygame Sound."""
        # Normalize and clip to prevent distortion
        arr = np.clip(arr, -1.0, 1.0)
        pcm = (arr * 32767).astype(np.int16)
        
        # Check active channels to support stereo mixers
        mixer_init = pygame.mixer.get_init()
        if mixer_init:
            channels = mixer_init[2]
            if channels == 2:
                # Convert 1D mono to 2D stereo array
                pcm = np.column_stack((pcm, pcm))
                
        return pygame.sndarray.make_sound(pcm)
        
    def generate_fire(self):
        """Creates a flame combustion/woosh sound (descending noise rumble)."""
        duration = 0.35
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        noise = np.random.uniform(-1.0, 1.0, len(t))
        
        # 120Hz down to 40Hz frequency sweep
        sweep_freq = 120 - 80 * (t / duration)
        sine_rumble = np.sin(2 * np.pi * sweep_freq * t)
        
        # Blend noise and low rumble, decay exponentially
        wave = (0.7 * noise + 0.3 * sine_rumble) * np.exp(-5 * t / duration)
        return self._array_to_sound(wave)
        
    def generate_water(self):
        """Creates a bubbling, resonant water sound using FM synthesis."""
        duration = 0.25
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        
        # Frequency Modulation: 380Hz carrier modulated by 15Hz vibrato
        modulation = 4 * np.sin(2 * np.pi * 15 * t)
        phase = 2 * np.pi * 380 * t + modulation
        
        wave = np.sin(phase) * np.exp(-6 * t / duration)
        return self._array_to_sound(wave)
        
    def generate_earth(self):
        """Creates a distorted rock-crushing/shattering earth impact."""
        duration = 0.3
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        
        # Distorted white noise
        noise = np.random.uniform(-1.0, 1.0, len(t))
        crunchy_noise = np.clip(noise * 2.5, -1.0, 1.0)
        
        # Low thud: 70Hz sine wave
        thud = np.sin(2 * np.pi * 70 * t)
        
        wave = (0.8 * crunchy_noise + 0.2 * thud) * np.exp(-6 * t / duration)
        return self._array_to_sound(wave)
        
    def generate_light(self):
        """Creates a high-pitched laser beam/light sound (rapid sweep up)."""
        duration = 0.2
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        
        # Rapid upward pitch sweep: 900Hz to 2400Hz
        freq = 900 + 1500 * (t / duration)
        phase = 2 * np.pi * freq * t
        
        wave = np.sin(phase) * np.exp(-7 * t / duration)
        return self._array_to_sound(wave)
        
    def generate_warp(self):
        """Creates a sci-fi time warping slowdown sound."""
        duration = 1.0
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        
        # Slowing pitch (500Hz down to 100Hz) modulated by a deep 8Hz LFO
        lfo = 10 * np.sin(2 * np.pi * 8 * t)
        freq_sweep = 500 - 400 * (t / duration)
        phase = 2 * np.pi * freq_sweep * t + lfo
        
        wave = np.sin(phase) * np.exp(-2.2 * t / duration)
        return self._array_to_sound(wave)
        
    def generate_shield(self):
        """Creates a metallic shield collision ring (clang)."""
        duration = 0.45
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        
        # Blend two non-harmonic ring frequencies: 420Hz and 615Hz
        wave1 = np.sin(2 * np.pi * 420 * t)
        wave2 = np.sin(2 * np.pi * 615 * t)
        
        wave = (0.6 * wave1 + 0.4 * wave2) * np.exp(-4 * t / duration)
        return self._array_to_sound(wave)
        
    def generate_score(self):
        """Creates a bright, satisfying arpeggio/chime sound for scores."""
        duration = 0.25
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        
        # Blend two harmonic frequencies (659.25Hz = E5, 987.77Hz = B5)
        wave1 = np.sin(2 * np.pi * 659.25 * t)
        wave2 = np.sin(2 * np.pi * 987.77 * t)
        
        envelope = np.exp(-5 * t / duration)
        wave = (0.5 * wave1 + 0.5 * wave2) * envelope
        return self._array_to_sound(wave)
        
    def generate_error(self):
        """Creates a buzzy, low square wave representing a bomb or mistake."""
        duration = 0.35
        t = np.linspace(0, duration, int(self.sample_rate * duration), endpoint=False)
        
        # 100Hz square wave
        freq = 100
        wave = np.sign(np.sin(2 * np.pi * freq * t))
        
        envelope = np.exp(-3 * t / duration)
        wave = wave * envelope * 0.4  # Slightly quieter to prevent harsh buzzing
        return self._array_to_sound(wave)
        
    def play(self, sound_name):
        """Plays the designated synthesized sound effect."""
        sound = self.sounds.get(sound_name)
        if sound:
            sound.play()
