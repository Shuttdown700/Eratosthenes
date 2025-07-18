import mutagen
from mutagen.flac import FLAC
import librosa
import numpy as np
import os

def check_flac_quality(file_path):
    try:
        # Load the FLAC file metadata
        audio = FLAC(file_path)
        
        # Extract metadata
        sample_rate = audio.info.sample_rate
        bits_per_sample = audio.info.bits_per_sample
        channels = audio.info.channels
        duration = audio.info.length
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
        
        print(f"File: {file_path}")
        print(f"Sample Rate: {sample_rate} Hz")
        print(f"Bit Depth: {bits_per_sample} bits")
        print(f"Channels: {channels}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"File Size: {file_size:.2f} MB")
        
        # Check if metadata indicates high quality
        is_high_quality = True
        quality_notes = []
        
        if sample_rate < 44100:
            is_high_quality = False
            quality_notes.append("Sample rate below CD quality (44100 Hz).")
        if bits_per_sample < 16:
            is_high_quality = False
            quality_notes.append("Bit depth below CD quality (16 bits).")
        
        # Approximate expected file size for lossless (MB per minute)
        expected_size_per_min = (sample_rate * bits_per_sample * channels * 60) / (8 * 1024 * 1024)
        actual_size_per_min = file_size / (duration / 60)
        
        if actual_size_per_min < (expected_size_per_min * 0.7):  # Allow 30% compression
            quality_notes.append("File size smaller than expected for lossless FLAC.")
        
        # Spectral analysis to detect lossy transcoding
        y, sr = librosa.load(file_path, sr=None)
        fft = np.abs(librosa.stft(y))
        freqs = librosa.fft_frequencies(sr=sr)
        mean_spectrum = np.mean(fft, axis=1)
        
        # Check for frequency cutoff (lossy formats like MP3 cut off above ~16-20 kHz)
        high_freq_energy = np.sum(mean_spectrum[freqs > 16000]) / np.sum(mean_spectrum)
        if high_freq_energy < 0.01:  # Low energy above 16 kHz suggests lossy source
            is_high_quality = False
            quality_notes.append("Low high-frequency content; likely transcoded from lossy format.")
        
        # Print quality assessment
        if is_high_quality and not quality_notes:
            print("Assessment: Likely a high-quality lossless FLAC.")
        else:
            print("Assessment: Potential quality issues detected:")
            for note in quality_notes:
                print(f"- {note}")
                
    except Exception as e:
        print(f"Error: Invalid or corrupted FLAC file. {str(e)}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python assess_flac_quality.py <path_to_flac_file>")
    else:
        check_flac_quality(sys.argv[1])